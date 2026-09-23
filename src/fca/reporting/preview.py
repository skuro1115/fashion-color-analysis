"""目視確認用の静的 preview.html を生成する。画像は相対パスで参照する(埋め込まない)。"""

from __future__ import annotations

import html
import os
from pathlib import Path

from .csv_io import read_csv, safe_name

REASON_LABELS = {
    "fg_too_small": "前景が小さい",
    "fg_too_large": "前景が大きすぎる",
    "largest_component_small": "最大領域が小さい",
    "fg_scattered": "前景が分散",
    "unstable_segmentation": "抽出が不安定",
    "too_few_pixels": "ピクセル不足",
    "complex_background": "背景が複雑",
    "fg_touches_border": "画像端に接触",
    "low_fg_bg_contrast": "背景との差が小さい",
    "no_colors": "色なし",
    "error": "処理エラー",
}


def _e(v) -> str:
    return html.escape(str(v), quote=True)


def _text_color(r: int, g: int, b: int) -> str:
    return "#000" if (0.299 * r + 0.587 * g + 0.114 * b) > 140 else "#fff"


def _palette(colors: list[dict], rank_key: str) -> str:
    if not colors:
        return '<div class="empty">—</div>'
    bar = "".join(
        f'<span style="background:{c["hex"]};flex:{float(c["ratio"]):.4f}" title="{c["hex"]} {float(c["ratio"]) * 100:.1f}%"></span>'
        for c in colors
    )
    chips = "".join(
        f'<div class="chip" style="background:{c["hex"]};color:{_text_color(int(c["r"]), int(c["g"]), int(c["b_rgb"]))}">'
        f'<b>{_e(c[rank_key])}</b><span>{c["hex"]}</span><span>{float(c["ratio"]) * 100:.1f}%</span></div>'
        for c in colors
    )
    return f'<div class="bar">{bar}</div><div class="chips">{chips}</div>'


def _card(img: dict, raw: list[dict], ana: list[dict], out_dir: Path) -> str:
    name = safe_name(img["image_id"])
    orig = os.path.relpath(img["original_path"], out_dir) if img.get("original_path") else ""
    review = img.get("review") == "True"
    reasons = [x for x in (img.get("review_reasons") or "").split(";") if x]
    reason_html = "".join(f'<span class="reason">{_e(REASON_LABELS.get(r, r))}</span>' for r in reasons)
    main = ana[0] if ana else None
    main_html = (
        f'<div class="main"><span class="swatch" style="background:{main["hex"]}"></span>'
        f'<div><div class="lbl">main color</div><div class="hex">{main["hex"]}</div>'
        f'<div class="sub">{float(main["ratio"]) * 100:.1f}% · L{float(main["L"]):.0f} a{float(main["a"]):.0f} b{float(main["b"]):.0f}</div></div></div>'
        if main else '<div class="main empty">main color なし</div>'
    )
    meta = " / ".join(x for x in (img.get("brand"), img.get("year"), img.get("season")) if x)
    fg = img.get("foreground_ratio") or ""
    fg_txt = f"{float(fg) * 100:.0f}%" if fg else "—"
    err = f'<div class="err">{_e(img["error_message"])}</div>' if img.get("error_message") else ""
    search = " ".join([img["image_id"], img.get("brand", ""), img.get("year", ""), img.get("season", ""), *reasons]).lower()
    return f"""
<article class="card{' is-review' if review else ''}" data-review="{int(review)}" data-brand="{_e(img.get('brand', ''))}" data-search="{_e(search)}">
  <header>
    <div><div class="id">{_e(img['image_id'])}</div><div class="meta">{_e(meta)}</div></div>
    <div class="badge {'bad' if review else 'ok'}">{'review' if review else 'ok'}</div>
  </header>
  <div class="reasons">{reason_html}</div>{err}
  <div class="imgs">
    <figure><img loading="lazy" src="{_e(orig)}" alt=""><figcaption>元画像</figcaption></figure>
    <figure><img loading="lazy" src="masks/{_e(name)}.png" alt=""><figcaption>mask · 前景 {fg_txt}</figcaption></figure>
    <figure class="checker"><img loading="lazy" src="cutouts/{_e(name)}.png" alt=""><figcaption>抽出後 · {_e(img.get('segmentation_method', ''))}</figcaption></figure>
  </div>
  {main_html}
  <h3>analysis ({len(ana)})</h3>{_palette(ana, 'color_rank')}
  <details><summary>raw 10クラスタ</summary>{_palette(raw, 'cluster_rank')}
    <div class="metrics">IoU {_e(img.get('stability_iou', ''))} · 外周残差 {_e(img.get('border_residual', ''))} · 端接触 {_e(img.get('border_touch', ''))} · 成分数 {_e(img.get('n_components', ''))} · 前景/背景ΔE {_e(img.get('fg_bg_delta_e', ''))}</div>
  </details>
</article>"""


CSS = """
:root{--bg:#f4f4f2;--card:#fff;--fg:#1d1d1f;--muted:#6b6b70;--line:#e3e3e0;--bad:#c2410c;--ok:#15803d}
*{box-sizing:border-box}body{margin:0;font:13px/1.45 -apple-system,BlinkMacSystemFont,"Hiragino Sans",sans-serif;background:var(--bg);color:var(--fg)}
.top{position:sticky;top:0;z-index:5;background:rgba(244,244,242,.95);backdrop-filter:blur(6px);border-bottom:1px solid var(--line);padding:12px 20px;display:flex;gap:12px;align-items:center;flex-wrap:wrap}
.top h1{font-size:15px;margin:0 12px 0 0}.top select,.top input{font:inherit;padding:5px 8px;border:1px solid var(--line);border-radius:6px;background:#fff}
.count{color:var(--muted);margin-left:auto}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(380px,1fr));gap:16px;padding:20px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px}.card.is-review{border-color:#f0b48a}
.card header{display:flex;justify-content:space-between;gap:8px}.id{font-weight:600;word-break:break-all}.meta{color:var(--muted)}
.badge{height:fit-content;padding:2px 8px;border-radius:99px;font-size:11px;font-weight:600;color:#fff}.badge.ok{background:var(--ok)}.badge.bad{background:var(--bad)}
.reasons{display:flex;flex-wrap:wrap;gap:4px;margin:6px 0}.reason{background:#fdebdd;color:var(--bad);border-radius:4px;padding:1px 6px;font-size:11px}
.err{color:var(--bad);font-family:monospace;font-size:11px}
.imgs{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin:8px 0}
figure{margin:0}figure img{width:100%;aspect-ratio:3/4;object-fit:contain;background:#eee;border-radius:6px;display:block}
figure.checker img{background:repeating-conic-gradient(#ddd 0 25%,#fff 0 50%) 0 0/14px 14px}
figcaption{color:var(--muted);font-size:11px;text-align:center;margin-top:2px}
.main{display:flex;gap:10px;align-items:center;margin:8px 0}.swatch{width:52px;height:52px;border-radius:8px;border:1px solid var(--line);flex:none}
.lbl{color:var(--muted);font-size:11px}.hex{font-weight:700;font-size:16px;font-family:ui-monospace,monospace}.sub{color:var(--muted);font-size:11px}
h3{font-size:12px;margin:10px 0 4px;color:var(--muted);font-weight:600}
.bar{display:flex;height:14px;border-radius:4px;overflow:hidden;border:1px solid var(--line)}
.chips{display:flex;flex-wrap:wrap;gap:4px;margin-top:6px}
.chip{display:flex;flex-direction:column;min-width:62px;padding:4px 6px;border-radius:5px;font-size:10px;font-family:ui-monospace,monospace;border:1px solid rgba(0,0,0,.08)}
details{margin-top:8px}summary{cursor:pointer;color:var(--muted);font-size:12px}
.metrics{color:var(--muted);font-size:11px;margin-top:6px}.empty{color:var(--muted)}
"""

JS = """
const q=s=>document.querySelector(s),cards=[...document.querySelectorAll('.card')];
function apply(){const rv=q('#f-review').value,br=q('#f-brand').value,t=q('#f-text').value.toLowerCase();let n=0;
for(const c of cards){const ok=(rv==='all'||c.dataset.review===rv)&&(!br||c.dataset.brand===br)&&(!t||c.dataset.search.includes(t));c.hidden=!ok;if(ok)n++}
q('#count').textContent=n+' / '+cards.length+' 枚'}
['#f-review','#f-brand','#f-text'].forEach(s=>q(s).addEventListener('input',apply));apply();
"""


def build_preview(out_dir: Path) -> Path:
    out_dir = Path(out_dir)
    if not (out_dir / "images.csv").exists():
        from ..errors import UserError

        raise UserError(f"{out_dir}/images.csv がありません。先に画像の解析を実行してください。")
    images = read_csv(out_dir / "images.csv")
    raw = read_csv(out_dir / "raw_colors.csv")
    ana_path = out_dir / "analysis_colors.csv"
    ana = read_csv(ana_path) if ana_path.exists() else []
    raw_by, ana_by = {}, {}
    for r in raw:
        raw_by.setdefault(r["image_id"], []).append(r)
    for r in ana:
        ana_by.setdefault(r["image_id"], []).append(r)

    brands = sorted({i.get("brand", "") for i in images if i.get("brand")})
    n_review = sum(1 for i in images if i.get("review") == "True")
    cards = "".join(_card(i, raw_by.get(i["image_id"], []), ana_by.get(i["image_id"], []), out_dir) for i in images)
    brand_opts = "".join(f'<option value="{_e(b)}">{_e(b)}</option>' for b in brands)
    page = f"""<!doctype html><html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Color Preview</title><style>{CSS}</style></head><body>
<div class="top"><h1>代表色 preview</h1>
<select id="f-review"><option value="all">すべて</option><option value="1">review のみ ({n_review})</option><option value="0">ok のみ</option></select>
<select id="f-brand"><option value="">全ブランド</option>{brand_opts}</select>
<input id="f-text" type="search" placeholder="ID・年・理由で検索">
<span class="count" id="count"></span></div>
<main class="grid">{cards}</main><script>{JS}</script></body></html>"""
    path = out_dir / "preview.html"
    path.write_text(page, encoding="utf-8")
    return path
