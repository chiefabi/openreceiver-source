#!/usr/bin/env bash
# Baut UxPlay (Windows, UCRT64). Die Bonjour-Funktionen lädt UxPlay zur Laufzeit selbst aus dnssd.dll (System);
# zum Bauen genügen der offene Header dns_sd.h und eine leere Platzhalter-Bibliothek.
set -euo pipefail
UXVER="${1:?UxPlay-Version angeben, z. B. 1.73.7}"
B=/f/claude/airplay-build
SDK="$B/bonjour-sdk"
SRC="$B/src/UxPlay-$UXVER"

mkdir -p "$SDK/Include" "$SDK/Lib/x64"
cp "$B/src/dns_sd.h" "$SDK/Include/dns_sd.h"
rm -f "$SDK/Lib/x64/dnssd.lib"; ar rcs "$SDK/Lib/x64/dnssd.lib"

cd "$B/src"
rm -rf "$SRC"; tar xf "UxPlay-$UXVER.tar.gz"
cd "$SRC"
# Eigene Korrekturen (siehe patches\): u. a. PIN-Kopplung, die UxPlay 1.73.7 fälschlich ablehnt
for p in /f/claude/airplay/tools/build-engine/patches/uxplay-$UXVER-*.patch; do
  [ -f "$p" ] || continue
  echo "Patch: $(basename "$p")"; patch -p1 < "$p"
done
rm -rf build && mkdir build && cd build
export BONJOUR_SDK_HOME="F:/claude/airplay-build/bonjour-sdk"
cmake -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_C_FLAGS="-O2" -DCMAKE_CXX_FLAGS="-O2" \
  -DCMAKE_EXE_LINKER_FLAGS="-s" .. 2>&1 | tail -n 25
ninja 2>&1 | tail -n 15
ls -la uxplay.exe
