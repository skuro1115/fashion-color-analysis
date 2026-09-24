---
name: run-analysis
description: ツール実行モード。images/ の画像で分析ツールを実行し、事前チェックと結果の要約まで行う。「分析して」「実行して」「解析を回して」「結果を出して」「設定を変えてもう一度」と言われたときに使う。コードは変更しない。
---

# ツール実行モード

利用者の代わりに分析を実行し、結果を分かりやすく要約する。**コードは変更しない。**
`config.yaml` を変えるのは利用者が頼んだときだけで、変更前に内容を見せて確認を取る。

## 1. 事前チェック（実行前に必ず）

- `images/` の画像枚数。0 枚なら止めて、入れ方（`images/README.txt`）を案内する
- フォルダ名の読み取り結果を集計して見せる。意図と違う読み取りがないか確認する：

ライブラリ入りの Python で実行する（`uv run python` / なければ `.venv-run/bin/python`。どちらもなければ先に 2. の実行で環境を作る）。

```bash
PYTHONPATH=src uv run python - <<'EOF'
from collections import Counter
from pathlib import Path
import yaml
from fca.image_processing.loader import scan_images
meta = yaml.safe_load(open("config.yaml", encoding="utf-8")).get("metadata", {})
recs = scan_images(Path("images"), **meta)
print(len(recs), "枚")
for key in ("brand", "year", "season", "gender"):
    c = Counter(getattr(r, key) or "(未指定)" for r in recs)
    print(key, dict(c.most_common()))
EOF
```

  - 例：時期のつもりの `2018_summer2` がブランドとして読まれている → フォルダ名の直し方か、`config.yaml` の `metadata.seasons` への追加を提案
- 画像が多いとき（数百枚以上）はおおよその時間を伝える（1枚 0.2 秒前後 + 初回セットアップ数分）

## 2. 実行

- 開発環境があれば：`uv run fca run`
- なければ：`FCA_NO_OPEN=1 ./run.command < /dev/null`（初回は環境構築に数分かかる）
- 設定のうち `analysis:` / `dataset:` だけを変えた場合は、画像解析をやり直さず `uv run fca analyze && uv run fca preview`
  （または `PYTHONPATH=src .venv-run/bin/python -m fca analyze` と `... preview`）
- エラーは `output/logs/error_*.log` を読み、原因を平易に説明する。コードの不具合なら「要望 / 修正依頼」として伝え、このモードでは直さない

## 3. 結果の要約（5〜8 行）

`output/images.csv` と `output/dataset.csv` を読んで伝える：

- 処理枚数、review の枚数と多い理由（`review_reasons`、表示名は `src/fca/reporting/preview.py` の `REASON_LABELS`）
- ブランド・年代・性別ごとの枚数と、よく出るメイン色（hex と大まかな色名）
- 気になる点（例：特定ブランドで review が多い、サブ色がほとんど出ていない）
- 最後に確認ページを開くか聞く（`open output/preview.html`）

数字は必ずファイルから読んだ値を使い、推測で書かない。
