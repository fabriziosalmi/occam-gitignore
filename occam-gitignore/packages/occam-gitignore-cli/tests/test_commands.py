# SPDX-License-Identifier: MIT
"""End-to-end tests for the `check` and `apply` CLI commands."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from occam_gitignore_cli.app import app
from occam_gitignore_core.reconcile import MANAGED_BLOCK_END, MANAGED_BLOCK_START

# Pin the data directory to the workspace `data/` so the tests never depend on
# whichever bundled/monorepo copy `data_root()` happens to resolve first.
_DATA = Path(__file__).resolve().parents[3] / "data"

runner = CliRunner()


@pytest.fixture(autouse=True)
def _use_workspace_data(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OCCAM_GITIGNORE_DATA_DIR", str(_DATA))


def _python_repo(tmp_path: Path) -> Path:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", "utf-8")
    (tmp_path / "main.py").write_text("print('hi')\n", "utf-8")
    return tmp_path


# --------------------------------------------------------------------------- #
# check                                                                        #
# --------------------------------------------------------------------------- #


def test_check_fails_and_lists_missing_when_no_gitignore(tmp_path: Path) -> None:
    repo = _python_repo(tmp_path)
    result = runner.invoke(app, ["check", str(repo)])
    assert result.exit_code == 1
    # The now-universal secret line must be reported as missing.
    assert ".env" in result.output
    assert "*.pem" in result.output


def test_check_passes_after_apply(tmp_path: Path) -> None:
    repo = _python_repo(tmp_path)
    assert runner.invoke(app, ["apply", str(repo)]).exit_code == 0
    result = runner.invoke(app, ["check", str(repo)])
    assert result.exit_code == 0


def test_check_allows_extra_project_lines(tmp_path: Path) -> None:
    repo = _python_repo(tmp_path)
    runner.invoke(app, ["apply", str(repo)])
    gi = repo / ".gitignore"
    gi.write_text(gi.read_text("utf-8") + "\n# project-specific\n/my-artifacts/\n", "utf-8")
    result = runner.invoke(app, ["check", str(repo)])
    assert result.exit_code == 0


def test_check_reports_only_missing_not_extras(tmp_path: Path) -> None:
    repo = _python_repo(tmp_path)
    (repo / ".gitignore").write_text("/only-my-line/\n", "utf-8")
    result = runner.invoke(app, ["check", str(repo)])
    assert result.exit_code == 1
    assert "/only-my-line/" not in result.output  # extras are never reported


# --------------------------------------------------------------------------- #
# apply                                                                        #
# --------------------------------------------------------------------------- #


def test_apply_creates_managed_block_and_preserves_custom_lines(tmp_path: Path) -> None:
    repo = _python_repo(tmp_path)
    gi = repo / ".gitignore"
    gi.write_text("# hand-written\nsecrets.txt\n", "utf-8")

    result = runner.invoke(app, ["apply", str(repo)])
    assert result.exit_code == 0

    content = gi.read_text("utf-8")
    assert "# hand-written" in content
    assert "secrets.txt" in content
    assert MANAGED_BLOCK_START in content
    assert MANAGED_BLOCK_END in content
    assert ".env" in content
    # The block comes first; hand-written lines follow it and therefore win.
    assert content.index(MANAGED_BLOCK_END) < content.index("secrets.txt")


def test_apply_is_idempotent_on_disk(tmp_path: Path) -> None:
    repo = _python_repo(tmp_path)
    gi = repo / ".gitignore"
    gi.write_text("keep-me\n", "utf-8")

    runner.invoke(app, ["apply", str(repo)])
    first = gi.read_text("utf-8")
    runner.invoke(app, ["apply", str(repo)])
    second = gi.read_text("utf-8")

    assert first == second
    assert second.count(MANAGED_BLOCK_START) == 1


def test_apply_then_reapply_updates_in_place_single_block(tmp_path: Path) -> None:
    repo = _python_repo(tmp_path)
    runner.invoke(app, ["apply", str(repo)])
    # Add a new ecosystem, re-apply: still exactly one block.
    (repo / "package.json").write_text("{}\n", "utf-8")
    runner.invoke(app, ["apply", str(repo)])
    content = (repo / ".gitignore").read_text("utf-8")
    assert content.count(MANAGED_BLOCK_START) == 1
    assert "node_modules/" in content  # node rules merged in


def test_apply_fails_on_malformed_block(tmp_path: Path) -> None:
    repo = _python_repo(tmp_path)
    (repo / ".gitignore").write_text(f"{MANAGED_BLOCK_START}\nfoo\n", "utf-8")
    result = runner.invoke(app, ["apply", str(repo)])
    assert result.exit_code == 2


# --------------------------------------------------------------------------- #
# generate --write                                                             #
# --------------------------------------------------------------------------- #


def test_generate_write_refuses_to_clobber_a_different_gitignore(tmp_path: Path) -> None:
    repo = _python_repo(tmp_path)
    gi = repo / ".gitignore"
    gi.write_text("private/\n", "utf-8")
    result = runner.invoke(app, ["generate", str(repo), "--write"])
    assert result.exit_code == 2
    assert "apply" in result.output
    assert gi.read_text("utf-8") == "private/\n"


def test_generate_write_force_replaces(tmp_path: Path) -> None:
    repo = _python_repo(tmp_path)
    gi = repo / ".gitignore"
    gi.write_text("private/\n", "utf-8")
    assert runner.invoke(app, ["generate", str(repo), "--write", "--force"]).exit_code == 0
    assert "private/" not in gi.read_text("utf-8")


def test_generate_write_creates_and_rewrites_identical_file(tmp_path: Path) -> None:
    repo = _python_repo(tmp_path)
    assert runner.invoke(app, ["generate", str(repo), "--write"]).exit_code == 0
    # Re-running over its own identical output is not a clobber.
    assert runner.invoke(app, ["generate", str(repo), "--write"]).exit_code == 0
