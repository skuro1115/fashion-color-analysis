from pathlib import Path

import numpy as np
from PIL import Image

from fca.analyze import analyze_clusters
from fca.colors import rgb_to_lab
from fca.config import load_config
from fca.dataset import parse_path
from fca.extract import extract_clusters
from fca.pipeline import read_csv, run_analyze, run_extract
from fca.preview import build_preview
from fca.segment import review_reasons, segment

CFG = load_config(None)


def _garment(bg, fg, size=(300, 400)):
    """背景色 bg の上に、胴体+袖の形をした fg 色の服を描いた画像。"""
    w, h = size
    img = np.full((h, w, 3), bg, dtype=np.uint8)
    img[80:360, 90:210] = fg      # 胴
    img[80:200, 50:90] = fg       # 左袖
    img[80:200, 210:250] = fg     # 右袖
    return img


def _seg(img, alpha=None):
    lab = rgb_to_lab(img)
    seg = segment(lab, alpha, CFG["foreground"], CFG["review"], seed=42)
    return lab, seg


def test_parse_path():
    assert parse_path(Path("prada/2018_SS/001.jpg")) == {
        "brand": "prada", "year": "2018", "season": "SS", "filename": "001.jpg"}
    assert parse_path(Path("gucci/2019/x.png"))["year"] == "2019"
    assert parse_path(Path("x.png"))["brand"] == ""


def test_white_background_navy_garment():
    img = _garment((255, 255, 255), (31, 39, 70))
    lab, seg = _seg(img)
    expected = (280 * 120 + 2 * 120 * 40) / (300 * 400)
    assert abs(seg.metrics["foreground_ratio"] - expected) < 0.02
    assert review_reasons(seg.metrics, CFG["foreground"], CFG["review"]) == []
    clusters = extract_clusters(lab, seg.mask, CFG["clustering"])
    assert clusters[0]["hex"] == "#1F2746"
    assert abs(sum(c["ratio"] for c in clusters) - 1) < 1e-4


def test_white_inner_part_kept_on_gray_background():
    img = _garment((200, 200, 200), (120, 20, 30))
    img[150:250, 130:170] = 255  # 胴の中央に白いパーツ(外周とは繋がらない)
    _, seg = _seg(img)
    assert seg.mask[200, 150]


def test_small_product_is_reviewed():
    img = np.full((400, 300, 3), 255, dtype=np.uint8)
    img[180:220, 130:170] = (200, 0, 0)
    _, seg = _seg(img)
    assert "fg_too_small" in review_reasons(seg.metrics, CFG["foreground"], CFG["review"])


def test_noisy_background_is_reviewed():
    rng = np.random.default_rng(0)
    img = rng.integers(0, 256, size=(400, 300, 3), dtype=np.uint8)
    img[80:360, 90:210] = (30, 30, 30)
    _, seg = _seg(img)
    assert review_reasons(seg.metrics, CFG["foreground"], CFG["review"])


def test_alpha_mask_used():
    img = _garment((0, 0, 0), (240, 200, 0))
    alpha = np.where((img == (240, 200, 0)).all(-1), 255, 0).astype(np.uint8)
    _, seg = _seg(img, alpha)
    assert seg.method == "alpha"
    assert seg.mask.sum() == (alpha > 0).sum()


def test_analysis_filter_and_merge():
    raw = [
        {"cluster_rank": 1, "L": 30, "a": 5, "b": -20, "ratio": 0.5, "pixels": 500},
        {"cluster_rank": 2, "L": 32, "a": 5, "b": -21, "ratio": 0.3, "pixels": 300},
        {"cluster_rank": 3, "L": 90, "a": 0, "b": 5, "ratio": 0.195, "pixels": 195},
        {"cluster_rank": 4, "L": 50, "a": 60, "b": 40, "ratio": 0.005, "pixels": 5},
    ]
    no_merge = analyze_clusters(raw, {"min_cluster_ratio": 0.01, "merge_delta_e": None})
    assert [c["source_clusters"] for c in no_merge] == ["1", "2", "3"]
    assert abs(sum(c["ratio"] for c in no_merge) - 1) < 1e-6

    merged = analyze_clusters(raw, {"min_cluster_ratio": 0.01, "merge_delta_e": 5.0})
    assert merged[0]["source_clusters"] == "1;2"
    assert abs(merged[0]["ratio"] - 800 / 995) < 1e-4
    assert len(merged) == 2


def test_end_to_end(tmp_path):
    images = tmp_path / "images" / "brand_a" / "2020_SS"
    images.mkdir(parents=True)
    Image.fromarray(_garment((255, 255, 255), (31, 39, 70))).save(images / "001.jpg", quality=95)
    Image.fromarray(_garment((180, 180, 180), (200, 30, 40))).save(images / "002.png")
    (images / "broken.jpg").write_bytes(b"not an image")

    cfg = load_config(None)
    cfg["paths"]["manifest"] = str(tmp_path / "none.csv")
    out = tmp_path / "output"
    stats = run_extract(cfg, tmp_path / "images", out)
    assert stats["n_images"] == 3 and stats["n_error"] == 1

    rows = {r["image_id"]: r for r in read_csv(out / "images.csv")}
    assert rows["brand_a/2020_SS/001"]["review"] == "False"
    assert rows["brand_a/2020_SS/broken"]["processing_status"] == "error"

    run_analyze(cfg, out)
    ana = read_csv(out / "analysis_colors.csv")
    main = {r["image_id"]: r for r in ana if r["color_rank"] == "1"}
    assert int(main["brand_a/2020_SS/002"]["r"]) > 150

    # 同じ入力 -> 同じ結果
    first = (out / "raw_colors.csv").read_text()
    run_extract(cfg, tmp_path / "images", out)
    assert (out / "raw_colors.csv").read_text() == first

    assert build_preview(out).exists()
