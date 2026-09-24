#!/bin/bash
# SessionStart フック: GitHub にこのツールの新しい版があるかを確認して知らせる。
# 確認するだけで、ファイルは一切変更しない (更新は update スキルで利用者の同意を得てから行う)。
# ネットワークがない・git がない等のときは何も出さずに終わる (起動を邪魔しない)。

cd "${CLAUDE_PROJECT_DIR:-$(dirname "$0")/../..}" 2>/dev/null || exit 0

# $1: 利用者に見せるメッセージ (空なら見せない) / $2: AI に渡す文脈
# 文言は固定文 + 数字だけなので、JSON のエスケープは不要
emit() {
  if [ -n "$1" ]; then
    printf '{"systemMessage":"%s","hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"%s"}}\n' "$1" "$2"
  else
    printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"%s"}}\n' "$2"
  fi
}

if [ ! -d .git ]; then
  emit "" "このフォルダは git で管理されていない (ZIP でダウンロードした版) ため、更新の有無は確認できない。利用者が更新したいと言ったら update スキルの ZIP 版の手順で案内する。"
  exit 0
fi

command -v git >/dev/null 2>&1 || exit 0
git rev-parse --abbrev-ref --symbolic-full-name '@{u}' >/dev/null 2>&1 || exit 0

GIT_TERMINAL_PROMPT=0 git -c http.lowSpeedLimit=1000 -c http.lowSpeedTime=5 fetch --quiet 2>/dev/null || exit 0

behind=$(git rev-list --count 'HEAD..@{u}' 2>/dev/null || echo 0)
[ "$behind" -gt 0 ] 2>/dev/null || exit 0

emit "🔔 このツールの新しい版があります (${behind} 件の更新)。「更新したい」と伝えると最新にできます。" \
  "GitHub にこのツールの新しい更新が ${behind} 件ある。利用者の最初の依頼に答える前か後に、update スキルで最新にするか一言だけ提案する (勝手に更新しない)。"
exit 0
