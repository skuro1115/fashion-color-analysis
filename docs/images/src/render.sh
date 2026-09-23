#!/bin/bash
# docs/images/src/*.html を docs/images/*.png に書き出す (Google Chrome が必要)
#   使い方: docs/images/src/render.sh [名前 ...]   例: docs/images/src/render.sh run
cd "$(dirname "$0")" || exit 1
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

size() {  # 図ごとの大きさ (CSS px)。PNG はこの 2 倍の解像度になる
  case "$1" in
    setup) echo 1200,420 ;;
    run) echo 1200,540 ;;
    results) echo 1200,620 ;;
    *) echo 1200,600 ;;
  esac
}

names=("$@")
[ ${#names[@]} -eq 0 ] && for f in *.html; do names+=("${f%.html}"); done
for n in "${names[@]}"; do
  "$CHROME" --headless=new --hide-scrollbars --force-device-scale-factor=2 --window-size="$(size "$n")" \
    --screenshot="../$n.png" "file://$PWD/$n.html" 2>/dev/null && echo "docs/images/$n.png"
done
