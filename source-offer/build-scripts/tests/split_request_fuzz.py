"""Prueft die Laengenbegrenzung beim Lesen des Protokoll-Tokens in http_request.c (on_url): schickt die
RTSP-Anfragezeile absichtlich in zwei getrennten TCP-Schreibvorgaengen (URL und " RTSP/1.0\r\n\r\n" getrennt),
nachdem vorher eine erkennbare Markierung in den (wiederverwendeten) 1024-Byte-Empfangspuffer der Engine
geschrieben wurde. Ohne den Patch uxplay-1.73.7-http-request-protocol-bounds koennte das Protokollfeld der
Antwort Reste dieser Markierung enthalten.
Aufruf: python -I split_request_fuzz.py <port>
"""
import socket, sys, time

HOST = "127.0.0.1"
PORT = int(sys.argv[1])
MARK = b"MARKER42"  # 8 Byte, gut wiedererkennbar


def fill_buffer_with_marker():
    """Schickt eine Anfrage, deren Kopfzeilen-Wert die Markierung in den Server-Lesepuffer legt."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(5.0)
        s.connect((HOST, PORT))
        # Eine grosse, aber gueltige Kopfzeile, die mit der Markierung endet; danach die Verbindung hart
        # schliessen (RST), damit der Server sie nicht als vollstaendige Anfrage verarbeitet, der Puffer-Inhalt
        # (derselbe wiederverwendete 1024-Byte-Stack-Puffer je Worker-Thread) aber gefuellt bleibt.
        junk = b"X" * 200 + MARK
        req = b"OPTIONS * RTSP/1.0\r\nCSeq: 1\r\nX-Filler: " + junk + b"\r\n"
        try:
            s.sendall(req)
            s.recv(4096)
        except OSError:
            pass


def split_url_request():
    """Schickt 'GET /foo' und ' RTSP/1.0\r\n\r\n' als zwei getrennte TCP-Pakete; liest die Statuszeile zurueck."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(5.0)
        s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        s.connect((HOST, PORT))
        s.sendall(b"GET /foo")
        time.sleep(0.3)   # erzwingt zwei getrennte recv()-Aufrufe auf der Serverseite
        s.sendall(b" RTSP/1.0\r\nCSeq: 2\r\n\r\n")
        try:
            data = s.recv(4096)
        except socket.timeout:
            return None
        return data


fails = 0
for i in range(5):
    fill_buffer_with_marker()
resp = split_url_request()
if resp is None:
    print("  [FEHLER] keine Antwort auf die zweigeteilte Anfrage")
    fails += 1
else:
    status_line = resp.split(b"\r\n", 1)[0]
    leaked = MARK in resp
    print(f"  Statuszeile: {status_line!r}")
    print(f"  [{'FEHLER' if leaked else 'OK'}] Markierung aus fremdem Puffer-Inhalt {'gefunden' if leaked else 'nicht gefunden'} in der Antwort")
    if leaked:
        fails += 1
    # Protokollfeld sollte entweder leer/kurz oder ein plausibles Token sein, nie 8 Byte Zufallsmuell mit hohen Bytes
    proto_guess = status_line.split(b" ", 1)[0]
    print(f"  Protokoll-Token in der Statuszeile: {proto_guess!r}")

print("ERGEBNIS: " + ("BESTANDEN" if fails == 0 else "FEHLER"))
sys.exit(0 if fails == 0 else 1)
