from pathlib import Path

import numpy as np
from PIL import Image

from fca.analysis.dataset import build_dataset
from fca.analysis.merge import analyze_clusters
from fca.color_extraction.colorspace import rgb_to_lab
from fca.color_extraction.kmeans import extract_clusters
from fca.config import load_config
from fca.image_processing.loader import parse_path
from fca.image_processing.review import review_reasons
from fca.image_processing.segmentation import segment
from fca.pipeline import build_preview, run_analyze, run_extract
from fca.reporting.csv_io import read_csv

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


def _meta(path):
    m = parse_path(Path(path))
    return m["brand"], m["year"], m["season"]


def test_parse_path():
    assert parse_path(Path("prada/2018_SS/001.jpg")) == {
        "brand": "prada", "year": "2018", "season": "SS", "gender": "", "filename": "001.jpg"}
    assert _meta("gucci/2019/x.png") == ("gucci", "2019", "")


def test_parse_path_flexible():
    assert _meta("001.jpg") == ("", "", "")                      # 指定なし
    assert _meta("prada/001.jpg") == ("prada", "", "")           # ブランドのみ
    assert _meta("2018_SS/001.jpg") == ("", "2018", "SS")        # 時期のみ
    assert _meta("2018/001.jpg") == ("", "2018", "")
    assert _meta("2018_SS/prada/001.jpg") == ("prada", "2018", "SS")  # 順番は問わない
    assert _meta("prada/2018_SS/extra/001.jpg") == ("prada", "2018", "SS")
    assert _meta("prada/2018-pre-fall/001.jpg") == ("prada", "2018", "PREFALL")
    assert _meta("prada/2018fw/001.jpg") == ("prada", "2018", "FW")
    # 時期に見えるがシーズン表記が未知 / 年の範囲外 -> ブランド扱い
    assert _meta("1017_ALYX/001.jpg") == ("1017_ALYX", "", "")
    assert _meta("3000/001.jpg") == ("3000", "", "")


def test_parse_path_gender():
    g = lambda p: parse_path(Path(p))["gender"]
    assert g("prada/women/2018_SS/001.jpg") == "women"
    assert g("Mens/001.jpg") == "men"
    assert g("prada/メンズ/001.jpg") == "men"
    assert g("unisex/001.jpg") == "unisex"
    assert g("prada/001.jpg") == ""
    assert _meta("women/prada/001.jpg") == ("prada", "", "")   # 性別フォルダはブランドにしない


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


def test_unspecified_metadata_end_to_end(tmp_path):
    root = tmp_path / "images"
    img = Image.fromarray(_garment((255, 255, 255), (31, 39, 70)))
    for rel in ["loose.jpg", "brand_x/a.jpg", "2020_FW/b.jpg"]:
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        img.save(root / rel)
    cfg = load_config(None)
    cfg["paths"]["manifest"] = str(tmp_path / "none.csv")
    out = tmp_path / "output"
    run_extract(cfg, root, out)
    rows = {r["image_id"]: (r["brand"], r["year"], r["season"]) for r in read_csv(out / "images.csv")}
    assert rows == {
        "loose": ("", "", ""), "brand_x/a": ("brand_x", "", ""), "2020_FW/b": ("", "2020", "FW")}
    html = build_preview(out).read_text()
    assert "ブランド未指定" in html and "時期未指定" in html

    run_analyze(cfg, out)
    ds = {r["image_id"]: r for r in read_csv(out / "dataset.csv")}
    assert set(ds) == {"loose", "brand_x/a", "2020_FW/b"}   # 未指定も含めて全画像
    assert ds["loose"]["main_hex"].startswith("#") and ds["loose"]["brand"] == ""


def test_build_dataset_main_and_sub():
    images = [{"image_id": "a", "brand": "prada", "year": "2018", "season": "SS", "gender": "women",
               "review": "False", "review_reasons": ""},
              {"image_id": "b", "brand": "", "year": "", "season": "", "gender": "", "review": "True",
               "review_reasons": "error"}]
    def c(rank, hex_, ratio):
        return {"color_rank": str(rank), "hex": hex_, "ratio": str(ratio), "r": 0, "g": 0, "b_rgb": 0,
                "L": 0, "a": 0, "b": 0}
    colors = {"a": [c(1, "#1C2542", 0.70), c(2, "#C8AA78", 0.27), c(3, "#FFFFFF", 0.03)]}
    colors["a"][0].update(r=28, g=37, b_rgb=66, a=6.2, b=-20.7)        # 紺
    colors["a"][1].update(r=200, g=170, b_rgb=120, a=4.2, b=29.9)      # ベージュ
    rows = build_dataset(images, colors, {"n_sub_colors": 2, "min_sub_ratio": 0.05, "achromatic_chroma": 8.0})
    a, b = rows
    assert (a["main_hex"], a["main_ratio"]) == ("#1C2542", "0.7")
    assert (a["sub1_hex"], a["sub1_ratio"]) == ("#C8AA78", "0.27")
    assert "sub2_hex" not in a          # 3% は min_sub_ratio 未満
    assert a["all_colors"] == "#1C2542:70.0%;#C8AA78:27.0%;#FFFFFF:3.0%"
    assert a["gender"] == "women"
    assert b["n_colors"] == 0 and "main_hex" not in b   # 色が取れない画像も行は残す
    assert (a["main_hue"], a["main_sat"], a["main_bri"]) == (225.8, 57.6, 25.9)
    assert 35 < a["sub1_hue"] < 40


def test_hsb_achromatic_and_column_order():
    from fca.analysis.dataset import dataset_columns
    from fca.color_extraction.colorspace import rgb_to_hsb

    assert rgb_to_hsb(128, 128, 128, 0.0, 0.0, 8.0) == (None, 0.0, 50.2)      # グレー: 色相なし
    assert rgb_to_hsb(30, 30, 34, 0.5, -2.5, 8.0)[0] is None                  # ほぼ黒: 色相なし
    assert rgb_to_hsb(200, 30, 40, 60.0, 35.0, 8.0)[0] == 356.5               # 赤
    cols = dataset_columns({"n_sub_colors": 2})
    # 既存列の並びは変えず、HSB は末尾に追加
    assert cols.index("review_reasons") < cols.index("main_hue")
    assert cols[-3:] == ["sub2_hue", "sub2_sat", "sub2_bri"]
