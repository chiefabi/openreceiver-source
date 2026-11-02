#!/usr/bin/env bash
# Baut ein MINIMALES FFmpeg unter LGPL: nur die Decoder, die der OpenReceiver braucht
# (AAC inkl. AAC-ELD, ALAC, H.264). Keine Encoder, keine externen Bibliotheken, kein Netzwerk.
set -euo pipefail
FFVER="${1:?FFmpeg-Version angeben, z. B. 8.1.3}"
B=/f/claude/airplay-build
SRC="$B/src/ffmpeg-$FFVER"
PREFIX="$B/prefix/ffmpeg-min"

mkdir -p "$B/src" "$PREFIX"
cd "$B/src"
[ -d "$SRC" ] || tar xf "ffmpeg-$FFVER.tar.xz"
cd "$SRC"
make distclean >/dev/null 2>&1 || true

./configure \
  --prefix="$PREFIX" \
  --disable-everything --disable-autodetect --disable-programs --disable-doc --disable-debug \
  --disable-network --disable-avdevice --disable-swscale --disable-swresample \
  --enable-shared --disable-static \
  --enable-avcodec --enable-avformat --enable-avfilter \
  --enable-decoder=aac,aac_latm,alac,h264 \
  --enable-parser=aac,aac_latm,h264 \
  --enable-filter=null,anull \
  --extra-cflags="-O2" 2>&1 | tail -n 25

make -j"$(nproc)" 2>&1 | tail -n 5
make install 2>&1 | tail -n 3
echo "=== FFmpeg fertig: $PREFIX"
