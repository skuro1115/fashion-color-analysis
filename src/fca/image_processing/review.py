"""review 判定: 抽出指標を config の閾値と比べ、人間確認が必要な理由を返す。

理由コードは images.csv の review_reasons 列と preview.html の表示名 (reporting/preview.py の
REASON_LABELS) で使われる。コードを追加したら REASON_LABELS と docs にも追記すること。
"""

from __future__ import annotations

import numpy as np


def review_reasons(metrics: dict, fg_cfg: dict, review_cfg: dict) -> list[str]:
    """review=true にすべき理由のリスト。空なら問題なし。"""
    r = []
    fr = metrics.get("foreground_ratio", 0.0)
    if fr < fg_cfg["min_ratio"]:
        r.append("fg_too_small")
    if fr >= fg_cfg["max_ratio"]:
        r.append("fg_too_large")
    if metrics.get("largest_component_ratio", 0.0) < review_cfg["min_largest_component"]:
        r.append("largest_component_small")
    if metrics.get("n_components", 0) > review_cfg["max_components"] or (
        metrics.get("largest_share", 1.0) < review_cfg["min_largest_share"]
    ):
        r.append("fg_scattered")
    if metrics.get("stability_iou", 1.0) < review_cfg["min_stability_iou"]:
        r.append("unstable_segmentation")
    if metrics.get("fg_pixels", 0) < review_cfg["min_pixels"]:
        r.append("too_few_pixels")
    if metrics.get("border_residual", 0.0) > review_cfg["max_border_residual"]:
        r.append("complex_background")
    if metrics.get("border_touch", 0.0) > review_cfg["max_border_touch"]:
        r.append("fg_touches_border")
    fbd = metrics.get("fg_bg_delta_e")
    if fbd is not None and not np.isnan(fbd) and fbd < review_cfg["min_fg_bg_delta_e"]:
        r.append("low_fg_bg_contrast")
    return r
