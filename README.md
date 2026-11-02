# Quellcode-Angebot (GPL-3.0 / LGPL-2.1)

> Entwurf, keine Rechtsberatung.

OpenReceiver enthält Software, die unter der GNU General Public License (GPL) bzw. der GNU Lesser
General Public License (LGPL) steht (UxPlay: GPL-3.0; FFmpeg, GStreamer, GLib, libplist u. a.: LGPL-2.1).

Sie können den vollständigen, maschinenlesbaren Quelltext der selbst gebauten Teile (UxPlay, FFmpeg,
gst-libav samt Build-Skripten) in genau den ausgelieferten Versionen erhalten:

1. **Download:** <https://github.com/chiefabi/openreceiver-source> (inkl. `SHA256SUMS.txt`)
2. **Auf Anfrage:** a.saridevelop@gmail.com, gegen Erstattung der Kosten für Datenträger und Versand

Dieses Angebot gilt für jeden, der dieses Programm erhalten hat, für mindestens drei Jahre nach der
letzten Auslieferung der jeweiligen Version (GPL-3.0, Abschnitt 6b).

## Selbst gebaute Teile

Upstream-Quellen zur Orientierung; maßgeblich ist das Archiv oben:

| Komponente | Version | Quelle |
|---|---|---|
| UxPlay | 1.73.7 | https://github.com/FDH2/UxPlay |
| FFmpeg (minimal) | 8.1.3 | https://ffmpeg.org/releases/ |
| gst-libav | 1.28.8 | https://gstreamer.freedesktop.org/src/gst-libav/ |
| mDNSResponder | 2881.120.11 | https://github.com/apple-oss-distributions/mDNSResponder (Apache-2.0 / BSD-3-Clause) |

## Änderungen an UxPlay

Siehe Ordner `patches/` im Archiv. Aktuell:

1. Korrektur der Längenprüfung des Client-Beweises bei der PIN-Kopplung (`lib/raop_handlers.h`)
2. Ton nach Pause: Lücken im Audiopuffer werden durch die leeren Antworten des Senders geschlossen,
   Wiederholungs-Anfragen sind begrenzt (`lib/raop_buffer.c`, `raop_buffer.h`, `raop_rtp.c`)
3. Datenraten-Zeile "STATS" für die Fehlersuche (neue Datei `netstats.h`, `uxplay.cpp`, `lib/raop.h`,
   `raop_rtp.c`, `raop_buffer.c`, `renderers/video_renderer.c`, `video_renderer.h`)
4. Titel und Symbol des Videofensters, UTF-8-Kommandozeile unter Windows, regelmäßiges Leeren der
   Standardausgabe (`uxplay.cpp`, `CMakeLists.txt`, neue Datei `uxplay.rc`)
5. Längenprüfungen für die vom Client gesendeten Schlüsseldaten (eiv/ekey bei SETUP, epk/authTag bei
   pair-setup-pin) in `lib/raop_handlers.h`, die ohne die Prüfung über das Ende des zugewiesenen
   Speichers hinaus gelesen hätten (zu kurze Felder führten zum Absturz der Engine)
6. Begrenzung des beim Lesen des Protokoll-Tokens ("RTSP/1.0") kopierten Bereichs auf die tatsächlich im
   aktuellen Lesevorgang angekommenen Daten (`lib/http_request.c`; betraf Anfragen, deren Kopfzeile auf
   zwei TCP-Pakete verteilt ankommt)
7. Prüfung des vom Client angegebenen `payload_size`-Feldes im Video-Mirroring-Datenstrom auf einen
   plausiblen Bereich (`lib/raop_rtp_mirror.c`; ein negativer oder zu großer Wert führte sonst zum
   Absturz der Engine, bestätigt durch eine Segmentierungsverletzung in der ungepatchten Version)
8. Korrektur einer Zeile in der Bonjour-Anmeldung (`_raop._tcp`), die den zuvor je nach PIN/Passwort-
   Einstellung gesetzten Wert des "sf"-Felds unmittelbar danach wieder mit einem festen Wert überschrieb,
   sodass die Fallunterscheidung wirkungslos war (`lib/dnssd.c`)
9. Prüfung des vom Client beim FairPlay-Schlüsselaustausch gesendeten Auswahl-Bytes auf einen gültigen
   Bereich (`lib/fairplay_playfair.c`; ein beliebiger Wert wurde zuvor ungeprüft als Index in eine
   kleine, feste Tabelle verwendet – das las Speicher weit außerhalb dieser Tabelle, schickte ihn als
   Antwort zurück und konnte die Engine zum Absturz bringen, erreichbar ganz ohne vorherige Geräte-Kopplung)
10. Prüfung der vom Client im Bildschirm-Datenstrom angegebenen SPS/PPS/VPS-Längenfelder gegen die
    tatsächlich empfangene Paketgröße (`lib/raop_rtp_mirror.c`, H.264- und H.265-Pfad; ein Längenfeld mit
    gesetztem höchstem Bit wurde als negative Zahl gespeichert und dann ungeprüft für Zeiger-Arithmetik,
    eine Speicher-Reservierung und einen Kopiervorgang verwendet – das konnte den Heap-Speicher beschädigen)
11. Jede gleichzeitige Engine (siehe `-m`/`-p` für mehrere iPhones an einem PC) meldet sich jetzt mit
    einer eigenen, aus ihrer eigenen Geräte-Adresse abgeleiteten Kennung an, statt mit einer fest
    einprogrammierten, bei jeder Instanz identischen Kennung (`lib/dnssd.c`, `lib/raop_handlers.h`)

## Änderungen an mDNSResponder

Nur Anpassungen für den Windows-Bau mit MinGW: Dateien `patches/mDNSResponder-2881.120.11-mingw.patch`
und `patches/mDNSResponder-2881.120.11-awdl.patch` im Archiv; dazu `build-scripts/mdns/firewall_stub.c`.

## Unverändert übernommene Bibliotheken

GStreamer 1.28.8, GLib, OpenSSL, libplist, zlib u. a. – Quelltext bei der MSYS2-Distribution,
https://repo.msys2.org/mingw/sources/ – Paketnamen und Versionen stehen in `THIRD-PARTY-NOTICES.txt`
(in der App unter Einstellungen → Lizenzen & Quellcode).

## Ersetzen der LGPL-Bibliotheken

Die LGPL-Bibliotheken (FFmpeg, GStreamer, GLib, libplist u. a.) liegen als DLLs in `engine/bin` und
`engine/lib/gstreamer-1.0` und dürfen durch eigene, kompatible Builds ersetzt werden.
