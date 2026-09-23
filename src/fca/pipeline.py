"""extract / analyze の各ステージ。ステージ間は CSV でのみ受け渡す。"""

from __future__ import annotations

import csv
import json
import platform
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from . import __version__
from .analyze import analyze_clusters
from .colors import rgb_to_lab
from .dataset import apply_manifest, load_image, read_manifest, scan_images
from .extract import extract_clusters
from .segment import review_reasons, segment

IMAGE_COLS = [
    "image_id", "brand", "year", "season", "filename", "review", "review_reasons",
    "processing_status", "error_message", "original_path", "processed_width", "processed_height",
    "segmentation_method", "foreground_ratio", "fg_pixels", "n_components",
    "largest_component_ratio", "largest_share", "border_touch", "border_residual",
    "fg_bg_delta_e", "stability_iou",
]
RAW_COLS = ["image_id", "cluster_rank", "L", "a", "b", "r", "g", "b_rgb", "hex", "ratio", "pixels"]
ANALYSIS_COLS = [
    "image_id", "color_rank", "L", "a", "b", "r", "g", "b_rgb", "hex",
    "ratio", "ratio_unfiltered", "pixels", "source_clusters",
]


def safe_name(image_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_\-.]", "_", image_id.replace("/", "__"))


def _write_csv(path: Path, cols: list[str], rows: list[dict]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
            cwd=Path(__file__).parent, timeout=5,
        ).stdout.strip()
    except Exception:
        return ""


def _write_run_log(out_dir: Path, stage: str, cfg: dict, stats: dict) -> Path:
    import skimage
    import sklearn

    log_dir = out_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    log = {
        "stage": stage,
        "executed_at": now.isoformat(timespec="seconds"),
        "tool_version": __version__,
        "git_commit": _git_commit(),
        "python": platform.python_version(),
        "libraries": {
            "numpy": np.__version__, "opencv": cv2.__version__,
            "scikit-learn": sklearn.__version__, "scikit-image": skimage.__version__,
        },
        "config": cfg,
        **stats,
    }
    path = log_dir / f"{stage}_{now.strftime('%Y%m%d_%H%M%S')}.json"
    path.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


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


def run_extract(cfg: dict, images_dir: Path, out_dir: Path, limit: int | None = None) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "masks").mkdir(exist_ok=True)
    (out_dir / "cutouts").mkdir(exist_ok=True)

    records = scan_images(images_dir)
    if limit:
        records = records[:limit]
    manifest_path = Path(cfg["paths"]["manifest"])
    extra_cols = apply_manifest(records, read_manifest(manifest_path))

    fg_cfg, rv_cfg, cl_cfg = cfg["foreground"], cfg["review"], cfg["clustering"]
    image_rows, raw_rows = [], []
    t0 = time.time()
    for i, rec in enumerate(records, start=1):
        row = {
            "image_id": rec.image_id, "brand": rec.brand, "year": rec.year, "season": rec.season,
            "filename": rec.filename, "original_path": str(rec.path), **rec.extra,
        }
        try:
            rgb, alpha = load_image(rec.path, cfg["image"]["max_size"])
            lab = rgb_to_lab(rgb)
            seg = segment(lab, alpha, fg_cfg, rv_cfg, seed=cl_cfg["random_state"])
            reasons = review_reasons(seg.metrics, fg_cfg, rv_cfg)
            color_mask = _erode(seg.mask, cl_cfg["edge_erode"])
            clusters = extract_clusters(lab, color_mask, cl_cfg) if color_mask.any() else []
            if not clusters:
                reasons.append("no_colors")
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
        flag = " review" if row["review"] else ""
        print(f"[{i}/{len(records)}] {rec.image_id}{flag}", flush=True)

    _write_csv(out_dir / "images.csv", IMAGE_COLS + extra_cols, image_rows)
    _write_csv(out_dir / "raw_colors.csv", RAW_COLS, raw_rows)
    stats = {
        "images_dir": str(images_dir),
        "n_images": len(records),
        "n_review": sum(1 for r in image_rows if r["review"]),
        "n_error": sum(1 for r in image_rows if r["processing_status"] == "error"),
        "elapsed_sec": round(time.time() - t0, 1),
    }
    _write_run_log(out_dir, "extract", cfg, stats)
    return stats


def run_analyze(cfg: dict, out_dir: Path) -> dict:
    raw = read_csv(out_dir / "raw_colors.csv")
    by_image: dict[str, list[dict]] = {}
    for r in raw:
        by_image.setdefault(r["image_id"], []).append(r)
    rows = []
    for image_id, clusters in by_image.items():
        for c in analyze_clusters(clusters, cfg["analysis"]):
            rows.append({"image_id": image_id, **c})
    _write_csv(out_dir / "analysis_colors.csv", ANALYSIS_COLS, rows)
    stats = {"n_images": len(by_image), "n_colors": len(rows)}
    _write_run_log(out_dir, "analyze", cfg, stats)
    return stats
