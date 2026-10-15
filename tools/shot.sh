#!/bin/bash
# Usage: tools/shot.sh <url> <out.png> [width] [height] [profile-dir]
# Screenshot a page with headless Chrome and print browser console errors.
URL="$1"; OUT="$2"; W="${3:-1440}"; H="${4:-1000}"; PROFILE="${5:-/tmp/bs-chrome-profile}"
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --disable-gpu --hide-scrollbars \
  --user-data-dir="$PROFILE" --enable-logging=stderr --v=0 --timeout=7000 \
  --window-size=$W,$H --screenshot="$OUT" "$URL" 2>&1 | grep -E "CONSOLE|Uncaught|SyntaxError|TypeError|ReferenceError|Failed to load" | sed 's/^.*CONSOLE/CONSOLE/' | head -30
echo "shot: $OUT"
