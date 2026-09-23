"""商品領域ピクセルを Lab 空間で K-means (k=10) し、raw クラスタを返す。"""

from __future__ import annotations

import numpy as np
from sklearn.cluster import KMeans

from .colorspace import lab_to_rgb, rgb_to_hex


def extract_clusters(lab: np.ndarray, mask: np.ndarray, cfg: dict) -> list[dict]:
    """面積比の大きい順に並んだクラスタのリストを返す。

    K-means の学習は最大 fit_sample ピクセルで行い、割当・面積・中心色は
    全対象ピクセルから計算し直す(サンプリングによる面積比の揺れを避ける)。
    """
    pix = lab[mask].astype(np.float64)
    n = len(pix)
    if n == 0:
        return []
    seed = int(cfg["random_state"])
    n_unique = len(np.unique(pix.round(2), axis=0))
    k = min(int(cfg["k"]), n_unique)

    rng = np.random.default_rng(seed)
    sample = pix[rng.choice(n, cfg["fit_sample"], replace=False)] if n > cfg["fit_sample"] else pix
    km = KMeans(n_clusters=k, random_state=seed, n_init=cfg["n_init"]).fit(sample)
    labels = km.predict(pix)
    counts = np.bincount(labels, minlength=k)

    clusters = []
    for idx in range(k):
        if counts[idx] == 0:
            continue
        center = pix[labels == idx].mean(axis=0)
        rgb = lab_to_rgb(center)
        clusters.append({
            "L": round(float(center[0]), 3),
            "a": round(float(center[1]), 3),
            "b": round(float(center[2]), 3),
            "r": int(rgb[0]),
            "g": int(rgb[1]),
            "b_rgb": int(rgb[2]),
            "hex": rgb_to_hex(rgb),
            "ratio": round(float(counts[idx] / n), 6),
            "pixels": int(counts[idx]),
        })
    clusters.sort(key=lambda c: (-c["pixels"], c["L"]))
    for rank, c in enumerate(clusters, start=1):
        c["cluster_rank"] = rank
    return clusters
