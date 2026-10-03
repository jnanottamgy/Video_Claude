#!/usr/bin/env bash
# Copy the shared notification-card kit into every notifs project (each must be self-contained).
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
for p in cards storm storm_hook; do
  mkdir -p "$here/../$p/lib"
  cp "$here/notif-kit.css" "$here/notif-kit.js" "$here/../$p/lib/"
  if [ "$p" != cards ]; then cp "$here/notif-storm.js" "$here/../$p/lib/"; fi
done
echo "synced notif-kit -> cards, storm, storm_hook"
