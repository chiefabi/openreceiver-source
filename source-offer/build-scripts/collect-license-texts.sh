#!/usr/bin/env bash
# Kopiert die Original-Lizenztexte (mit Copyright-Zeilen) aller in der Engine verwendeten MSYS2-Pakete.
# Eingabe: components.tsv (aus collect-licenses.sh). Ausgabe: <Zielordner>\<paket>\...
set -uo pipefail
TSV="${1:?components.tsv}"
DEST="${2:?Zielordner}"
export LC_ALL=C
rm -rf "$DEST"; mkdir -p "$DEST"
cut -f2 "$TSV" | grep -v '^(' | sort -u | while IFS= read -r pkg; do
  short="${pkg#mingw-w64-ucrt-x86_64-}"
  n=0
  while IFS= read -r f; do
    case "$f" in
      *share/licenses/*[!/]) [ -f "$f" ] || continue
        rel="${f#*share/licenses/}"; rel="${rel#*/}"
        mkdir -p "$DEST/$short/$(dirname "$rel")"; cp "$f" "$DEST/$short/$rel"; n=$((n+1));;
    esac
  done < <(pacman -Ql "$pkg" | awk '{print $2}' | sed 's#^/#/#')
  echo "$short: $n Lizenzdatei(en)"
done
