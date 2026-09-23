# はじめかた

```text
 ① ダウンロード  →  ② images に入れる  →  ③ run.command  →  ④ 結果を見る
```

---

## ① ダウンロード

[ZIP をダウンロード](https://github.com/skuro1115/fashion-color-analysis/archive/refs/heads/main.zip) → ダブルクリックで開く。

```text
fashion-color-analysis-main/
├── images/        ← ここに画像を入れる
├── samples/       ← 試し用の画像
├── run.command    ← ダブルクリックで実行
└── ...
```

> フォルダは「書類」や「デスクトップ」など、好きな場所に移してかまいません。

---

## ② images に画像を入れる

jpg / png / webp が使えます。**ブランド → 年_シーズン** でフォルダを分けると、結果に自動で記録されます。

```text
images/
├── prada/
│   ├── 2018_SS/
│   │   ├── 001.jpg
│   │   └── 002.jpg
│   └── 2018_FW/
└── gucci/
    └── 2019_SS/
```

分けずに直接入れても動きます。

**まず試したいとき：** `samples` の中のフォルダを `images` にコピーしてください。

---

## ③ run.command をダブルクリック

黒い画面（ターミナル）が開いて、自動で進みます。何も入力しなくて大丈夫です。

```text
==== Fashion Color Analysis ====
▶ 画像を確認しています
  画像: 6 枚
▶ 必要なライブラリをインストールしています (初回は数分かかります)   ← 初回だけ
▶ 解析しています
  [1/6] prada/2018_SS/001
  [2/6] prada/2018_SS/002  ← 要確認
  ...
✔ 完了しました
```

### 初回だけ出るかもしれない画面

| 表示 | すること |
| --- | --- |
| 「開発元を検証できません」「Apple は検証できませんでした」 | [開き方](troubleshooting.md#runcommand-が開けない) を見る（初回のみ） |
| 「"ターミナル" が "ダウンロード" フォルダにアクセスしようとしています」 | 「許可」を押す |
| Python のインストールを求められる | [Python を入れる](troubleshooting.md#python-が見つかりません) |

---

## ④ 結果を見る

終わると、ブラウザで確認ページが自動で開きます。

![確認ページ](images/preview.png)

`output` フォルダにはこんなファイルができます。

```text
output/
├── preview.html          ← 確認ページ（ダブルクリックで開く）
├── analysis_colors.csv   ← 画像ごとの色（Excel で開ける）
└── images.csv            ← 画像ごとの情報・要確認の印
```

意味は → [結果の見方](results-guide.md)

---

## 画像を増やしたら

`images` に追加して、もう一度 `run.command` をダブルクリックするだけです。2回目からはすぐ始まります。
