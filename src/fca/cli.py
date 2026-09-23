"""fca コマンド。

  fca extract        画像 -> images.csv, raw_colors.csv, masks/, cutouts/
  fca analyze        raw_colors.csv -> analysis_colors.csv (画像を読まない)
  fca preview        -> preview.html
  fca run            extract + analyze + preview
  fca init-manifest  manifest.csv に未登録画像の行を追記
"""

from __future__ import annotations

import argparse
from pathlib import Path

from .config import load_config
from .dataset import scan_images, write_manifest_template


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="fca", description="服画像の代表色抽出ツール")
    parser.add_argument("command", choices=["extract", "analyze", "preview", "run", "init-manifest"])
    parser.add_argument("-c", "--config", default="config.yaml")
    parser.add_argument("--images", help="画像フォルダ (config の paths.images_dir を上書き)")
    parser.add_argument("--output", help="出力フォルダ (config の paths.output_dir を上書き)")
    parser.add_argument("--manifest", help="manifest.csv (config の paths.manifest を上書き)")
    parser.add_argument("--limit", type=int, help="先頭 N 枚だけ処理 (試行用)")
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    for key in ("images", "output", "manifest"):
        value = getattr(args, key)
        if value:
            cfg["paths"]["images_dir" if key == "images" else "output_dir" if key == "output" else key] = value
    images_dir = Path(cfg["paths"]["images_dir"])
    out_dir = Path(cfg["paths"]["output_dir"])

    if args.command == "init-manifest":
        n = write_manifest_template(scan_images(images_dir), Path(cfg["paths"]["manifest"]))
        print(f"{cfg['paths']['manifest']}: {n} 行追加")
        return

    # 重い依存の import はここで行う (init-manifest を軽くするため)
    from .pipeline import run_analyze, run_extract
    from .preview import build_preview

    if args.command in ("extract", "run"):
        if not images_dir.is_dir():
            parser.error(f"画像フォルダがありません: {images_dir}")
        stats = run_extract(cfg, images_dir, out_dir, args.limit)
        print(f"extract: {stats['n_images']} 枚 / review {stats['n_review']} / error {stats['n_error']} ({stats['elapsed_sec']}s)")
    if args.command in ("analyze", "run"):
        stats = run_analyze(cfg, out_dir)
        print(f"analyze: {stats['n_images']} 枚 / {stats['n_colors']} 色")
    if args.command in ("preview", "run"):
        print(f"preview: {build_preview(out_dir)}")


if __name__ == "__main__":
    main()
