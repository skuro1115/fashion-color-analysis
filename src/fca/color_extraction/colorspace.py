"""色空間変換と色差。Lab は CIELAB (D65, L: 0-100)。"""

from __future__ import annotations

import numpy as np
from skimage import color as skcolor


def rgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    """uint8 RGB (..., 3) -> float Lab (..., 3)"""
    return skcolor.rgb2lab(rgb.astype(np.float64) / 255.0)


def lab_to_rgb(lab: np.ndarray) -> np.ndarray:
    """Lab (..., 3) -> uint8 RGB (..., 3)。色域外はクリップ。"""
    lab = np.asarray(lab, dtype=np.float64)
    shape = lab.shape
    rgb = skcolor.lab2rgb(lab.reshape(-1, 1, 3)).reshape(shape)
    return np.clip(np.round(rgb * 255.0), 0, 255).astype(np.uint8)


def rgb_to_hex(rgb) -> str:
    r, g, b = (int(v) for v in rgb)
    return f"#{r:02X}{g:02X}{b:02X}"


def delta_e(lab1: np.ndarray, lab2: np.ndarray, metric: str = "ciede2000") -> np.ndarray:
    lab1 = np.asarray(lab1, dtype=np.float64)
    lab2 = np.asarray(lab2, dtype=np.float64)
    if metric == "ciede2000":
        return skcolor.deltaE_ciede2000(lab1, lab2)
    if metric == "cie76":
        return skcolor.deltaE_cie76(lab1, lab2)
    raise ValueError(f"unknown delta_e metric: {metric}")
