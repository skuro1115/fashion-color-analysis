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


def test_skills_have_matching_names():
    """.claude/skills/<名前>/SKILL.md の name がフォルダ名と一致し、説明があること。"""
    skills = sorted((ROOT / ".claude" / "skills").glob("*/SKILL.md"))
    assert {p.parent.name for p in skills} >= {"request", "guide", "run-analysis", "update"}
    for p in skills:
        head = p.read_text(encoding="utf-8").split("---")[1]
        assert f"name: {p.parent.name}\n" in head, p
        assert "description:" in head, p


def test_agents_skills_mirror_claude_skills():
    """.agents/skills (Codex 等向け) は .claude/skills と同じ内容に保つ。"""
    claude = {p.relative_to(ROOT / ".claude" / "skills"): p.read_text(encoding="utf-8")
              for p in (ROOT / ".claude" / "skills").glob("*/SKILL.md")}
    agents = {p.relative_to(ROOT / ".agents" / "skills"): p.read_text(encoding="utf-8")
              for p in (ROOT / ".agents" / "skills").glob("*/SKILL.md")}
    assert agents == claude, ".claude/skills を変えたら .agents/skills にも同じ内容をコピーしてください"


def test_update_hook_is_configured():
    """起動時の更新確認フックが設定され、スクリプトが実行可能であること。"""
    import json
    import os

    settings = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    commands = [h["command"] for m in settings["hooks"]["SessionStart"] for h in m["hooks"]]
    assert any("check-update.sh" in c for c in commands)
    assert os.access(ROOT / ".claude" / "hooks" / "check-update.sh", os.X_OK)
