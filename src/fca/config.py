"""設定の読み込み。config.yaml に無い項目はここの既定値で補う。"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import yaml

from .errors import UserError

DEFAULTS: dict[str, Any] = {
    "paths": {
        "images_dir": "images",
        "output_dir": "output",
        "manifest": "manifest.csv",
    },
    "metadata": {
        "seasons": ["SS", "FW", "AW", "SPRING", "SUMMER", "FALL", "AUTUMN", "WINTER",
                    "RESORT", "CRUISE", "PREFALL", "PRESPRING", "PF", "PS"],
    },
    "image": {"max_size": 512},
    "foreground": {
        "border_width": 0.03,
        "bg_clusters": 3,
        "bg_cluster_min_share": 0.10,
        "bg_delta_e": 12.0,
        "remove_enclosed_background": False,
        "enclosed_bg_delta_e": 5.0,
        "morph_kernel": 5,
        "min_component_ratio": 0.2,
        "min_component_area": 0.005,
        "use_alpha": True,
        "min_ratio": 0.15,
        "max_ratio": 0.90,
    },
    "clustering": {"k": 10, "random_state": 42, "n_init": 4, "fit_sample": 20000, "edge_erode": 2},
    "analysis": {
        "min_cluster_ratio": 0.01,
        "merge_delta_e": None,
        "delta_e_metric": "ciede2000",
    },
    "review": {
        "min_largest_component": 0.05,
        "max_components": 3,
        "min_largest_share": 0.6,
        "min_pixels": 2000,
        "stability_scale": 0.3,
        "min_stability_iou": 0.85,
        "max_border_residual": 0.25,
        "max_border_touch": 0.30,
        "min_fg_bg_delta_e": 15.0,
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def load_config(path: str | Path | None) -> dict[str, Any]:
    if path is None or not Path(path).exists():
        return copy.deepcopy(DEFAULTS)
    try:
        with open(path, encoding="utf-8") as f:
            user = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        raise UserError(f"{path} の書き方に誤りがあります (インデントや「:」を確認してください)\n{e}") from e
    if not isinstance(user, dict):
        raise UserError(f"{path} の書き方に誤りがあります")
    return _deep_merge(DEFAULTS, user)
