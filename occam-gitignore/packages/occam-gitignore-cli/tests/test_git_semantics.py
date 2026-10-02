# SPDX-License-Identifier: MIT
"""The generated rules mean, *to git*, what they are meant to mean.

Text-level tests cannot catch a negation that git silently ignores (e.g. a
re-include under an excluded directory). Here git itself is the judge.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from occam_gitignore_cli.app import app

_DATA = Path(__file__).resolve().parents[3] / "data"

runner = CliRunner()


@pytest.fixture(autouse=True)
def _use_workspace_data(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OCCAM_GITIGNORE_DATA_DIR", str(_DATA))


def _ignored(repo: Path, paths: list[str]) -> set[str]:
    res = subprocess.run(  # noqa: S603
        [  # noqa: S607
            "git", "-C", str(repo), "-c", "core.excludesFile=/dev/null",
            "check-ignore", "--no-index", "--stdin",
        ],
        input="\n".join(paths) + "\n",
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode in (0, 1), res.stderr
    return set(res.stdout.split())


def _applied(tmp_path: Path, *markers: str, own: str = "") -> Path:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)  # noqa: S603, S607
    for m in markers:
        (tmp_path / m).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / m).write_text("", "utf-8")
    if own:
        (tmp_path / ".gitignore").write_text(own, "utf-8")
    assert runner.invoke(app, ["apply", str(tmp_path)]).exit_code == 0
    return tmp_path


@pytest.mark.parametrize(
    ("markers", "ignored", "kept"),
    [
        (
            ("pyproject.toml",),
            [".env", ".env.local", ".env.production", "id_rsa", "server.key",
             ".vscode/settings.local.json", ".vscode/.history/x"],
            [".env.example", ".env.prod.example", ".env.local.example", ".env.sample",
             ".env.template", ".vscode/settings.json", ".vscode/tasks.json",
             ".vscode/launch.json", ".vscode/extensions.json", ".vscode/py.code-snippets",
             "id_rsa.pub"],
        ),
        (("Cargo.toml",), ["target/debug/app"], ["Cargo.lock"]),
        (
            ("Package.swift",),
            [".build/x", "App.xcodeproj/xcuserdata/me.xcuserdatad/x"],
            ["App.xcodeproj/project.pbxproj", "Package.resolved"],
        ),
        (("go.mod",), ["app.test"], ["vendor/github.com/x/y.go"]),
        (("package.json",), ["node_modules/x/i.js", "dist/i.js"], ["logs/run.json", "out/x.js"]),
        (("App.csproj",), ["bin/x.dll"], [".vscode/settings.json"]),
    ],
)
def test_canonical_rules_as_git_sees_them(
    tmp_path: Path, markers: tuple[str, ...], ignored: list[str], kept: list[str],
) -> None:
    repo = _applied(tmp_path, *markers)
    verdict = _ignored(repo, ignored + kept)
    assert sorted(set(ignored) - verdict) == []  # must be ignored
    assert sorted(verdict & set(kept)) == []  # must stay visible


def test_own_lines_override_the_managed_block(tmp_path: Path) -> None:
    # The project ignores .env.example and wants Cargo.lock out; the block's
    # re-include of .env.example must not win.
    repo = _applied(tmp_path, "Cargo.toml", own=".env.example\nCargo.lock\n")
    assert _ignored(repo, [".env.example", "Cargo.lock"]) == {".env.example", "Cargo.lock"}
