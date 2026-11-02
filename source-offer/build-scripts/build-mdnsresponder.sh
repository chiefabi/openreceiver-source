#!/usr/bin/env bash
# Baut Apples mDNSResponder (Apache-2.0) fuer Windows mit MinGW (MSYS2 UCRT64): mDNSResponder.exe (laeuft im Direktmodus,
# ohne Windows-Dienst und ohne Administratorrechte) und dnssd.dll (Client-Bibliothek, Schnittstelle wie Apples Bonjour).
# Aufruf: build-mdnsresponder.sh [Version] [Ausgabeordner] [TCP-Port]   (Port nur fuer Tests, Standard 5354 wie bei Bonjour)
set -euo pipefail
VER="${1:-2881.120.11}"
OUT="${2:-/f/claude/airplay-build/mdns-out}"
PORT="${3:-}"
B=/f/claude/airplay-build
T=/f/claude/airplay/tools/build-engine
SRC="$B/src/mDNSResponder-$VER"

cd "$B/src"
rm -rf "$SRC"; tar xf "mDNSResponder-$VER.tar.gz"
cd "$SRC"
for p in "$T"/patches/mDNSResponder-$VER-*.patch; do echo "Patch: $(basename "$p")"; patch -p1 < "$p"; done

GEN="$B/src/mdns-gen-$VER"; rm -rf "$GEN"; mkdir -p "$GEN" "$OUT"
windmc -h "$GEN" -r "$GEN" mDNSWindows/SystemService/EventLog.mc   # Meldungs-Kopf EventLog.h (bei Apple vom MSVC-Meldungscompiler)

EXTRA=""; [ -n "$PORT" ] && EXTRA="-DMDNS_TCP_SERVERPORT=$PORT"
INC="-ImDNSCore -ImDNSShared -ImDNSShared/utilities -ImDNSWindows -ImDNSWindows/SystemService -I$GEN"
OBJ="$B/src/mdns-obj-$VER"; rm -rf "$OBJ"; mkdir -p "$OBJ/exe" "$OBJ/dll"

# --- mDNSResponder.exe (Dienstprogramm, hier im Direktmodus "-server") ---
DEXE="$EXTRA -DWIN32 -DNDEBUG -D_CONSOLE -D_WIN32_WINNT=0x0600 -DTARGET_OS_WIN32 -DWIN32_LEAN_AND_MEAN -DUSE_TCP_LOOPBACK -DPLATFORM_NO_STRSEP -DPLATFORM_NO_EPIPE -DPLATFORM_NO_RLIMIT -DPID_FILE=\"\" -DUNICODE -D_UNICODE -D_CRT_SECURE_NO_DEPRECATE -D_WINSOCK_DEPRECATED_NO_WARNINGS"
for f in mDNSCore/mDNS.c mDNSCore/uDNS.c mDNSCore/DNSCommon.c mDNSCore/DNSDigest.c mDNSShared/uds_daemon.c mDNSShared/ClientRequests.c \
         mDNSShared/dnssd_ipc.c mDNSShared/mDNSDebug.c mDNSShared/DebugServices.c mDNSShared/GenLinkedList.c \
         mDNSWindows/mDNSWin32.c mDNSWindows/Poll.c mDNSWindows/PosixCompat.c mDNSWindows/Secret.c \
         mDNSWindows/SystemService/Service.c mDNSWindows/SystemService/main.c "$T/mdns/firewall_stub.c"; do
  gcc -std=gnu17 -c -w -O2 $DEXE $INC -include stdint.h "$f" -o "$OBJ/exe/$(basename "${f%.*}").o"
done
gcc -municode -s -o "$OUT/mDNSResponder.exe" "$OBJ"/exe/*.o -lws2_32 -liphlpapi -lcrypt32 -lnetapi32 -lpowrprof -ladvapi32 -lole32 -loleaut32 -luuid -lshell32 -luser32

# --- dnssd.dll (Client-Bibliothek, die UxPlay zur Laufzeit laedt) ---
DDLL="$EXTRA -DWIN32 -DNDEBUG -D_WINDOWS -D_USRDLL -DMDNS_DEBUGMSGS=0 -DWIN32_LEAN_AND_MEAN -DUSE_TCP_LOOPBACK -D_CRT_SECURE_NO_DEPRECATE -D_WINSOCK_DEPRECATED_NO_WARNINGS -DNOT_HAVE_SA_LEN -D_WIN32_WINNT=0x0600 -DTARGET_OS_WIN32"
for f in mDNSShared/dnssd_clientlib.c mDNSShared/dnssd_clientstub.c mDNSShared/dnssd_ipc.c mDNSShared/DebugServices.c mDNSShared/GenLinkedList.c mDNSWindows/DLL/dllmain.c; do
  gcc -std=gnu17 -c -w -O2 $DDLL $INC -include stdint.h "$f" -o "$OBJ/dll/$(basename "${f%.*}").o"
done
gcc -shared -s -o "$OUT/dnssd.dll" "$OBJ"/dll/*.o mDNSWindows/DLL/dnssd.def -lws2_32 -liphlpapi -ladvapi32 -static-libgcc
cp LICENSE "$OUT/LICENSE-mDNSResponder.txt"
ls -la "$OUT"
