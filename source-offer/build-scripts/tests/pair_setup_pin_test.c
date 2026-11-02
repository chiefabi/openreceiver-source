/*
 * Regressionstest für die PIN-Kopplung (pair-setup-pin, SRP-6a/SHA-1) gegen einen laufenden uxplay.exe.
 * Verhält sich wie ein iPhone: Schritt 1 (user/method) und Schritt 2 (pk + proof) mit dem richtigen PIN.
 * Erwartung: Der Server antwortet in Schritt 2 mit 200 und einem "proof" (20 Bytes) statt die Verbindung zu schließen.
 *
 * Bauen (MSYS2 UCRT64), im UxPlay-Quellordner:
 *   gcc -O1 -o pair_test.exe pair_setup_pin_test.c lib/srp.c -I lib -DOPENSSL_API_COMPAT=0x10101000L \
 *       $(pkg-config --cflags --libs libplist-2.0 openssl) -lws2_32
 * Aufruf: pair_test.exe <port> <pin>
 */
#include <winsock2.h>
#include <ws2tcpip.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <plist/plist.h>
#include "srp.h"

static SOCKET connect_to(const char *host, int port) {
    WSADATA w; WSAStartup(MAKEWORD(2, 2), &w);
    SOCKET s = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    struct sockaddr_in a; memset(&a, 0, sizeof a);
    a.sin_family = AF_INET; a.sin_port = htons((u_short) port); inet_pton(AF_INET, host, &a.sin_addr);
    if (connect(s, (struct sockaddr *) &a, sizeof a) != 0) { fprintf(stderr, "connect failed\n"); exit(2); }
    return s;
}

/* sendet eine RTSP-POST-Anfrage und liest Status + Body; status = 0, wenn die Verbindung geschlossen wurde */
static int rtsp_post(SOCKET s, const char *path, int cseq, const char *body, int len, char **out, int *outlen) {
    char head[512];
    int hl = snprintf(head, sizeof head,
        "POST %s RTSP/1.0\r\nCSeq: %d\r\nUser-Agent: AirPlay/980.77.1\r\n"
        "Content-Type: application/x-apple-binary-plist\r\nContent-Length: %d\r\n\r\n", path, cseq, len);
    send(s, head, hl, 0); if (len) send(s, body, len, 0);

    char buf[8192]; int n = 0, got;
    int hdr_end = -1;
    while (hdr_end < 0 && n < (int) sizeof buf - 1) {
        got = recv(s, buf + n, (int) sizeof buf - 1 - n, 0);
        if (got <= 0) return 0;
        n += got; buf[n] = 0;
        char *p = strstr(buf, "\r\n\r\n"); if (p) hdr_end = (int) (p - buf) + 4;
    }
    int status = 0; sscanf(buf, "%*s %d", &status);
    int clen = 0; for (char *p = buf; p && p < buf + hdr_end; p++) {
        if (_strnicmp(p, "Content-Length:", 15) == 0) { clen = atoi(p + 15); break; }
    }
    *out = (char *) malloc(clen + 1); *outlen = 0;
    int have = n - hdr_end; if (have > clen) have = clen;
    memcpy(*out, buf + hdr_end, have); *outlen = have;
    while (*outlen < clen) { got = recv(s, *out + *outlen, clen - *outlen, 0); if (got <= 0) break; *outlen += got; }
    return status;
}

int main(int argc, char **argv) {
    if (argc < 3) { fprintf(stderr, "usage: %s <port> <pin>\n", argv[0]); return 2; }
    int port = atoi(argv[1]); const char *pin = argv[2];
    const char *user = "46:04:C1:95:52:B5";
    SOCKET s = connect_to("127.0.0.1", port);

    /* Schritt 1: method=pin, user=<device id> */
    plist_t d1 = plist_new_dict();
    plist_dict_set_item(d1, "method", plist_new_string("pin"));
    plist_dict_set_item(d1, "user", plist_new_string(user));
    char *b1 = NULL; uint32_t l1 = 0; plist_to_bin(d1, &b1, &l1); plist_free(d1);
    char *r1 = NULL; int rl1 = 0;
    int st1 = rtsp_post(s, "/pair-setup-pin", 1, b1, (int) l1, &r1, &rl1);
    printf("Schritt 1: Status %d, %d Byte Antwort\n", st1, rl1);
    if (st1 != 200) { printf("FEHLER: Schritt 1 nicht erfolgreich\n"); return 1; }

    plist_t resp1 = NULL; plist_from_bin(r1, rl1, &resp1);
    char *salt = NULL, *B = NULL; uint64_t lsalt = 0, lB = 0;
    plist_get_data_val(plist_dict_get_item(resp1, "salt"), &salt, &lsalt);
    plist_get_data_val(plist_dict_get_item(resp1, "pk"), &B, &lB);
    printf("  salt %d Byte, B %d Byte\n", (int) lsalt, (int) lB);

    /* Client-Seite von SRP-6a (SHA-1, 2048 Bit) mit dem eingegebenen PIN */
    struct SRPUser *usr = srp_user_new(SRP_SHA1, SRP_NG_2048, user, (const unsigned char *) pin, (int) strlen(pin), NULL, NULL, 1);
    const char *uname = NULL; const unsigned char *A = NULL; int lA = 0;
    srp_user_start_authentication(usr, &uname, &A, &lA);
    const unsigned char *M = NULL; int lM = 0;
    srp_user_process_challenge(usr, (const unsigned char *) salt, (int) lsalt, (const unsigned char *) B, (int) lB, &M, &lM);
    printf("  Client-Beweis M: %d Byte\n", lM);
    if (!M) { printf("FEHLER: Client konnte keinen Beweis berechnen\n"); return 1; }

    /* Schritt 2: pk (= A) und proof (= M) */
    plist_t d2 = plist_new_dict();
    plist_dict_set_item(d2, "pk", plist_new_data((const char *) A, lA));
    plist_dict_set_item(d2, "proof", plist_new_data((const char *) M, lM));
    char *b2 = NULL; uint32_t l2 = 0; plist_to_bin(d2, &b2, &l2); plist_free(d2);
    char *r2 = NULL; int rl2 = 0;
    int st2 = rtsp_post(s, "/pair-setup-pin", 2, b2, (int) l2, &r2, &rl2);
    printf("Schritt 2: Status %d, %d Byte Antwort\n", st2, rl2);
    if (st2 != 200) { printf("FEHLER: Server hat den Beweis abgelehnt oder die Verbindung geschlossen\n"); return 1; }

    plist_t resp2 = NULL; plist_from_bin(r2, rl2, &resp2);
    char *proof = NULL; uint64_t lp = 0;
    plist_get_data_val(plist_dict_get_item(resp2, "proof"), &proof, &lp);
    printf("  Server-Beweis: %d Byte\n", (int) lp);
    if (lp != 20) { printf("FEHLER: unerwartete Beweislänge\n"); return 1; }
    srp_user_verify_session(usr, (const unsigned char *) proof);
    printf("  Server-Beweis vom Client %s\n", srp_user_is_authenticated(usr) ? "bestätigt (gegenseitige Authentifizierung OK)" : "NICHT bestätigt");
    printf("ERGEBNIS: PIN-Kopplung bis Schritt 2 erfolgreich\n");
    return srp_user_is_authenticated(usr) ? 0 : 1;
}
