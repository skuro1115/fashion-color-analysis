"""再現性のための実行ログ (output/logs/<stage>_<日時>.json)。"""

from __future__ import annotations

import json
import platform
import subprocess
from datetime import datetime
from pathlib import Path

from .. import __version__


def _git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
            cwd=Path(__file__).parent, timeout=5,
        ).stdout.strip()
    except Exception:
        return ""


def write_run_log(out_dir: Path, stage: str, cfg: dict, stats: dict) -> Path:
    import cv2
    import numpy as np
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
