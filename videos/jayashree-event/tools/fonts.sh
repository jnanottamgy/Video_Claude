#!/usr/bin/env bash
# The title fonts as TTF for PIL (all SIL Open Font License), from the @fontsource npm packages:
# Cinzel 500/700, Marcellus 400, Cormorant Garamond 500/600/700 and 500 italic, Noto Serif Kannada 500/700.
#   tools/fonts.sh  ->  renders/fonts/*.ttf
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p renders/fonts
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
(cd "$T" && for p in cinzel marcellus cormorant-garamond noto-serif-kannada; do
   npm pack --silent "@fontsource/$p@5.3.0" > /dev/null
 done && for t in *.tgz; do mkdir -p "${t%.tgz}" && tar xzf "$t" -C "${t%.tgz}"; done)
python3 - "$T" <<'PY'
import glob, os, sys
from fontTools.ttLib import TTFont
for w in ["cinzel-latin-500-normal", "cinzel-latin-700-normal", "marcellus-latin-400-normal",
          "cormorant-garamond-latin-500-normal", "cormorant-garamond-latin-600-normal",
          "cormorant-garamond-latin-700-normal", "cormorant-garamond-latin-500-italic",
          "noto-serif-kannada-kannada-500-normal", "noto-serif-kannada-kannada-700-normal"]:
    src = glob.glob(os.path.join(sys.argv[1], "*", "package", "files", w + ".woff2"))[0]
    t = TTFont(src)
    t.flavor = None
    t.save(os.path.join("renders/fonts", w + ".ttf"))
    print(w)
PY
