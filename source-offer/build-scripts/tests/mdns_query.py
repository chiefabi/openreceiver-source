"""Fragt per mDNS (Multicast-DNS) nach Diensten und gibt aus, welche Instanznamen antworten.
Aufruf: python -I mdns_query.py <Dienstart, z. B. _airplay._tcp.local> <erwarteter Instanzname-Teil> [Sekunden]
Exit 0, wenn eine Antwort den erwarteten Namen enthaelt. Die Anfrage verlangt eine Unicast-Antwort (QU-Bit),
daher genuegt ein beliebiger lokaler Port."""
import socket, struct, sys, time

def qname(name):
    return b"".join(bytes([len(p)]) + p.encode() for p in name.split(".")) + b"\0"

service, expect = sys.argv[1], sys.argv[2].lower()
secs = float(sys.argv[3]) if len(sys.argv) > 3 else 6
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(("", 0)); s.settimeout(0.5)
pkt = struct.pack(">HHHHHH", 0, 0, 1, 0, 0, 0) + qname(service) + struct.pack(">HH", 12, 0x8001)  # PTR, IN + QU
end = time.time() + secs; found = False; last = 0
while time.time() < end:
    if time.time() - last > 1.5:
        s.sendto(pkt, ("224.0.0.251", 5353)); last = time.time()
    try:
        data, addr = s.recvfrom(9000)
    except socket.timeout:
        continue
    txt = data.decode("latin-1")
    if expect in txt.lower():
        found = True
        print(f"Antwort von {addr[0]}: enthaelt '{expect}' ({len(data)} Byte)")
        break
print("GEFUNDEN" if found else "NICHT GEFUNDEN")
sys.exit(0 if found else 1)
