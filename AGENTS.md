# AGENTS.md — AI エージェント向けガイド

人間向けの説明は README.md と docs/。このファイルは AI (Claude Code / Codex 等) がリポジトリを安全に改修するための前提をまとめたもの。
利用者の多くは非エンジニアで、コードを読まずに日本語で要望を伝えてくる。ファイル名を指定されなくても、ここを基に変更箇所を判断すること。

## 目的

ブランドの服画像から代表色を抽出し、ブランド・年代・シーズンごとの色彩傾向を分析できるデータ (CSV) を作る研究用ツール。
正確さより「怪しいものを review=true で人間確認に回す」ことを優先する。重い AI モデル (SAM, YOLO 等) は明示的に頼まれない限り導入しない。

## 4つのモード

利用者の依頼を、まずどのモードかで受け止める。手順の詳細は `.claude/skills/<名前>/SKILL.md`
(Claude Code 以外のエージェントもこのファイルを読んで同じように振る舞うこと)。

| モード | きっかけの例 | すること | しないこと |
| --- | --- | --- | --- |
| 要望を整える (`request`) | 「こんな機能がほしい」「相談したい」 | 質問して `docs/requests/` に要望書を作る | 実装・設定変更 |
| 使い方を理解する (`guide`) | 「どう使うの？」「この結果の意味は？」 | 利用者の実際の状態を見て平易に説明 | ファイル変更 |
| ツールを実行する (`run-analysis`) | 「分析して」「もう一度回して」 | 事前チェック → 実行 → 結果の要約 | コード変更 |
| 最新版にする (`update`) | 「更新したい」「最新にして」 | GitHub の新しい版を安全に取り込む (git pull) | push・利用者の変更の破棄 |
| (改修) | 「実装して」「直して」 | 下記のルールに従って変更・テスト | — |

依頼があいまいなときは、どのモードかを1行で確認してから進める。大きな改修は先に `request` で要望書を作る。
「更新したい」は「最新版を取り込む (update)」と「機能を変える (request / 改修)」のどちらにも取れるので、文脈で判断し、迷えば聞く。

Claude Code では起動時に `.claude/hooks/check-update.sh` (SessionStart フック、`.claude/settings.json`) が GitHub の新しい版を確認し、
あれば利用者に知らせる。確認だけで、更新は必ず `update` モードで同意を得てから行う。

## 将来の道具

① この分析ツール、② データ収集ツール（構想）、③ パワポ作成 skill（構想）。詳細と、道具どうしの受け渡しの約束
(`images/` + `manifest.csv` と `dataset.csv`) は `docs/roadmap.md`。**この約束を壊す変更はしない。**

## 処理フロー

```text
images/[<brand>/][<gender>/][<year>_<season>/]*.jpg   (フォルダは任意・順不同。ないものは未指定)
  │  image_processing/loader.py        画像列挙・パス→メタデータ・manifest.csv 結合・縮小読み込み
  │  image_processing/segmentation.py  外周から背景色推定 → 商品マスク
  │  image_processing/review.py        マスク指標 → review 理由
  │  color_extraction/                 Lab 変換 → K-means (k=10)
  ▼
output/images.csv, raw_colors.csv, masks/, cutouts/     ← extract ステージ
  │  analysis/merge.py                 小クラスタ除外・近似色統合 (画像は読まない)
  │  analysis/dataset.py               images.csv と結合して 1画像1行に (メイン色・サブ色)
  ▼
output/analysis_colors.csv, dataset.csv                  ← analyze ステージ
  │  reporting/preview.py
  ▼
output/preview.html                                      ← preview ステージ
```

## ディレクトリの責務

| パス | 責務 |
| --- | --- |
| `config.yaml` | 利用者が変える値はすべてここ。既定値は `src/fca/config.py` の `DEFAULTS` |
| `src/fca/pipeline.py` | **公開 API**。`run_extract` / `run_analyze` / `build_preview` / `process_image`。CLI・run.command・将来の GUI はここだけを呼ぶ |
| `src/fca/image_processing/` | 画像の読み込み、商品領域抽出、review 判定 |
| `src/fca/color_extraction/` | 色空間変換・ΔE、K-means |
| `src/fca/analysis/` | raw → analysis の後処理。集計 (brand_year_summary 等) を足すならここ |
| `src/fca/reporting/` | CSV 列定義と入出力、preview.html、実行ログ |
| `src/fca/cli/` | argparse と利用者向けメッセージだけ。ロジックを書かない |
| `src/fca/errors.py` | `UserError`: 利用者が直せるエラー。メッセージは非エンジニア向け日本語 |
| `run.command` | Mac 用ダブルクリック起動。環境構築と `python -m fca run` の呼び出しだけ |
| `requirements.txt` | run.command 用の依存。`pyproject.toml` と一致させる (テストで検査) |
| `samples/` | 動作確認用の合成画像 |
| `docs/` | 人間向けドキュメント。`technical.md` が仕様の詳細 |
| `docs/roadmap.md` | 将来の計画と、道具どうしの受け渡しの約束 |
| `docs/requests/` | 要望書 (request モードの成果物)。`TEMPLATE.md` が型 |
| `.claude/skills/` | 4つのモードの手順書 (request / guide / run-analysis / update) |
| `.claude/settings.json`, `.claude/hooks/` | Claude Code のプロジェクト設定。起動時の更新確認フックと、git の読み取り・`pull --ff-only` の許可 |
| `.agents/skills/` | 上と同じ内容のコピー (Codex 等の他エージェント向け)。**片方を変えたらもう片方も同じにする** (テストで検査) |
| `docs/images/src/` | README 等の図の元 HTML。PNG は直接編集せず、ここを直して再生成する |

レイヤーの向き: `cli` / `run.command` / GUI → `pipeline` → 各処理パッケージ。逆向きの import を作らない。

## 守ること

1. **raw データを壊さない**。`raw_colors.csv` は画像解析の一次データ。analyze 以降のステージで書き換えない。
   後処理の判断 (除外・統合・色名分類など) は analysis 側に置き、raw に混ぜない。
2. **設定値は config.yaml へ**。閾値・件数・サイズなどをコードに直書きしない。新しい値は
   `config.yaml` (日本語コメント付き) と `config.py` の `DEFAULTS` の両方に追加する。
3. **出力の後方互換**。既存 CSV の列名・順序・意味を変えない。列の追加は末尾へ (`reporting/csv_io.py`)。
   `image_id` (images/ からの相対パス、拡張子なし) の形式を変えない。CSV は BOM 付き UTF-8 (Excel 対策)。
4. **未指定のメタデータを捨てない**。`brand` / `year` / `season` / `gender` は空文字 (= 未指定) がありうる
   (`images/001.jpg`, `images/prada/001.jpg`, `images/2018_SS/001.jpg` のどれも正しい入力)。
   集計やグラフでは空欄を除外せず「未指定」グループとして扱う。パス解釈は `loader.parse_path` に集約する。
5. **再現性**。乱数は `clustering.random_state` を使う。実行ログ (`output/logs/*.json`) の記録を消さない。
6. **pipeline 層で print しない**。進捗は `progress` コールバック、失敗は例外で返す (GUI から再利用するため)。
7. **非エンジニア向けメッセージ**。利用者が直せるエラーは `UserError` を日本語で投げる。traceback を見せない。
   新しいエラーを追加したら `docs/troubleshooting.md` にも追記する。
8. **Python 3.9 互換**。Mac 標準の python3 (3.9) で run.command が動くため。`match` 文や実行時評価される
   `X | Y` 型 (dataclass 外の `isinstance` 等) を使わない。各ファイル先頭の `from __future__ import annotations` を残す。
9. **依存を増やすとき**は `pyproject.toml` と `requirements.txt` の両方に追加。重いライブラリは避け、必要ならオプション扱いにする。
10. review 理由コードを追加したら `reporting/preview.py` の `REASON_LABELS` と `docs/results-guide.md` を更新する。
11. 挙動を変えたら、関係する `docs/` (特に `technical.md`, `results-guide.md`) も更新する。README は短く保つ。

## 変更してよい場所の目安

| 要望の例 | 触る場所 |
| --- | --- |
| 色数・閾値・画像サイズ | `config.yaml` のみ (コード変更不要) |
| 集計 CSV・グラフ | 入力は `dataset.csv` (1画像1行) を基本にする。`analysis/` に集計関数、`pipeline.py` にステージ追加、`cli/main.py` にサブコマンド |
| preview の見た目・別ページ | `reporting/preview.py` |
| CSV に列追加 | `reporting/csv_io.py` の列定義 (末尾) + 値を作る処理。manifest 由来の列は自動で images.csv に付く |
| GUI (Streamlit 等) | 新しいパッケージ (例 `src/fca/gui/` や `app.py`) から `pipeline` を呼ぶ。コアロジックは変えない |
| 背景除去の改善 | `image_processing/segmentation.py`。review 判定との整合を確認 |

## テストと確認

```bash
uv sync                 # 開発用環境 (.venv)。run.command 用の .venv-run とは別
uv run pytest -q        # 全テスト (数秒)
uv run fca run --images samples --output /tmp/fca-out   # サンプルで一通り実行
```

- 変更後は必ず `uv run pytest -q` を通す。新しい挙動にはテストを足す (`tests/`)
- 見た目の変更は `/tmp/fca-out/preview.html` を開いて確認する
- uv が無い環境: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt pytest && PYTHONPATH=src .venv/bin/pytest -q`
