"""画像の列挙、パスからのメタデータ取得、manifest の結合、画像読み込み。

image_id は images_dir からの相対パス(拡張子なし, 例: "prada/2018_SS/001")。
連番と違い、画像を追加・削除しても既存画像の ID が変わらない。
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
_YEAR_SEASON = re.compile(r"^(?P<year>\d{4})(?:[_\-\s]?(?P<season>[A-Za-z]+))?$")
PATH_FIELDS = ("brand", "year", "season")


@dataclass
class ImageRecord:
    image_id: str
    path: Path
    brand: str = ""
    year: str = ""
    season: str = ""
    filename: str = ""
    extra: dict[str, str] = field(default_factory=dict)


def parse_path(rel: Path) -> dict[str, str]:
    """images/<brand>/<year>_<season>/<file> からメタデータを取り出す。

    階層が浅い/深い場合も取れる範囲で埋め、取れない項目は空文字にする。
    """
    parts = rel.parts
    meta = {"brand": "", "year": "", "season": "", "filename": rel.name}
    dirs = parts[:-1]
    if dirs:
        meta["brand"] = dirs[0]
    for d in dirs[1:]:
        m = _YEAR_SEASON.match(d)
        if m:
            meta["year"] = m.group("year")
            meta["season"] = (m.group("season") or "").upper()
            break
    return meta


def scan_images(images_dir: Path) -> list[ImageRecord]:
    records = []
    for p in sorted(images_dir.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in IMAGE_EXTS:
            continue
        if any(part.startswith(".") for part in p.relative_to(images_dir).parts):
            continue
        rel = p.relative_to(images_dir)
        meta = parse_path(rel)
        records.append(ImageRecord(image_id=rel.with_suffix("").as_posix(), path=p, **meta))
    return records


def read_manifest(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or "image_id" not in reader.fieldnames:
            raise ValueError(f"{path}: 'image_id' 列が必要です")
        return {row["image_id"].strip(): row for row in reader if row.get("image_id")}


def apply_manifest(records: list[ImageRecord], manifest: dict[str, dict[str, str]]) -> list[str]:
    """manifest の値でパス由来の値を上書きし、追加列は extra に入れる。追加列名を返す。"""
    extra_cols: list[str] = []
    for row in manifest.values():
        for col in row:
            if col not in ("image_id", "filename", *PATH_FIELDS) and col not in extra_cols:
                extra_cols.append(col)
    for rec in records:
        row = manifest.get(rec.image_id)
        if not row:
            continue
        for key in PATH_FIELDS:
            value = (row.get(key) or "").strip()
            if value:
                setattr(rec, key, value)
        rec.extra = {c: (row.get(c) or "") for c in extra_cols}
    return extra_cols


def write_manifest_template(records: list[ImageRecord], path: Path) -> int:
    """manifest.csv に未登録の画像行を追記する(既存行は変更しない)。追記数を返す。"""
    base_cols = ["image_id", "brand", "year", "season", "category", "source_url", "notes"]
    existing = read_manifest(path)
    if existing:
        with open(path, encoding="utf-8-sig", newline="") as f:
            cols = next(csv.reader(f))
    else:
        cols = base_cols
    new = [r for r in records if r.image_id not in existing]
    mode = "a" if existing else "w"
    with open(path, mode, encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        if not existing:
            writer.writeheader()
        for r in new:
            writer.writerow({"image_id": r.image_id, "brand": r.brand, "year": r.year, "season": r.season})
    return len(new)


def load_image(path: Path, max_size: int) -> tuple[np.ndarray, np.ndarray | None]:
    """RGB uint8 と (あれば) alpha uint8 を返す。EXIF の回転を反映し、最大辺を max_size に縮小。"""
    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im)
        im.load()
        has_alpha = im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info)
        im = im.convert("RGBA") if has_alpha else im.convert("RGB")
        if max(im.size) > max_size:
            im.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        arr = np.asarray(im)
    if has_alpha:
        return arr[..., :3].copy(), arr[..., 3].copy()
    return arr, None
