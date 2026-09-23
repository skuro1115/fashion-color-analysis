#!/bin/bash
# Fashion Color Analysis — Mac でダブルクリックして実行するスクリプト
#
#   画像チェック → Python 確認 → 実行環境(.venv-run)作成 → ライブラリ導入 → 解析 → 結果を開く
#
# 2回目以降はセットアップを省略する (requirements.txt が変わったときだけ再インストール)。
# 解析ロジックはここに書かない (src/fca/pipeline.py を呼ぶだけ)。
# 環境変数 FCA_NO_OPEN=1 で、終了時に Finder/ブラウザを開かない (テスト用)。

cd "$(dirname "$0")" || exit 1

VENV=".venv-run"          # uv 開発用の .venv とは分ける
STAMP="$VENV/.installed-requirements"
PIP_LOG="$VENV/pip-install.log"

# ダブルクリック起動だと PATH が最小限なので、よくある Python の場所を足す
export PATH="/opt/homebrew/bin:/usr/local/bin:/Library/Frameworks/Python.framework/Versions/Current/bin:$PATH"

bold() { printf "\033[1m%s\033[0m\n" "$1"; }
step() { printf "\n\033[1;34m▶ %s\033[0m\n" "$1"; }
fail() {
  printf "\n\033[1;31m✖ %s\033[0m\n" "$1"
  shift
  for line in "$@"; do echo "  $line"; done
  echo "  困ったときは docs/troubleshooting.md を見てください。"
  finish 1
}
finish() {
  echo
  if [ -t 0 ]; then read -r -p "Enter キーを押すとこの画面を閉じられます " _; fi
  exit "${1:-0}"
}
open_if_allowed() { [ "$FCA_NO_OPEN" = "1" ] || open "$@"; }

bold "==== Fashion Color Analysis ===="

# ---- 1. 画像があるか -------------------------------------------------------
step "画像を確認しています"
mkdir -p images
count=$(find images -type f \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' -o -iname '*.webp' \) \
  ! -path '*/.*' 2>/dev/null | wc -l | tr -d ' ')
if [ "$count" = "0" ]; then
  open_if_allowed images
  fail "images フォルダに画像がありません" \
    "今開いた images フォルダに jpg / png / webp の画像を入れてから、" \
    "もう一度 run.command をダブルクリックしてください。"
fi
echo "  画像: ${count} 枚"

# ---- 2. Python があるか ----------------------------------------------------
find_python() {
  for cmd in python3.13 python3.12 python3.11 python3.10 python3; do
    p=$(command -v "$cmd" 2>/dev/null) || continue
    # Mac 標準の /usr/bin/python3 は、開発ツール未導入だとインストール画面が出るだけなので飛ばす
    if [ "$p" = "/usr/bin/python3" ] && ! xcode-select -p >/dev/null 2>&1; then continue; fi
    if "$p" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then
      echo "$p"
      return 0
    fi
  done
  return 1
}

if [ ! -x "$VENV/bin/python" ] || ! "$VENV/bin/python" -c 'import sys' >/dev/null 2>&1; then
  step "Python を確認しています"
  PY=$(find_python) || {
    open_if_allowed "https://www.python.org/downloads/macos/"
    fail "Python が見つかりません" \
      "今開いたページから Python (macOS 用インストーラ) を入れてください。" \
      "インストール後、もう一度 run.command をダブルクリックしてください。"
  }
  echo "  $("$PY" --version 2>&1) ($PY)"

  step "実行環境を作っています (初回のみ)"
  rm -rf "$VENV"
  "$PY" -m venv "$VENV" >/dev/null 2>&1 || fail "実行環境 (.venv-run) を作れませんでした" \
    "フォルダが書き込み禁止の場所 (ダウンロード中の ZIP の中など) にないか確認してください。"
fi

# ---- 3. ライブラリ ---------------------------------------------------------
req_hash=$(shasum requirements.txt | cut -d' ' -f1)
libs_ok() { "$VENV/bin/python" -c 'import numpy, cv2, PIL, sklearn, skimage, yaml' >/dev/null 2>&1; }
if [ "$(cat "$STAMP" 2>/dev/null)" != "$req_hash" ] || ! libs_ok; then
  step "必要なライブラリをインストールしています (初回は数分かかります)"
  {
    "$VENV/bin/python" -m pip install --upgrade pip &&
    "$VENV/bin/python" -m pip install -r requirements.txt
  } >"$PIP_LOG" 2>&1 || {
    tail -n 5 "$PIP_LOG" | sed 's/^/    /'
    fail "依存ライブラリのインストールに失敗しました" \
      "インターネットに接続されているか確認して、もう一度実行してください。" \
      "詳しい記録: $PIP_LOG"
  }
  echo "$req_hash" >"$STAMP"
  echo "  完了"
fi

# ---- 4. 解析 ---------------------------------------------------------------
step "解析しています"
PYTHONPATH=src "$VENV/bin/python" -m fca run
rc=$?
if [ $rc -ne 0 ]; then
  # エラー内容は Python 側で分かりやすく表示済み
  fail "解析を完了できませんでした" "上に表示されたメッセージを確認してください。"
fi

# ---- 5. 結果 ---------------------------------------------------------------
printf "\n\033[1;32m✔ 完了しました\033[0m\n"
echo "  結果は output フォルダにあります:"
echo "    preview.html        … ブラウザで結果を確認するページ (自動で開きます)"
echo "    dataset.csv         … 分析用データ: 1画像1行 (メイン色・サブ色と面積、ブランド・年代・性別)"
echo "    images.csv          … 画像ごとの情報・要確認フラグ"
echo "  結果の見方: docs/results-guide.md"
open_if_allowed output/preview.html
open_if_allowed output
finish 0
