QUELLCODE-ARCHIV (nur zum Bereitstellen/Hosten, wird NICHT mit dem Programm ausgeliefert)
=======================================================================================

Inhalt: der Quelltext aller selbst gebauten Teile der Engine in genau der ausgelieferten Version.

  UxPlay-1.73.7.tar.gz      UxPlay 1.73.7 (GPL-3.0-or-later)  https://github.com/FDH2/UxPlay
  ffmpeg-8.1.3.tar.xz       FFmpeg 8.1.3, minimal gebaut (LGPL-2.1-or-later)  https://ffmpeg.org
  gst-libav-1.28.8.tar.xz   GStreamer-Plugin libav 1.28.8 (LGPL-2.1-or-later)  https://gstreamer.freedesktop.org
  mDNSResponder-2881.120.11.tar.gz  Apples mDNSResponder (Apache-2.0, Client-Bibliothek BSD-3-Clause) https://github.com/apple-oss-distributions/mDNSResponder
  dns_sd.h                  Bonjour-Header (BSD-3-Clause, Apple), nur zum Übersetzen von UxPlay
  build-scripts\            die Skripte, mit denen alles gebaut wurde (FFmpeg-configure-Optionen stehen in build-ffmpeg.sh)
  components.tsv            Paketliste (Name, Version, Lizenz) der übrigen Bibliotheken aus MSYS2 (UCRT64)

Die übrigen Bibliotheken (GStreamer 1.28.8, GLib, OpenSSL, libplist usw.) stammen unverändert aus den Paketen
der MSYS2-Distribution. Deren Quelltext liegt bei MSYS2: https://repo.msys2.org/mingw/sources/
(Paketnamen und Versionen: siehe components.tsv).

Prüfsummen: SHA256SUMS.txt
