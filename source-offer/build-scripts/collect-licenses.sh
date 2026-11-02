#!/usr/bin/env bash
# Liest für jede DLL der Engine Paketname, Version, Lizenz und URL aus der MSYS2-Paketdatenbank.
# Eingabe: Textdatei mit DLL-Namen (eine pro Zeile). Ausgabe: TSV (Datei, Paket, Version, Lizenz, URL).
set -uo pipefail
LIST="${1:?Liste der DLL-Namen}"
OUT="${2:?Ausgabe-TSV}"
export LC_ALL=C
: > "$OUT"
declare -A INFO
while IFS= read -r name; do
  name="${name%$'\r'}"; [ -z "$name" ] && continue
  path=""
  for d in /ucrt64/bin /ucrt64/lib/gstreamer-1.0; do [ -f "$d/$name" ] && path="$d/$name" && break; done
  if [ -z "$path" ]; then printf '%s\t(eigener Build)\t\t\t\n' "$name" >> "$OUT"; continue; fi
  pkg="$(pacman -Qoq "$path" 2>/dev/null | head -n1)"
  if [ -z "$pkg" ]; then printf '%s\t(unbekannt)\t\t\t\n' "$name" >> "$OUT"; continue; fi
  if [ -z "${INFO[$pkg]+x}" ]; then
    q="$(pacman -Qi "$pkg")"
    ver="$(printf '%s\n' "$q" | sed -n 's/^Version *: *//p' | head -n1)"
    lic="$(printf '%s\n' "$q" | sed -n 's/^Licenses *: *//p' | head -n1)"
    url="$(printf '%s\n' "$q" | sed -n 's/^URL *: *//p' | head -n1)"
    INFO[$pkg]="$ver"$'\t'"$lic"$'\t'"$url"
  fi
  printf '%s\t%s\t%s\n' "$name" "$pkg" "${INFO[$pkg]}" >> "$OUT"
done < "$LIST"
echo "geschrieben: $OUT ($(wc -l < "$OUT") Zeilen)"
