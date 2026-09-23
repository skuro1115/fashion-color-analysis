# 図の元データ

README やドキュメントの図は、ここの HTML をブラウザで描画して PNG に書き出したもの。
**PNG を直接編集せず、HTML を直して再生成する。**

| 元データ | 書き出し先 | 内容 | 使われている場所 |
| --- | --- | --- | --- |
| `setup.html` | `../setup.png` | セットアップの4ステップ | README, getting-started |
| `run.html` | `../run.png` | run.command 実行中の画面と説明 | README, getting-started |
| `results.html` | `../results.png` | 確認ページの見方と output のファイル | README, getting-started, results-guide |

`../preview.png` は実際の preview.html のスクリーンショット (samples で実行したもの)。

## 再生成

リポジトリのルートで実行する (Google Chrome が必要)。

```bash
docs/images/src/render.sh            # すべて
docs/images/src/render.sh run        # 1つだけ
```

図を追加したら `render.sh` の `size()` に大きさを書き、この表にも追記する。
run.command の表示文言を変えたら `run.html` も合わせる。
