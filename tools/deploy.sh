#!/bin/bash
# Publish the app to https://theramlakhan.com/projects/bill-studio/
# Copies only the runtime files into the GitHub Pages site repo under projects/bill-studio/.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SITE_REPO="ramlakhanmadheshiya/ramlakhanmadheshiya.github.io"
DEST="projects/bill-studio"
WORK="${TMPDIR:-/tmp}/bill-studio-deploy"

python3 "$ROOT/tools/build-sw.py" >/dev/null && python3 "$ROOT/tools/build-sw.py"
python3 "$ROOT/tools/build-offline.py"
rm -rf "$WORK"
gh repo clone "$SITE_REPO" "$WORK" -- --depth 1 --quiet
rm -rf "$WORK/$DEST" && mkdir -p "$WORK/$DEST"
cp -R "$ROOT/index.html" "$ROOT/sw.js" "$ROOT/manifest.webmanifest" "$ROOT/assets" "$WORK/$DEST/"
mkdir -p "$WORK/$DEST/downloads" && cp "$ROOT/dist/Bill-Studio-offline.html" "$ROOT/dist/bill-studio-offline.zip" "$WORK/$DEST/downloads/"
find "$WORK/$DEST" -name .DS_Store -delete
cd "$WORK"
git add "$DEST"
if git diff --cached --quiet; then echo "Nothing changed — already up to date."; exit 0; fi
git commit -q -m "Bill Studio: deploy $(cd "$ROOT" && git rev-parse --short HEAD 2>/dev/null || date +%Y%m%d%H%M)"
git push -q origin HEAD
echo "Deployed → https://theramlakhan.com/$DEST/"
