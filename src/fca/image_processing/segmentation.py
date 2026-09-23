"""古典的画像処理による商品領域抽出と、review 判定用の指標計算。

手順:
  1. 画像外周の帯から背景色候補を K-means で推定
  2. 各ピクセルと最も近い背景色の ΔE(CIE76) を計算し、閾値未満を背景候補とする
  3. 背景候補のうち外周に連結しているものだけを背景とする(商品内部の白などを残すため)
  4. morphology (opening -> closing)
  5. 最大連結成分と、それに近い大きさの成分だけを残す
"""

from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np
from sklearn.cluster import KMeans


@dataclass
class Segmentation:
    mask: np.ndarray                      # bool HxW, True = 商品
    method: str                           # "color" | "alpha"
    bg_colors: np.ndarray                 # (n, 3) Lab
    metrics: dict[str, float] = field(default_factory=dict)


def _border_mask(h: int, w: int, width_ratio: float) -> np.ndarray:
    bw = max(2, int(round(min(h, w) * width_ratio)))
    border = np.zeros((h, w), dtype=bool)
    border[:bw, :] = border[-bw:, :] = True
    border[:, :bw] = border[:, -bw:] = True
    return border


def _estimate_background(lab: np.ndarray, border: np.ndarray, cfg: dict, seed: int) -> np.ndarray:
    pix = lab[border]
    rng = np.random.default_rng(seed)
    if len(pix) > 5000:
        pix = pix[rng.choice(len(pix), 5000, replace=False)]
    n = min(cfg["bg_clusters"], len(np.unique(pix.round(1), axis=0)))
    km = KMeans(n_clusters=max(n, 1), random_state=seed, n_init=3).fit(pix)
    shares = np.bincount(km.labels_, minlength=km.n_clusters) / len(pix)
    centers = km.cluster_centers_[shares >= cfg["bg_cluster_min_share"]]
    if len(centers) == 0:
        centers = km.cluster_centers_[[int(np.argmax(shares))]]
    return centers


def _distance_to_bg(lab: np.ndarray, bg_colors: np.ndarray) -> np.ndarray:
    d = np.linalg.norm(lab[:, :, None, :] - bg_colors[None, None, :, :], axis=-1)
    return d.min(axis=-1)


def _clean_components(fg: np.ndarray, cfg: dict) -> tuple[np.ndarray, list[int]]:
    """小さい孤立成分を除去し、(マスク, 残した成分の面積リスト) を返す。"""
    n, labels, stats, _ = cv2.connectedComponentsWithStats(fg.astype(np.uint8), connectivity=8)
    if n <= 1:
        return np.zeros_like(fg), []
    areas = stats[1:, cv2.CC_STAT_AREA]
    largest = areas.max()
    min_area = max(cfg["min_component_ratio"] * largest, cfg["min_component_area"] * fg.size)
    keep = [i + 1 for i, a in enumerate(areas) if a >= min_area]
    if not keep:
        keep = [int(np.argmax(areas)) + 1]
    return np.isin(labels, keep), sorted((int(stats[i, cv2.CC_STAT_AREA]) for i in keep), reverse=True)


def _mask_from_distance(dist: np.ndarray, border: np.ndarray, thr: float, cfg: dict):
    bg_like = dist < thr
    _, labels = cv2.connectedComponents(bg_like.astype(np.uint8), connectivity=4)
    touching = np.unique(labels[border & bg_like])
    bg = np.isin(labels, touching) & bg_like
    if cfg["remove_enclosed_background"]:
        bg |= dist < cfg["enclosed_bg_delta_e"]
    fg = ~bg
    k = int(cfg["morph_kernel"])
    if k > 1:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
        fg_u8 = fg.astype(np.uint8)
        fg_u8 = cv2.morphologyEx(fg_u8, cv2.MORPH_OPEN, kernel)
        fg_u8 = cv2.morphologyEx(fg_u8, cv2.MORPH_CLOSE, kernel)
        fg = fg_u8.astype(bool)
    return _clean_components(fg, cfg)


def _iou(a: np.ndarray, b: np.ndarray) -> float:
    union = np.logical_or(a, b).sum()
    return float(np.logical_and(a, b).sum() / union) if union else 1.0


def segment(lab: np.ndarray, alpha: np.ndarray | None, fg_cfg: dict, review_cfg: dict, seed: int) -> Segmentation:
    h, w = lab.shape[:2]
    border = _border_mask(h, w, fg_cfg["border_width"])

    # 透過 PNG は alpha をそのまま信用する
    if fg_cfg["use_alpha"] and alpha is not None and (alpha < 128).mean() > 0.01:
        mask, areas = _clean_components(alpha >= 128, fg_cfg)
        metrics = _metrics(mask, areas, border, None, None)
        metrics["stability_iou"] = 1.0
        return Segmentation(mask=mask, method="alpha", bg_colors=np.empty((0, 3)), metrics=metrics)

    bg_colors = _estimate_background(lab, border, fg_cfg, seed)
    dist = _distance_to_bg(lab, bg_colors)
    thr = float(fg_cfg["bg_delta_e"])
    mask, areas = _mask_from_distance(dist, border, thr, fg_cfg)

    metrics = _metrics(mask, areas, border, dist, thr)
    s = review_cfg["stability_scale"]
    lo, _ = _mask_from_distance(dist, border, thr * (1 - s), fg_cfg)
    hi, _ = _mask_from_distance(dist, border, thr * (1 + s), fg_cfg)
    metrics["stability_iou"] = round(_iou(lo, hi), 4)
    return Segmentation(mask=mask, method="color", bg_colors=bg_colors, metrics=metrics)


def _metrics(mask, areas, border, dist, thr) -> dict[str, float]:
    total = mask.size
    fg_pixels = int(mask.sum())
    m = {
        "foreground_ratio": round(fg_pixels / total, 4),
        "fg_pixels": fg_pixels,
        "n_components": len(areas),
        "largest_component_ratio": round(areas[0] / total, 4) if areas else 0.0,
        "largest_share": round(areas[0] / fg_pixels, 4) if areas and fg_pixels else 0.0,
        "border_touch": round(float(mask[border].mean()), 4),
    }
    if dist is not None:
        m["border_residual"] = round(float((dist[border] >= thr).mean()), 4)
        m["fg_bg_delta_e"] = round(float(np.median(dist[mask])), 2) if fg_pixels else 0.0
    else:
        m["border_residual"] = 0.0
        m["fg_bg_delta_e"] = float("nan")
    return m
