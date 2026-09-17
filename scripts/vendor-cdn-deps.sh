#!/usr/bin/env bash
# Vendor CDN <script src> dependencies into a composition so it renders offline.
#
# Why: HyperFrames scaffolds load GSAP (and friends) from cdn.jsdelivr.net. Some
# sandboxed networks — including Claude Code web sessions — block public CDNs, and
# the render then fails its correctness gate with:
#     sub_timeline_script_failure: A sub-composition timeline script failed to load
# The npm registry is usually still reachable, so we pull the same package from npm
# and rewrite the tag to a relative path.
#
# Usage:  scripts/vendor-cdn-deps.sh <project-dir>     (default: current directory)
set -euo pipefail

PROJ="${1:-.}"
HTML="$PROJ/index.html"
[ -f "$HTML" ] || { echo "No index.html in $PROJ" >&2; exit 1; }

mkdir -p "$PROJ/vendor"
changed=0

# Matches https://cdn.jsdelivr.net/npm/<pkg>@<ver>/<path> and unpkg equivalents.
grep -oE 'https://(cdn\.jsdelivr\.net/npm|unpkg\.com)/[^"'"'"']+' "$HTML" 2>/dev/null | sort -u | while read -r url; do
  spec="${url#*/npm/}"; spec="${spec#*unpkg.com/}"
  pkgver="${spec%%/*}"                      # e.g. gsap@3.14.2
  inner="${spec#*/}"                        # e.g. dist/gsap.min.js
  file="$(basename "$inner")"
  [ "$pkgver" = "$spec" ] && continue

  echo "  vendoring $pkgver -> vendor/$file"
  tmp="$(mktemp -d)"
  ( cd "$tmp" && npm pack "$pkgver" --silent >/dev/null 2>&1 ) || { echo "    npm pack failed for $pkgver" >&2; rm -rf "$tmp"; continue; }
  tgz="$(find "$tmp" -name '*.tgz' | head -1)"
  tar -xzf "$tgz" -C "$tmp" "package/$inner" 2>/dev/null || { echo "    $inner not in tarball" >&2; rm -rf "$tmp"; continue; }
  cp "$tmp/package/$inner" "$PROJ/vendor/$file"
  rm -rf "$tmp"

  # Rewrite the tag to the local copy.
  python3 - "$HTML" "$url" "./vendor/$file" <<'PY'
import sys, pathlib
html, old, new = sys.argv[1], sys.argv[2], sys.argv[3]
p = pathlib.Path(html)
p.write_text(p.read_text().replace(old, new))
PY
  changed=1
done

echo "Done. Re-run: npx hyperframes render"
