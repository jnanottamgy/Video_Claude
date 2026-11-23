#!/usr/bin/env bash
# Fonts as TTF for PIL (all SIL Open Font License), from the @fontsource npm packages:
# Anton 400 (big words), JetBrains Mono 400/700 (HUD), Instrument Serif 400 italic (contrast words), Inter 600/800.
#   tools/fonts.sh  ->  renders/fonts/*.ttf
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p renders/fonts
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
(cd "$T" && for p in anton jetbrains-mono instrument-serif inter; do
   npm pack --silent "@fontsource/$p@5.2.5" > /dev/null 2>&1 || npm pack --silent "@fontsource/$p" > /dev/null
 done && for t in *.tgz; do mkdir -p "${t%.tgz}" && tar xzf "$t" -C "${t%.tgz}"; done)
python3 - "$T" <<'PY'
import glob, os, sys
from fontTools.ttLib import TTFont
for w in ["anton-latin-400-normal", "jetbrains-mono-latin-400-normal", "jetbrains-mono-latin-700-normal",
          "instrument-serif-latin-400-italic", "instrument-serif-latin-400-normal", "inter-latin-600-normal",
          "inter-latin-800-normal"]:
    src = glob.glob(os.path.join(sys.argv[1], "*", "package", "files", w + ".woff2"))[0]
    t = TTFont(src)
    t.flavor = None
    t.save(os.path.join("renders/fonts", w + ".ttf"))
    print(w)
PY
