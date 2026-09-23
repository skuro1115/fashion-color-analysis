"""解析の公開 API。CLI・run.command・将来の GUI (Streamlit 等) はすべてここを呼ぶ。

    run_extract(cfg, images_dir, out_dir, progress=...)  画像 -> images.csv, raw_colors.csv
    run_analyze(cfg, out_dir)                            raw_colors.csv -> analysis_colors.csv, dataset.csv
    build_preview(out_dir)                               -> preview.html

この層では print しない。進捗は progress コールバックで呼び出し側へ渡す。
ステージ間の受け渡しは CSV のみ (raw_colors.csv は一次データなので analyze では書き換えない)。
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Callable, Optional

import cv2
import numpy as np
from PIL import Image

from .analysis.dataset import build_dataset, dataset_columns
from .analysis.merge import analyze_clusters
from .color_extraction.colorspace import rgb_to_lab
from .color_extraction.kmeans import extract_clusters
from .errors import UserError
from .image_processing.loader import apply_manifest, load_image, read_manifest, scan_images
from .image_processing.review import review_reasons
from .image_processing.segmentation import segment
from .reporting.csv_io import ANALYSIS_COLS, IMAGE_COLS, RAW_COLS, read_csv, safe_name, write_csv
from .reporting.preview import build_preview  # noqa: F401  (公開 API として再エクスポート)
from .reporting.run_log import write_run_log

# progress(現在の枚数, 総枚数, image_id, review が必要か)
ProgressFn = Callable[[int, int, str, bool], None]


def _save_visuals(rgb: np.ndarray, mask: np.ndarray, name: str, out_dir: Path) -> None:
    Image.fromarray((mask * 255).astype(np.uint8)).save(out_dir / "masks" / f"{name}.png")
    rgba = np.dstack([rgb, (mask * 255).astype(np.uint8)])
    Image.fromarray(rgba, "RGBA").save(out_dir / "cutouts" / f"{name}.png")


def _erode(mask: np.ndarray, px: int) -> np.ndarray:
    """輪郭の背景混じりピクセルを色抽出から外す。削りすぎて消える場合は元のマスクを使う。"""
    if px <= 0:
        return mask
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * px + 1, 2 * px + 1))
    eroded = cv2.erode(mask.astype(np.uint8), kernel).astype(bool)
    return eroded if eroded.sum() >= 0.5 * mask.sum() else mask


def process_image(rgb: np.ndarray, alpha: Optional[np.ndarray], cfg: dict):
    """1枚分の解析。(segmentation, review理由, rawクラスタ) を返す。GUI から単体で呼んでもよい。"""
    fg_cfg, rv_cfg, cl_cfg = cfg["foreground"], cfg["review"], cfg["clustering"]
    lab = rgb_to_lab(rgb)
    seg = segment(lab, alpha, fg_cfg, rv_cfg, seed=cl_cfg["random_state"])
    reasons = review_reasons(seg.metrics, fg_cfg, rv_cfg)
    color_mask = _erode(seg.mask, cl_cfg["edge_erode"])
    clusters = extract_clusters(lab, color_mask, cl_cfg) if color_mask.any() else []
    if not clusters:
        reasons.append("no_colors")
    return seg, reasons, clusters


def run_extract(
    cfg: dict, images_dir: Path, out_dir: Path,
    limit: Optional[int] = None, progress: Optional[ProgressFn] = None,
) -> dict:
    images_dir, out_dir = Path(images_dir), Path(out_dir)
    if not images_dir.is_dir():
        raise UserError(f"画像フォルダが見つかりません: {images_dir}")
    records = scan_images(images_dir, **cfg["metadata"])
    if not records:
        raise UserError(
            f"{images_dir}/ に画像がありません。\n"
            "jpg / jpeg / png / webp の画像を入れてから、もう一度実行してください。"
        )
    if limit:
        records = records[:limit]

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "masks").mkdir(exist_ok=True)
    (out_dir / "cutouts").mkdir(exist_ok=True)
    extra_cols = apply_manifest(records, read_manifest(Path(cfg["paths"]["manifest"])))

    image_rows, raw_rows = [], []
    t0 = time.time()
    for i, rec in enumerate(records, start=1):
        row = {
            "image_id": rec.image_id, "brand": rec.brand, "year": rec.year, "season": rec.season,
            "gender": rec.gender,
            "filename": rec.filename, "original_path": str(rec.path), **rec.extra,
        }
        try:
            rgb, alpha = load_image(rec.path, cfg["image"]["max_size"])
            seg, reasons, clusters = process_image(rgb, alpha, cfg)
            _save_visuals(rgb, seg.mask, safe_name(rec.image_id), out_dir)
            row.update(seg.metrics)
            row.update({
                "processed_width": rgb.shape[1], "processed_height": rgb.shape[0],
                "segmentation_method": seg.method, "processing_status": "ok", "error_message": "",
                "review": bool(reasons), "review_reasons": ";".join(reasons),
            })
            for c in clusters:
                raw_rows.append({"image_id": rec.image_id, **c})
        except Exception as e:  # 1枚の失敗で全体を止めない
            row.update({
                "processing_status": "error", "error_message": f"{type(e).__name__}: {e}",
                "review": True, "review_reasons": "error",
            })
        image_rows.append(row)
        if progress:
            progress(i, len(records), rec.image_id, bool(row["review"]))

    write_csv(out_dir / "images.csv", IMAGE_COLS + extra_cols, image_rows)
    write_csv(out_dir / "raw_colors.csv", RAW_COLS, raw_rows)
    stats = {
        "images_dir": str(images_dir),
        "n_images": len(records),
        "n_review": sum(1 for r in image_rows if r["review"]),
        "n_error": sum(1 for r in image_rows if r["processing_status"] == "error"),
        "elapsed_sec": round(time.time() - t0, 1),
    }
    write_run_log(out_dir, "extract", cfg, stats)
    return stats


def run_analyze(cfg: dict, out_dir: Path) -> dict:
    out_dir = Path(out_dir)
    raw_path = out_dir / "raw_colors.csv"
    if not raw_path.exists():
        raise UserError(f"{raw_path} がありません。先に画像の解析 (extract) を実行してください。")
    by_image: dict = {}
    for r in read_csv(raw_path):
        by_image.setdefault(r["image_id"], []).append(r)
    rows = []
    for image_id, clusters in by_image.items():
        for c in analyze_clusters(clusters, cfg["analysis"]):
            rows.append({"image_id": image_id, **c})
    write_csv(out_dir / "analysis_colors.csv", ANALYSIS_COLS, rows)

    # 1画像1行の分析用データ (メイン色・サブ色 + メタデータ)
    colors_by_image: dict = {}
    for r in rows:
        colors_by_image.setdefault(r["image_id"], []).append(r)
    images = read_csv(out_dir / "images.csv") if (out_dir / "images.csv").exists() else []
    dataset = build_dataset(images, colors_by_image, cfg["dataset"])
    write_csv(out_dir / "dataset.csv", dataset_columns(cfg["dataset"]), dataset)

    stats = {"n_images": len(by_image), "n_colors": len(rows), "n_dataset_rows": len(dataset)}
    write_run_log(out_dir, "analyze", cfg, stats)
    return stats
