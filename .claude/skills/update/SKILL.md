---
name: update
description: 最新版にするモード。GitHub にあるこのツールの新しい版を取り込む (git pull)。「更新したい」「最新にして」「アップデートして」「新しい版にして」「git pull して」と言われたとき、または起動時に「新しい版があります」と知らせた後に使う。利用者の変更や画像・結果は消さない。
---

# 最新版にするモード

GitHub の新しい版を、利用者の作業を壊さずに取り込む。**push はしない。利用者の変更を消す操作 (reset --hard, checkout -- , clean, 強制上書き) は、同意なしに絶対にしない。**

## 0. 意味を確かめる

「更新したい」は2通りに取れる。はっきりしないときは1行で確認する。

- 最新版を取り込みたい → このモード
- 機能を変えたい・直したい（「〜を更新したい」「CSV を更新したい」など）→ `request` モードか改修へ

## 1. ZIP 版かどうか

`.git` フォルダがなければ ZIP でダウンロードした版なので、git pull はできない。次を案内する：

- **おすすめ**：新しい ZIP をダウンロードし、古いフォルダから `images/` の中身（と、自分で変えていれば `config.yaml` / `manifest.csv`）を新しいフォルダに移す
- **今後もかんたんに更新したい場合**：Claude Code に「このフォルダを GitHub と同期できるようにして」と頼めば、git 管理に切り替えられることを伝える。
  頼まれたら、変更前に手順を説明して同意を得てから行う：
  `git init` → `git remote add origin https://github.com/skuro1115/fashion-color-analysis.git` → `git fetch origin main` →
  `git reset origin/main`（`--hard` にしない。手元のファイルはそのまま残る）→ `git branch --set-upstream-to=origin/main` →
  `git status` で差分を見せ、利用者が変えたファイル以外は `git checkout -- <ファイル>` で最新に戻してよいか確認する

## 2. 現状を確認する（git 版）

```bash
git status --short          # 手元の変更 (images/ と output/ は管理外なので出ない)
git fetch --quiet
git log --oneline HEAD..@{u}    # 取り込まれる更新
git log --oneline @{u}..HEAD    # 手元にしかないコミット
git diff --name-only HEAD @{u}  # 更新で変わるファイル
```

- 取り込む更新が 0 件なら「すでに最新です」と伝えて終わる
- 更新内容をコミットメッセージから **平易な日本語で 3〜5 行に要約** して見せる（例「dataset.csv に色相の列が増えました」）

## 3. 取り込む

| 状況 | すること |
| --- | --- |
| 手元の変更なし・手元だけのコミットなし | `git pull --ff-only` |
| 手元で変えたファイルが、更新で変わるファイルと重ならない | そのまま `git pull --ff-only`（git が変更を残したまま取り込む） |
| 重なる（例：利用者が `config.yaml` を編集していて、更新でも `config.yaml` が変わる） | 状況を説明し、同意を得てから `git stash` → `git pull --ff-only` → `git stash pop`。ぶつかったら利用者の設定値を残す方向で直し、結果を見せて確認する |
| 手元だけのコミットがある（AI で改修して commit 済みなど） | 同意を得てから `git pull --rebase`。ぶつかったら内容を説明して一緒に決める |

迷ったら取り込まずに止めて、状況を説明する。

## 4. 取り込んだ後

- 何が変わったかを短く伝える
- `requirements.txt` が変わっていたら：次に `run.command` を実行したとき自動で入れ直される（数分かかる）と伝える。開発環境があれば `uv sync`
- `.claude/` （モードの手順書・設定）が変わっていたら：Claude Code を開き直すと反映されると伝える
- 開発環境があれば `uv run pytest -q` で動作確認してよい
- 必要なら「分析をやり直しますか？」と `run-analysis` を提案する
