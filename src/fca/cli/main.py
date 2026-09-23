"""fca コマンド (pipeline.py の薄いラッパー。解析ロジックはここに書かない)。

  fca extract        画像 -> images.csv, raw_colors.csv, masks/, cutouts/
  fca analyze        raw_colors.csv -> analysis_colors.csv (画像を読まない)
  fca preview        -> preview.html
  fca run            extract + analyze + preview
  fca init-manifest  manifest.csv に未登録画像の行を追記

終了コード: 0 = 成功 / 2 = 利用者が直せるエラー (UserError) / 1 = 想定外のエラー
"""

from __future__ import annotations

import argparse
import sys
import traceback
from datetime import datetime
from pathlib import Path

from ..config import load_config
from ..errors import UserError


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fca", description="服画像の代表色抽出ツール")
    parser.add_argument("command", choices=["extract", "analyze", "preview", "run", "init-manifest"])
    parser.add_argument("-c", "--config", default="config.yaml")
    parser.add_argument("--images", help="画像フォルダ (config の paths.images_dir を上書き)")
    parser.add_argument("--output", help="出力フォルダ (config の paths.output_dir を上書き)")
    parser.add_argument("--manifest", help="manifest.csv (config の paths.manifest を上書き)")
    parser.add_argument("--limit", type=int, help="先頭 N 枚だけ処理 (試行用)")
    return parser


def _progress(i: int, total: int, image_id: str, review: bool) -> None:
    flag = "  ← 要確認" if review else ""
    print(f"  [{i}/{total}] {image_id}{flag}", flush=True)


def _run(args) -> None:
    cfg = load_config(args.config)
    overrides = {"images": "images_dir", "output": "output_dir", "manifest": "manifest"}
    for arg, key in overrides.items():
        if getattr(args, arg):
            cfg["paths"][key] = getattr(args, arg)
    images_dir = Path(cfg["paths"]["images_dir"])
    out_dir = Path(cfg["paths"]["output_dir"])

    if args.command == "init-manifest":
        from ..image_processing.loader import scan_images, write_manifest_template

        n = write_manifest_template(scan_images(images_dir, cfg["metadata"]["seasons"]), Path(cfg["paths"]["manifest"]))
        print(f"{cfg['paths']['manifest']}: {n} 行追加")
        return

    from .. import pipeline

    if args.command in ("extract", "run"):
        print("画像を解析しています...")
        s = pipeline.run_extract(cfg, images_dir, out_dir, args.limit, progress=_progress)
        print(f"解析完了: {s['n_images']} 枚 (要確認 {s['n_review']} 枚 / エラー {s['n_error']} 枚, {s['elapsed_sec']}秒)")
    if args.command in ("analyze", "run"):
        s = pipeline.run_analyze(cfg, out_dir)
        print(f"色の整理完了: {s['n_images']} 枚 / {s['n_colors']} 色")
    if args.command in ("preview", "run"):
        print(f"確認ページ: {pipeline.build_preview(out_dir)}")


def main(argv: list | None = None) -> None:
    args = _build_parser().parse_args(argv)
    try:
        _run(args)
    except UserError as e:
        print(f"\n[エラー] {e}", file=sys.stderr)
        sys.exit(2)
    except KeyboardInterrupt:
        print("\n中断しました", file=sys.stderr)
        sys.exit(130)
    except Exception:
        log = Path("output") / "logs" / f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(traceback.format_exc(), encoding="utf-8")
        print(
            "\n[エラー] 予期しないエラーが発生しました。\n"
            f"詳細は {log} に保存しました。AI (Claude Code 等) に見せると原因を調べられます。",
            file=sys.stderr,
        )
        sys.exit(1)
