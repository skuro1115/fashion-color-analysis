"""リポジトリ構成のルールを守れているかの確認 (AI による改修で壊れやすい箇所)。"""

import re
import sys
from pathlib import Path

import pytest

from fca.cli.main import main

ROOT = Path(__file__).resolve().parents[1]


def _names(lines):
    return {re.split(r"[<>=!~\[ ]", l.strip(), maxsplit=1)[0].lower() for l in lines if l.strip() and not l.strip().startswith("#")}


def test_requirements_match_pyproject():
    if sys.version_info >= (3, 11):
        import tomllib
    else:
        pytest.importorskip("tomli")
        import tomli as tomllib
    deps = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["dependencies"]
    reqs = (ROOT / "requirements.txt").read_text().splitlines()
    assert _names(deps) == _names(reqs), "requirements.txt と pyproject.toml の dependencies を一致させてください"


def test_run_command_is_executable():
    import os

    assert os.access(ROOT / "run.command", os.X_OK)


def test_no_images_gives_friendly_error(tmp_path, capsys):
    (tmp_path / "images").mkdir()
    with pytest.raises(SystemExit) as e:
        main(["run", "--images", str(tmp_path / "images"), "--output", str(tmp_path / "out"),
              "-c", str(tmp_path / "none.yaml")])
    assert e.value.code == 2
    assert "画像がありません" in capsys.readouterr().err
