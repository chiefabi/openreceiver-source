"""
Regressionstest für die PIN-Kopplung (pair-setup-pin) eines laufenden uxplay.exe.

Verhält sich wie ein iPhone und führt SRP-6a (SHA-1, 2048 Bit, Apple-Variante) mit dem eingegebenen PIN durch:
  Schritt 1: {method: "pin", user: <Geräte-ID>}      -> Server antwortet mit salt + pk (B)
  Schritt 2: {pk: A, proof: M1}                       -> Server soll mit {proof: M2} (20 Byte) antworten
Ein falscher PIN muss abgelehnt werden (Gegenprobe).

Aufruf:  python pair_setup_pin_test.py <port> <pin> [--expect-fail]
Exit-Code 0 = Ergebnis wie erwartet.
"""
import hashlib, os, plistlib, socket, sys

N = int(
    "AC6BDB41324A9A9BF166DE5E1389582FAF72B6651987EE07FC3192943DB56050A37329CBB4"
    "A099ED8193E0757767A13DD52312AB4B03310DCD7F48A9DA04FD50E8083969EDB767B0CF60"
    "95179A163AB3661A05FBD5FAAAE82918A9962F0B93B855F97993EC975EEAA80D740ADBF4FF"
    "747359D041D5C33EA71D281E446B14773BCA97B43A23FB801676BD207A436C6481F1D2B907"
    "8717461A5B9D32E688F87748544523B524B0D57D5EA77A2775D2ECFA032CFBDBF52FB37861"
    "60279004E57AE6AF874E7303CE53299CCC041C7BC308D82A5698F3A8D0C38271AE35F8E9DB"
    "FBB694B5C803D89F7AE435DE236D525F54759B65E372FCD68EF20FA7111F9E4AFF73", 16)
g = 2
LEN_N = (N.bit_length() + 7) // 8


def H(*parts):
    h = hashlib.sha1()
    for p in parts:
        h.update(p)
    return h.digest()


def bn(x):                      # wie BN_bn2bin: ohne führende Nullen
    return x.to_bytes((x.bit_length() + 7) // 8, "big") if x else b""


def pad(x):                     # wie H_nn_rfc5054: auf Länge von N aufgefüllt
    return x.to_bytes(LEN_N, "big")


def num(b):
    return int.from_bytes(b, "big")


def rtsp_post(sock, path, cseq, body):
    head = (f"POST {path} RTSP/1.0\r\nCSeq: {cseq}\r\nUser-Agent: AirPlay/980.77.1\r\n"
            f"Content-Type: application/x-apple-binary-plist\r\nContent-Length: {len(body)}\r\n\r\n").encode()
    sock.sendall(head + body)
    data = b""
    while b"\r\n\r\n" not in data:
        chunk = sock.recv(8192)
        if not chunk:
            return 0, b""                       # Verbindung vom Server geschlossen
        data += chunk
    header, _, rest = data.partition(b"\r\n\r\n")
    status = int(header.split(b" ")[1])
    clen = 0
    for line in header.split(b"\r\n"):
        if line.lower().startswith(b"content-length:"):
            clen = int(line.split(b":")[1])
    while len(rest) < clen:
        chunk = sock.recv(8192)
        if not chunk:
            break
        rest += chunk
    return status, rest[:clen]


def main():
    port, pin = int(sys.argv[1]), sys.argv[2]
    expect_fail = "--expect-fail" in sys.argv
    user = "46:04:C1:95:52:B5"
    s = socket.create_connection(("127.0.0.1", port), timeout=10)

    st, body = rtsp_post(s, "/pair-setup-pin", 1, plistlib.dumps({"method": "pin", "user": user}, fmt=plistlib.FMT_BINARY))
    print(f"Schritt 1: Status {st}")
    if st != 200:
        print("FEHLER: Schritt 1 nicht erfolgreich"); return 1
    r1 = plistlib.loads(body)
    salt, B = r1["salt"], num(r1["pk"])
    print(f"  salt {len(salt)} Byte, B {len(r1['pk'])} Byte")

    # SRP-6a Client (rfc5054-kompatibel, Apple-Sitzungsschlüssel)
    x = num(H(bn(num(salt)), H(user.encode(), b":", pin.encode())))
    a = num(os.urandom(32))
    A = pow(g, a, N)
    k = num(H(pad(N), pad(g)))
    u = num(H(pad(A), pad(B)))
    S = pow((B - k * pow(g, x, N)) % N, a + u * x, N)
    Sb = bn(S)
    K = H(Sb, b"\0\0\0\0") + H(Sb, b"\0\0\0\1")                          # 40 Byte
    H_xor = bytes(p ^ q for p, q in zip(H(bn(N)), H(bn(g))))
    M1 = H(H_xor, H(user.encode()), bn(num(salt)), bn(A), bn(B), K)       # 20 Byte
    print(f"  Client-Beweis M1: {len(M1)} Byte")

    st, body = rtsp_post(s, "/pair-setup-pin", 2, plistlib.dumps({"pk": bn(A), "proof": M1}, fmt=plistlib.FMT_BINARY))
    print(f"Schritt 2: Status {st}")
    if st != 200:
        print("-> Server hat den Beweis abgelehnt bzw. die Verbindung geschlossen")
        ok = expect_fail
        print("ERGEBNIS:", "wie erwartet (abgelehnt)" if ok else "FEHLGESCHLAGEN")
        return 0 if ok else 1
    M2 = plistlib.loads(body)["proof"]
    expected = H(bn(A), M1, K)
    good = (len(M2) == 20 and M2 == expected)
    print(f"  Server-Beweis M2: {len(M2)} Byte, stimmt mit Erwartung überein: {good}")
    if expect_fail:
        print("ERGEBNIS: FEHLGESCHLAGEN (falscher PIN wurde akzeptiert)"); return 1
    print("ERGEBNIS:", "PIN-Kopplung bis Schritt 2 erfolgreich (gegenseitige Authentifizierung OK)" if good else "FEHLGESCHLAGEN")
    return 0 if good else 1


sys.exit(main())
