# SPDX-License-Identifier: MIT
"""`audit` and the `apply` warning: tracked files matched by ignore rules."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from occam_gitignore_cli.app import app
from occam_gitignore_cli.audit import tracked_ignored

_DATA = Path(__file__).resolve().parents[3] / "data"

runner = CliRunner()


@pytest.fixture(autouse=True)
def _use_workspace_data(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OCCAM_GITIGNORE_DATA_DIR", str(_DATA))


def _repo(root: Path, files: dict[str, str]) -> Path:
    subprocess.run(["git", "init", "-q", str(root)], check=True)  # noqa: S603, S607
    for rel, content in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(content, "utf-8")
    subprocess.run(["git", "-C", str(root), "add", "-A", "-f"], check=True)  # noqa: S603, S607
    return root


def test_secrets_are_listed_first_and_labelled(tmp_path: Path) -> None:
    repo = _repo(tmp_path, {
        "package.json": "{}",
        "src/index.js": "",
        ".cache/x.json": "",  # sorts before `.env`: secrets must still come first
        "dist/index.js": "",
        "certs/server.key": "",
        ".env": "",
    })
    result = runner.invoke(app, ["audit", str(repo)])
    assert result.exit_code == 1
    rows = [line.split("\t") for line in result.stdout.splitlines()]
    assert rows == [
        ["secret", ".env", ".env"],
        ["secret", "certs/server.key", "*.key"],
        ["tracked", ".cache/x.json", ".cache/"],
        ["tracked", "dist/index.js", "dist/"],
    ]
    assert "rotate" in result.stderr


def test_own_lines_can_keep_a_tracked_dir(tmp_path: Path) -> None:
    # A GitHub Action commits dist/ on purpose and says so below the block.
    repo = _repo(tmp_path, {
        "package.json": "{}",
        "dist/index.js": "",
        ".gitignore": "!dist/\n",
    })
    result = runner.invoke(app, ["audit", str(repo)])
    assert result.exit_code == 0, result.stdout


def test_clean_repo_passes(tmp_path: Path) -> None:
    repo = _repo(tmp_path, {"pyproject.toml": "", "src/app.py": ""})
    assert runner.invoke(app, ["audit", str(repo)]).exit_code == 0


def test_outside_git_is_an_error(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("", "utf-8")
    assert runner.invoke(app, ["audit", str(tmp_path)]).exit_code == 2


def test_apply_warns_but_still_writes(tmp_path: Path) -> None:
    repo = _repo(tmp_path, {"pyproject.toml": "", "deploy/id_rsa": ""})
    result = runner.invoke(app, ["apply", str(repo)])
    assert result.exit_code == 0
    assert "1 look like credentials" in result.stderr
    assert (repo / ".gitignore").is_file()


def test_apply_is_quiet_when_nothing_tracked_matches(tmp_path: Path) -> None:
    repo = _repo(tmp_path, {"pyproject.toml": ""})
    result = runner.invoke(app, ["apply", str(repo)])
    assert "warning" not in result.stderr


def test_negated_paths_are_not_findings(tmp_path: Path) -> None:
    repo = _repo(tmp_path, {".env.example": "", ".env.prod.example": "", "x.txt": ""})
    findings = tracked_ignored(repo, ".env.*\n!.env.example\n!.env.*.example\n")
    assert findings == ()


def test_placeholder_env_files_are_not_labelled_secret(tmp_path: Path) -> None:
    # The project's own `.env.*` (after the block) wins over `!.env.example`,
    # so the file is reported, but as a plain tracked file, not a credential.
    repo = _repo(tmp_path, {"pyproject.toml": "", ".env.example": "", ".gitignore": ".env.*\n"})
    result = runner.invoke(app, ["audit", str(repo)])
    assert result.stdout.splitlines() == ["tracked\t.env.example\t.env.*"]
