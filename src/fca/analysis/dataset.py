"""images.csv + analysis_colors.csv -> dataset.csv (1画像1行の分析用データ)。

各画像について、メタデータ (brand / year / season / gender) と
メイン色 (analysis の面積1位) ・サブ色 (2位以降) の色と面積を横に並べる。
集計やグラフはこのファイルを入力にすることを想定している。
"""

from __future__ import annotations

from ..color_extraction.colorspace import rgb_to_hsb

META_COLS = ["image_id", "brand", "year", "season", "gender"]
COLOR_FIELDS = ["hex", "ratio", "r", "g", "b_rgb", "L", "a", "b"]
TAIL_COLS = ["n_colors", "all_colors", "review", "review_reasons"]
# HSB (色相・彩度・明度) は後から追加したので、後方互換のため全列の末尾に並べる
HSB_FIELDS = ["hue", "sat", "bri"]


def slot_names(n_sub: int) -> list[str]:
    return ["main"] + [f"sub{i}" for i in range(1, n_sub + 1)]


def dataset_columns(cfg: dict) -> list[str]:
    cols = list(META_COLS)
    for slot in slot_names(int(cfg["n_sub_colors"])):
        cols += [f"{slot}_{f}" for f in COLOR_FIELDS]
    cols += TAIL_COLS
    for slot in slot_names(int(cfg["n_sub_colors"])):
        cols += [f"{slot}_{f}" for f in HSB_FIELDS]
    return cols


def build_dataset(images: list[dict], colors_by_image: dict, cfg: dict) -> list[dict]:
    """images: images.csv の行、colors_by_image: image_id -> analysis_colors の行 (color_rank 順)。

    サブ色は面積比が min_sub_ratio 以上のものだけ入れ、足りない枠は空欄にする。
    all_colors には除外前の全色を "hex:割合%" の形で並べる。
    各色には HSB (hue 色相° / sat 彩度 / bri 明度) も付ける。無彩色の hue は空欄。
    brand などが空 (未指定) の画像も除外しない。
    """
    slots = slot_names(int(cfg["n_sub_colors"]))
    min_sub = float(cfg["min_sub_ratio"])
    rows = []
    for img in images:
        colors = sorted(colors_by_image.get(img["image_id"], []), key=lambda c: int(c["color_rank"]))
        row = {c: img.get(c, "") for c in META_COLS}
        picked = colors[:1] + [c for c in colors[1:] if float(c["ratio"]) >= min_sub]
        for slot, color in zip(slots, picked):
            for f in COLOR_FIELDS:
                row[f"{slot}_{f}"] = color[f]
            hue, sat, bri = rgb_to_hsb(color["r"], color["g"], color["b_rgb"], color["a"], color["b"],
                                       float(cfg["achromatic_chroma"]))
            row[f"{slot}_hue"] = "" if hue is None else hue
            row[f"{slot}_sat"], row[f"{slot}_bri"] = sat, bri
        row["n_colors"] = len(colors)
        row["all_colors"] = ";".join(f'{c["hex"]}:{float(c["ratio"]) * 100:.1f}%' for c in colors)
        row["review"] = img.get("review", "")
        row["review_reasons"] = img.get("review_reasons", "")
        rows.append(row)
    return rows
