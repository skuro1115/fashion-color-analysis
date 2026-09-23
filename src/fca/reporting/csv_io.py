"""出力 CSV の列定義と読み書き。

列の順序・名前は既存出力との後方互換のため変更しない。列を追加する場合は末尾に足す。
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

IMAGE_COLS = [
    "image_id", "brand", "year", "season", "filename", "review", "review_reasons",
    "processing_status", "error_message", "original_path", "processed_width", "processed_height",
    "segmentation_method", "foreground_ratio", "fg_pixels", "n_components",
    "largest_component_ratio", "largest_share", "border_touch", "border_residual",
    "fg_bg_delta_e", "stability_iou", "gender",
]
RAW_COLS = ["image_id", "cluster_rank", "L", "a", "b", "r", "g", "b_rgb", "hex", "ratio", "pixels"]
ANALYSIS_COLS = [
    "image_id", "color_rank", "L", "a", "b", "r", "g", "b_rgb", "hex",
    "ratio", "ratio_unfiltered", "pixels", "source_clusters",
]


def safe_name(image_id: str) -> str:
    """image_id を masks/ cutouts/ のファイル名に変換する。"""
    return re.sub(r"[^A-Za-z0-9_\-.]", "_", image_id.replace("/", "__"))


def write_csv(path: Path, cols: list[str], rows: list[dict]) -> None:
    # BOM 付き UTF-8: Excel で開いても日本語が文字化けしない
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))
