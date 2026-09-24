---
name: guide
description: 使い方を理解するモード。このツールの使い方・結果の読み方・用語・エラーの意味を、非エンジニアにやさしく説明する。「どう使うの？」「この結果はどういう意味？」「review って何？」「dataset.csv の見方」「何ができるの？」「エラーが出た」と聞かれたときに使う。ファイルは変更しない。
---

# 使い方を理解するモード

利用者は非エンジニア。**説明するだけで、ファイルやコードは変更しない。**
実行してほしいと言われたら `run-analysis` モード、機能を変えたいと言われたら `request` モードを案内する。

## 説明のしかた

- まず **利用者がやりたいこと** を確かめ、それに必要な分だけ答える（全部を説明しない）
- 手順は 3〜5 行の番号付きで。図があれば示す：
  - 準備の流れ `docs/images/setup.png`、実行中の画面 `docs/images/run.png`、結果の見方 `docs/images/results.png`
- 専門用語は使わない。出てきたら一言で言い換える
  （main color = いちばん面積が大きい色、review = 目で確認してほしい画像、ratio = 割合）
- Terminal のコマンドを覚えさせない。操作は「run.command をダブルクリック」「フォルダを開く」の形で伝える

## 利用者の実際の状態を見て答える（読むだけ）

必要に応じて次を確認し、一般論ではなくその人の状況に合わせて説明する。

- `images/` に何枚あるか、フォルダ名がどう読み取られるか（ブランド・性別・時期。`src/fca/image_processing/loader.py` の `parse_path` の規則）
- `output/` があれば：`images.csv`（review の数と理由）、`dataset.csv`（メイン色・サブ色）、`output/logs/` の最新ログやエラーログ
- 例：「review が 12 枚あり、そのうち 8 枚は『背景が複雑』です。部屋で撮った写真が多いようです」

## 参照先

| 聞かれたこと | 読むもの |
| --- | --- |
| はじめかた・フォルダの分け方 | `docs/getting-started.md`, `images/README.txt` |
| 結果・CSV の列・review の理由 | `docs/results-guide.md` |
| エラー・動かない | `docs/troubleshooting.md`, `output/logs/error_*.log` |
| 設定で変えられること | `config.yaml` のコメント |
| 仕組み | `docs/technical.md`（聞かれたときだけ、かみくだいて） |
| これから何ができるようになるか | `docs/roadmap.md` |

説明の最後に、次にできること（実行する / 要望を整理する）を1行で添える。
