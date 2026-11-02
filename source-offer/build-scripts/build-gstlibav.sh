#!/usr/bin/env bash
# Baut das GStreamer-Plugin "libav" (libgstlibav.dll) gegen unser minimales FFmpeg.
set -euo pipefail
GSTVER="${1:?GStreamer-Version angeben, z. B. 1.28.2}"
B=/f/claude/airplay-build
SRC="$B/src/gst-libav-$GSTVER"
PREFIX="$B/prefix/ffmpeg-min"

cd "$B/src"
[ -d "$SRC" ] || tar xf "gst-libav-$GSTVER.tar.xz"
cd "$SRC"
rm -rf build
export PKG_CONFIG_PATH="$PREFIX/lib/pkgconfig:${PKG_CONFIG_PATH:-}"
meson setup build --buildtype=release -Dtests=disabled -Ddoc=disabled \
  -Dpackage-name="OpenReceiver (gst-libav $GSTVER, minimal LGPL FFmpeg)" \
  -Dpackage-origin="local build" 2>&1 | tail -n 25
ninja -C build 2>&1 | tail -n 5
ls -la build/ext/libav/*.dll
