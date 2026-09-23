"""raw_colors -> analysis_colors の後処理。画像は読まないので、閾値を変えて何度でも再実行できる。

  1. 面積比が min_cluster_ratio 未満のクラスタを除外
  2. ΔE が merge_delta_e 未満の最近接ペアを、ピクセル数で重み付けした Lab 平均に統合(繰り返し)
  3. 残ったピクセルで面積比を再計算し、大きい順に並べ直す (color_rank=1 が main color)
"""

from __future__ import annotations

import numpy as np

from ..color_extraction.colorspace import delta_e, lab_to_rgb, rgb_to_hex


def analyze_clusters(clusters: list[dict], cfg: dict) -> list[dict]:
    if not clusters:
        return []
    total_all = sum(int(c["pixels"]) for c in clusters)
    kept = [c for c in clusters if float(c["ratio"]) >= cfg["min_cluster_ratio"]]
    if not kept:  # 全部小さい場合は最大クラスタだけ残す
        kept = [max(clusters, key=lambda c: int(c["pixels"]))]

    groups = [
        {
            "lab": np.array([float(c["L"]), float(c["a"]), float(c["b"])]),
            "pixels": int(c["pixels"]),
            "sources": [int(c["cluster_rank"])],
        }
        for c in kept
    ]

    thr = cfg.get("merge_delta_e")
    metric = cfg.get("delta_e_metric", "ciede2000")
    while thr is not None and len(groups) > 1:
        labs = np.array([g["lab"] for g in groups])
        d = delta_e(labs[:, None, :], labs[None, :, :], metric)
        np.fill_diagonal(d, np.inf)
        i, j = np.unravel_index(np.argmin(d), d.shape)
        if d[i, j] >= thr:
            break
        gi, gj = groups[i], groups[j]
        p = gi["pixels"] + gj["pixels"]
        merged = {
            "lab": (gi["lab"] * gi["pixels"] + gj["lab"] * gj["pixels"]) / p,
            "pixels": p,
            "sources": sorted(gi["sources"] + gj["sources"]),
        }
        groups = [g for k, g in enumerate(groups) if k not in (i, j)] + [merged]

    total = sum(g["pixels"] for g in groups)
    groups.sort(key=lambda g: (-g["pixels"], g["sources"][0]))
    out = []
    for rank, g in enumerate(groups, start=1):
        rgb = lab_to_rgb(g["lab"])
        out.append({
            "color_rank": rank,
            "L": round(float(g["lab"][0]), 3),
            "a": round(float(g["lab"][1]), 3),
            "b": round(float(g["lab"][2]), 3),
            "r": int(rgb[0]),
            "g": int(rgb[1]),
            "b_rgb": int(rgb[2]),
            "hex": rgb_to_hex(rgb),
            "ratio": round(g["pixels"] / total, 6),
            "ratio_unfiltered": round(g["pixels"] / total_all, 6),
            "pixels": g["pixels"],
            "source_clusters": ";".join(str(s) for s in g["sources"]),
        })
    return out
