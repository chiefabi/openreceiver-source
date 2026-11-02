/*
 * Regressionstest für den Audio-Paketpuffer von UxPlay (lib/raop_buffer.c).
 *
 * Hintergrund: Pausiert das iPhone, schickt es für die stille Strecke keine Tondaten, zählt aber die Paketnummern
 * weiter. UxPlay fordert die "fehlenden" Pakete an; das iPhone antwortet mit leeren Platzhaltern. Unkorrigiert wirft
 * UxPlay diese Antworten weg, die Lücke bleibt offen, und der Ton wird nicht mehr ausgeliefert (Stillstand, viele
 * Sekunden verzögerter Ton, tausende Wiederholungs-Anfragen).
 *
 * Bauen (MSYS2 UCRT64), im UxPlay-Quellordner (unverändert oder mit Patch):
 *   gcc -O1 [-DPATCHED] -o buffer_test.exe raop_buffer_test.c lib/raop_buffer.c lib/crypto.c lib/logger.c \
 *       lib/utils.c lib/byteutils.c -I lib -DOPENSSL_API_COMPAT=0x10101000L $(pkg-config --cflags --libs openssl) -lws2_32
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include "raop_buffer.h"
#include "logger.h"

unsigned long long raop_stat_gaps_skipped = 0;   /* Zähler, den raop_buffer.c (mit Patch stats-line) erwartet; normalerweise in raop_rtp.c */

static int fails = 0;
static void check(const char *what, int ok) { printf("  [%s] %s\n", ok ? "OK" : "FEHLER", what); if (!ok) fails++; }

static const unsigned char NO_DATA[4] = { 0x00, 0x68, 0x34, 0x00 };
static int resend_calls, resend_first, resend_count;

static int on_resend(void *opaque, unsigned short seq, unsigned short count) {
    (void) opaque; resend_calls++; resend_first = seq; resend_count = count; return 0;
}

static void data_packet(raop_buffer_t *b, unsigned short seq) {
    unsigned char p[44]; memset(p, 0, sizeof p);
    p[0] = 0x80; p[1] = 0x60; p[2] = (unsigned char) (seq >> 8); p[3] = (unsigned char) seq;
    uint32_t ts = (uint32_t) seq * 480u; p[4] = ts >> 24; p[5] = ts >> 16; p[6] = ts >> 8; p[7] = (unsigned char) ts;
    memset(p + 12, 0x8c, 32);
    raop_buffer_enqueue(b, p, sizeof p, 1);
}

/* Antwort des iPhones auf eine Wiederholungs-Anfrage für ein Paket, das es nie gesendet hat (leerer Platzhalter) */
static void resend_reply_empty(raop_buffer_t *b, unsigned short seq) {
#ifdef PATCHED
    raop_buffer_enqueue_empty(b, seq);                   /* so behandelt raop_rtp.c die Antwort jetzt */
#else
    unsigned char p[16]; memset(p, 0, sizeof p);         /* so wurde sie bisher behandelt: nur an enqueue() übergeben */
    p[0] = 0x80; p[1] = 0x60; p[2] = (unsigned char) (seq >> 8); p[3] = (unsigned char) seq; memcpy(p + 12, NO_DATA, 4);
    raop_buffer_enqueue(b, p, sizeof p, 1);              /* gibt 0 zurück und füllt den Eintrag nicht */
#endif
}

static int drain(raop_buffer_t *b, unsigned short *last_seq) {
    int n = 0; unsigned int len; uint32_t ts; unsigned short seq; void *d;
    while ((d = raop_buffer_dequeue(b, &len, &ts, &seq, 0))) { free(d); n++; if (last_seq) *last_seq = seq; }
    return n;
}

static raop_buffer_t *fresh(logger_t *lg) {
    unsigned char key[16] = { 0 }, iv[16] = { 0 };
    return raop_buffer_init(lg, key, iv);
}

int main(void) {
    logger_t *lg = logger_init(); logger_set_level(lg, LOGGER_ERR);
    unsigned short last = 0; int n;
#ifdef PATCHED
    printf("Variante: KORRIGIERT\n");
#else
    printf("Variante: UNVERAENDERT (UxPlay 1.73.7)\n");
#endif

    printf("Test 1: Normalbetrieb, Pakete in Reihenfolge\n");
    { raop_buffer_t *b = fresh(lg);
      for (unsigned short s = 100; s < 110; s++) data_packet(b, s);
      check("10 Pakete ausgeliefert", drain(b, &last) == 10 && last == 109); }

    printf("Test 2: Reihenfolge vertauscht, echte Wiederholung kommt an (muss weiter funktionieren)\n");
    { raop_buffer_t *b = fresh(lg);
      data_packet(b, 200); data_packet(b, 202);
      check("zunächst nur Paket 200 (201 fehlt)", drain(b, &last) == 1 && last == 200);
      resend_calls = 0; raop_buffer_handle_resends(b, on_resend, NULL);
      check("Wiederholung von Paket 201 angefordert", resend_calls == 1 && resend_first == 201 && resend_count == 1);
      data_packet(b, 201);
      check("danach 201 und 202 ausgeliefert", drain(b, &last) == 2 && last == 202); }

    printf("Test 3: Pause - 35 Pakete nie gesendet, iPhone antwortet mit leeren Platzhaltern\n");
    { raop_buffer_t *b = fresh(lg);
      for (unsigned short s = 100; s < 105; s++) data_packet(b, s);
      drain(b, &last);
      data_packet(b, 140); for (unsigned short s = 141; s <= 145; s++) data_packet(b, s);
      check("Lücke erkannt: es wird gewartet (nichts ausgeliefert)", drain(b, &last) == 0);
      resend_calls = 0; raop_buffer_handle_resends(b, on_resend, NULL);
      check("Anforderung für 35 Pakete ab 105", resend_calls == 1 && resend_first == 105 && resend_count == 35);
      for (unsigned short s = 105; s < 140; s++) resend_reply_empty(b, s);
      n = drain(b, &last);
      printf("     ausgeliefert nach den Platzhalter-Antworten: %d Pakete (erwartet 6: 140..145)\n", n);
      check("Ton läuft sofort weiter (6 Pakete, letztes 145)", n == 6 && last == 145); }

    printf("Test 4: Pause - das iPhone antwortet gar nicht\n");
    { raop_buffer_t *b = fresh(lg);
      for (unsigned short s = 100; s < 105; s++) data_packet(b, s);
      drain(b, &last);
      data_packet(b, 140); for (unsigned short s = 141; s <= 145; s++) data_packet(b, s);
      resend_calls = 0;
      for (int i = 0; i < 100; i++) { raop_buffer_handle_resends(b, on_resend, NULL); }
      n = drain(b, &last);
      printf("     Anfragen: %d, danach ausgeliefert: %d Pakete\n", resend_calls, n);
#ifdef PATCHED
      check("Anfragen sind begrenzt (höchstens 30) statt endlos", resend_calls <= 30);
#else
      check("(unverändert) Anfragen sind endlos: 100 von 100", resend_calls == 100);
#endif
      check("Ton läuft nach kurzer Wartezeit weiter (6 Pakete)", n == 6 && last == 145); }

    printf("Test 5: Überlauf der 16-Bit-Paketnummer mitten in der Lücke\n");
    { raop_buffer_t *b = fresh(lg);
      for (unsigned short s = 65530; s != 2; s++) data_packet(b, s);   /* 65530..65535, 0, 1 */
      drain(b, &last);
      data_packet(b, 30); data_packet(b, 31);
      check("Lücke über den Überlauf: es wird gewartet", drain(b, &last) == 0);
      for (unsigned short s = 2; s < 30; s++) resend_reply_empty(b, s);
      n = drain(b, &last);
      check("danach 30 und 31 ausgeliefert", n == 2 && last == 31); }

    logger_destroy(lg);
    printf(fails ? "ERGEBNIS: %d FEHLER\n" : "ERGEBNIS: BESTANDEN\n", fails);
    return fails ? 1 : 0;
}
