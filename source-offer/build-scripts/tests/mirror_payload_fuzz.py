"""Prueft die Laengenpruefung des payload_size-Feldes im TCP-Datenstrom des Video-Mirrorings (raop_rtp_mirror.c).
Baut eine echte RTSP-SETUP-Anfrage (wie ein iPhone sie fuer Mirroring schickt), liest den zugewiesenen
Mirror-Datenport aus der Antwort, verbindet sich dorthin und schickt einen 128-Byte-Kopf mit einem
unplausiblen payload_size-Wert (negativ bzw. riesig). Ohne den Patch
uxplay-1.73.7-mirror-payload-size-bound fuehrte das zu einem NULL-Zeiger (fehlgeschlagenes malloc) oder
zu mehreren Gigabyte Speicherzuweisung pro Verbindung.
Aufruf: python -I mirror_payload_fuzz.py <rtsp_port>
"""
import plistlib, socket, struct, sys, time

HOST = "127.0.0.1"
PORT = int(sys.argv[1])


def rtsp(sock, method, path, body=b"", content_type=None, cseq=1):
    headers = [f"{method} {path} RTSP/1.0", f"CSeq: {cseq}"]
    if content_type:
        headers.append(f"Content-Type: {content_type}")
    headers.append(f"Content-Length: {len(body)}")
    req = ("\r\n".join(headers) + "\r\n\r\n").encode("ascii") + body
    sock.sendall(req)
    data = sock.recv(65536)
    head, _, rest = data.partition(b"\r\n\r\n")
    return head.decode("latin1"), rest


ctrl = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
ctrl.settimeout(10.0)
ctrl.connect((HOST, PORT))

setup_body = plistlib.dumps({
    "deviceID": "AA:BB:CC:DD:EE:FF",
    "model": "fuzz",
    "name": "fuzz-client",
    "eiv": bytes(16),
    "ekey": bytes(72),
    "timingProtocol": "NTP",
    "timingPort": 7000,
    "streams": [{"type": 110, "streamConnectionID": 12345}],
}, fmt=plistlib.FMT_BINARY)

status, body = rtsp(ctrl, "SETUP", "rtsp://127.0.0.1/", setup_body, "application/x-apple-binary-plist", cseq=1)
print(f"  SETUP-Antwort: {status}")
if "200" not in status:
    print("ERGEBNIS: FEHLER (SETUP nicht erfolgreich, kann Mirror-Port nicht ermitteln)")
    sys.exit(1)

resp = plistlib.loads(body, fmt=plistlib.FMT_BINARY)
data_port = None
for s in resp.get("streams", []):
    if s.get("type") == 110:
        data_port = s.get("dataPort")
print(f"  Mirror-Datenport laut Antwort: {data_port}")
if not data_port:
    print("ERGEBNIS: FEHLER (kein dataPort in der Antwort)")
    sys.exit(1)

fails = 0
# Der Mirror-Datenport nimmt pro Sitzung nur eine Verbindung an; nach der ersten (boesartigen) schliesst
# die Engine die Sitzung. Fuer mehrere Faelle muesste pro Fall neu per SETUP eine Sitzung aufgebaut werden -
# hier genuegt ein Fall, um zu zeigen, dass die Engine nicht abstuerzt.
label, size_bytes = "payload_size = -1 (0xFFFFFFFF)", struct.pack("<i", -1)
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.settimeout(5.0)
    try:
        s.connect((HOST, data_port))
        header = size_bytes + bytes(124)  # 128-Byte-Kopf, Rest irrelevant fuer diesen Test
        s.sendall(header)
    except OSError as e:
        print(f"  [FEHLER] {label}: {e}")
        fails += 1
    time.sleep(0.3)
print(f"  [gesendet] {label}")

time.sleep(1.0)
# Pruefen, ob der Steuersocket (dieselbe RTSP-Verbindung) noch antwortet -> Engine insgesamt nicht abgestuerzt
try:
    status2, _ = rtsp(ctrl, "OPTIONS", "*", cseq=99)
    alive = status2.startswith("RTSP/1.0 200")
except OSError:
    alive = False
    status2 = "(keine Antwort)"
print(f"  [{'OK' if alive else 'FEHLER'}] Steuerverbindung antwortet nach den Tests noch: {status2}")
if not alive:
    fails += 1

print("ERGEBNIS: " + ("BESTANDEN" if fails == 0 else "FEHLER"))
sys.exit(0 if fails == 0 else 1)
