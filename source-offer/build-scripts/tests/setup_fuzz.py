"""Prueft, dass die Engine (UxPlay) bei fehlerhaften SETUP-/pair-setup-pin-Anfragen nicht abstuerzt, sondern die
Anfrage sauber ablehnt (Laengenpruefung fuer eiv/ekey/epk/authTag, Patch uxplay-1.73.7-setup-data-length-checks).
Aufruf: python -I setup_fuzz.py <port>   (Engine muss bereits auf 127.0.0.1:<port> auf RTSP-Anfragen warten, RTSP ohne PIN)
Exit 0, wenn alle Anfragen eine Antwort bekommen (die Verbindung also nicht kommentarlos abbricht) und das
Steuersocket danach fuer eine normale OPTIONS-Anfrage weiterhin antwortet (Engine ist nicht abgestuerzt).
"""
import plistlib, socket, sys, time

HOST = "127.0.0.1"
PORT = int(sys.argv[1])


def rtsp(method, path, body=b"", content_type=None, cseq=1, timeout=5.0):
    """Schickt eine RTSP-Anfrage auf einer neuen Verbindung und gibt (status_line, headers, body) oder None (keine Antwort) zurueck."""
    headers = [f"{method} {path} RTSP/1.0", f"CSeq: {cseq}", "User-Agent: setup_fuzz.py"]
    if content_type:
        headers.append(f"Content-Type: {content_type}")
    headers.append(f"Content-Length: {len(body)}")
    req = ("\r\n".join(headers) + "\r\n\r\n").encode("ascii") + body
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        s.connect((HOST, PORT))
        s.sendall(req)
        try:
            data = s.recv(65536)
        except socket.timeout:
            return None
        if not data:
            return None
        head = data.split(b"\r\n\r\n", 1)[0].decode("latin1")
        return head.splitlines()[0] if head else "(leer)"


def bplist(d):
    return plistlib.dumps(d, fmt=plistlib.FMT_BINARY)


cases = []

# 1) SETUP, erste Phase: eiv/ekey jeweils zu kurz (Soll: keine Daten kopiert, keine Antwort fehlt)
for eiv_len, ekey_len in [(0, 0), (1, 1), (15, 71), (17, 73)]:
    body = bplist({
        "deviceID": "AA:BB:CC:DD:EE:FF",
        "model": "fuzz",
        "name": "fuzz-client",
        "eiv": bytes(eiv_len),
        "ekey": bytes(ekey_len),
        "timingProtocol": "NTP",
        "timingPort": 7000,
    })
    cases.append((f"SETUP mit eiv={eiv_len}B ekey={ekey_len}B", "SETUP", "rtsp://127.0.0.1/", body, "application/x-apple-binary-plist"))

# 2) pair-setup-pin, dritter Schritt: epk/authTag jeweils zu kurz
for epk_len, tag_len in [(0, 0), (31, 16), (32, 15), (1, 1)]:
    body = bplist({"epk": bytes(epk_len), "authTag": bytes(tag_len)})
    cases.append((f"pair-setup-pin(3) mit epk={epk_len}B authTag={tag_len}B", "POST", "/pair-setup-pin", body, "application/x-apple-binary-plist"))

# 3) leerer/kaputter Plist-Rumpf (plist_from_bin mit Muell)
cases.append(("SETUP mit kaputtem Plist (kein bplist00)", "SETUP", "rtsp://127.0.0.1/", b"\x00\x01\x02garbage", "application/x-apple-binary-plist"))
cases.append(("pair-setup-pin mit leerem Rumpf", "POST", "/pair-setup-pin", b"", "application/x-apple-binary-plist"))

fails = 0
for label, method, path, body, ctype in cases:
    resp = rtsp(method, path, body, ctype)
    ok = resp is not None
    print(f"  [{'OK' if ok else 'FEHLER'}] {label}: {'keine Antwort/Verbindung abgebrochen' if not ok else resp}")
    if not ok:
        fails += 1
    time.sleep(0.05)

# Nach allen fehlerhaften Anfragen muss die Engine noch auf eine normale OPTIONS-Anfrage antworten (kein Absturz).
alive = rtsp("OPTIONS", "*", cseq=999)
ok_alive = alive is not None and alive.startswith("RTSP/1.0 200")
print(f"  [{'OK' if ok_alive else 'FEHLER'}] Engine antwortet nach allen Tests noch normal (OPTIONS): {alive}")
if not ok_alive:
    fails += 1

print("ERGEBNIS: " + ("BESTANDEN" if fails == 0 else "FEHLER"))
sys.exit(0 if fails == 0 else 1)
