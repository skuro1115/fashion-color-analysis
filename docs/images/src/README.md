# 図の元データ

| 元データ | 書き出し先 | 使われている場所 |
| --- | --- | --- |
| `how-to-use.html` | `../how-to-use.png` | README 冒頭 |

HTML を編集したら、リポジトリのルートで次を実行して PNG を再生成する (Google Chrome が必要)。

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --hide-scrollbars \
  --force-device-scale-factor=2 --window-size=1200,420 \
  --screenshot=docs/images/how-to-use.png "file://$PWD/docs/images/src/how-to-use.html"
```
