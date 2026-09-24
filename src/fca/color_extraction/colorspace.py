"""色空間変換と色差。Lab は CIELAB (D65, L: 0-100)。"""

from __future__ import annotations

import colorsys
import math
from typing import Optional

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


def rgb_to_hsb(r, g, b, lab_a: float, lab_b: float, achromatic_chroma: float) -> tuple:
    """RGB (0-255) -> (色相 0-360 or None, 彩度 0-100, 明度 0-100)。HSB = HSV。

    Lab の彩度 (chroma = sqrt(a^2 + b^2)) が achromatic_chroma 未満の色は無彩色
    (黒・白・グレー) とみなし、色相を None にする。HSV の色相は無彩色で不安定なため。
    色相は円なので、集計で平均するときは単純平均ではなく円周平均を使うこと。
    """
    h, s, v = colorsys.rgb_to_hsv(float(r) / 255, float(g) / 255, float(b) / 255)
    hue: Optional[float] = round(h * 360, 1) % 360
    if math.hypot(float(lab_a), float(lab_b)) < achromatic_chroma:
        hue = None
    return hue, round(s * 100, 1), round(v * 100, 1)
