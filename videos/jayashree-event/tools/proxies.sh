#!/usr/bin/env bash
# 1080x1920 SDR working copies of every clip: HLG HDR tone-mapped (hable), SDR passed through, CRF 10.
#   tools/proxies.sh   ->  renders/proxy/<clip>.mp4
set -euo pipefail
cd "$(dirname "$0")/.."
TM="zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p"
one() {
  f=$1; out=renders/proxy/$(basename "${f%.*}").mp4
  [ -s "$out" ] && return 0
  if [ "$(ffprobe -v error -select_streams v:0 -show_entries stream=color_transfer -of csv=p=0 "$f")" = "arib-std-b67" ]; then
    vf="$TM,scale=1080:1920:flags=lanczos"
  else
    vf="scale=1080:1920:flags=lanczos,format=yuv420p"
  fi
  ffmpeg -v error -y -i "$f" -vf "$vf" -c:v libx264 -preset veryfast -crf 10 -color_range tv -colorspace bt709 \
    -color_primaries bt709 -color_trc bt709 -c:a aac -b:a 160k -ar 48000 "$out.tmp.mp4" && mv "$out.tmp.mp4" "$out"
  echo "ok $out"
}
export -f one; export TM
ls renders/src/drive/*.[Mm][Oo][Vv] | xargs -P 4 -I{} bash -c 'one "{}"'
echo DONE
