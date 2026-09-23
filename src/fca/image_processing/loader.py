"""画像の列挙、パスからのメタデータ取得、manifest の結合、画像読み込み。

image_id は images_dir からの相対パス(拡張子なし, 例: "prada/2018_SS/001")。
連番と違い、画像を追加・削除しても既存画像の ID が変わらない。
"""

from __future__ import annotations

import csv
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

from ..errors import UserError

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
_PERIOD = re.compile(r"^(?P<year>(?:19|20)\d{2})(?:[_\-\s]?(?P<season>[A-Za-z][A-Za-z_\-\s]*))?$")
PATH_FIELDS = ("brand", "year", "season", "gender")
DEFAULT_SEASONS = (
    "SS", "FW", "AW", "SPRING", "SUMMER", "FALL", "AUTUMN", "WINTER",
    "RESORT", "CRUISE", "PREFALL", "PRESPRING", "PF", "PS",
)
DEFAULT_GENDERS = {
    "men": ["men", "mens", "man", "male", "メンズ", "男性"],
    "women": ["women", "womens", "woman", "female", "ladies", "レディース", "女性"],
    "unisex": ["unisex", "ユニセックス", "男女兼用"],
}


@dataclass
class ImageRecord:
    image_id: str
    path: Path
    brand: str = ""
    year: str = ""
    season: str = ""
    gender: str = ""
    filename: str = ""
    extra: dict[str, str] = field(default_factory=dict)


def _normalize_season(text: str) -> str:
    return re.sub(r"[_\-\s]", "", text).upper()


def parse_period(name: str, seasons=DEFAULT_SEASONS):
    """フォルダ名が時期 ("2018", "2018_SS", "2018-pre-fall" 等) なら (year, season)、違えば None。

    シーズン部分は seasons (config の metadata.seasons) にあるものだけ認める。
    "1017_ALYX" のようなブランド名を時期と誤認しないため。
    """
    m = _PERIOD.match(name.strip())
    if not m:
        return None
    season = _normalize_season(m.group("season") or "")
    if season and season not in {_normalize_season(s) for s in seasons}:
        return None
    return m.group("year"), season


def _normalize_word(text: str) -> str:
    return re.sub(r"[_\-\s'’.]", "", unicodedata.normalize("NFKC", text)).lower()


def parse_gender(name: str, genders=None):
    """フォルダ名が性別 (men / women / メンズ 等) なら正規化した値 ("men" 等)、違えば None。

    genders は {"men": ["men", "mens", ...], ...} (config の metadata.genders)。
    """
    word = _normalize_word(name)
    for value, aliases in (genders or DEFAULT_GENDERS).items():
        if word in {_normalize_word(a) for a in [value, *aliases]}:
            return value
    return None


def parse_path(rel: Path, seasons=DEFAULT_SEASONS, genders=None) -> dict[str, str]:
    """images/ からの相対パスからメタデータを取り出す。フォルダの深さ・順番は問わない。

      001.jpg                  -> すべて未指定
      prada/001.jpg            -> brand のみ
      2018_SS/001.jpg          -> 時期のみ
      prada/2018_SS/001.jpg    -> brand + 時期 (2018_SS/prada/ の順でもよい)
      prada/women/001.jpg      -> brand + 性別

    時期の形をしたフォルダ名は時期、性別の語 (men / women 等) は性別、
    それ以外で最初のフォルダ名を brand とする。
    取れない項目は空文字 (= 未指定)。
    """
    meta = {"brand": "", "year": "", "season": "", "gender": "", "filename": rel.name}
    for d in rel.parts[:-1]:
        period = parse_period(d, seasons)
        gender = None if period else parse_gender(d, genders)
        if period:
            if not meta["year"]:
                meta["year"], meta["season"] = period
        elif gender:
            meta["gender"] = meta["gender"] or gender
        elif not meta["brand"]:
            meta["brand"] = d
    return meta


def scan_images(images_dir: Path, seasons=DEFAULT_SEASONS, genders=None) -> list[ImageRecord]:
    records = []
    for p in sorted(images_dir.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in IMAGE_EXTS:
            continue
        if any(part.startswith(".") for part in p.relative_to(images_dir).parts):
            continue
        rel = p.relative_to(images_dir)
        meta = parse_path(rel, seasons, genders)
        records.append(ImageRecord(image_id=rel.with_suffix("").as_posix(), path=p, **meta))
    return records


def read_manifest(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or "image_id" not in reader.fieldnames:
            raise UserError(f"{path} の1行目に image_id 列が必要です。")
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
    base_cols = ["image_id", "brand", "year", "season", "gender", "source_url", "notes"]
    existing = read_manifest(path)
    if existing:
        with open(path, encoding="utf-8-sig", newline="") as f:
            cols = next(csv.reader(f))
    else:
        cols = base_cols
    new = [r for r in records if r.image_id not in existing]
    mode = "a" if existing else "w"
    with open(path, mode, encoding="utf-8-sig", newline="") as f:  # Excel で編集できるよう BOM 付き
        writer = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        if not existing:
            writer.writeheader()
        for r in new:
            writer.writerow({"image_id": r.image_id, "brand": r.brand, "year": r.year, "season": r.season, "gender": r.gender})
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
