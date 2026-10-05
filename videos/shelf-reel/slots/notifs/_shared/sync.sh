#!/usr/bin/env bash
# Copy the shared v2 WhatsApp kit into every notifs project (each project must be self-contained).
#   wa-kit.css / wa-kit.js   the iOS-dark WhatsApp banner + keyframe sampler  -> cards, storm, storm_hook
#   wa-storm.js              the storm planner + choreography engine          -> storm, storm_hook
# (notif-kit.* / notif-storm.js are the retired v1 kit, kept here for reference only.)
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
for p in cards storm storm_hook; do
  mkdir -p "$here/../$p/lib"
  rm -f "$here/../$p/lib/notif-kit.css" "$here/../$p/lib/notif-kit.js" "$here/../$p/lib/notif-storm.js"
  cp "$here/wa-kit.css" "$here/wa-kit.js" "$here/../$p/lib/"
  if [ "$p" != cards ] && [ -f "$here/wa-storm.js" ]; then cp "$here/wa-storm.js" "$here/../$p/lib/"; fi
done
echo "synced wa-kit -> cards, storm, storm_hook"
