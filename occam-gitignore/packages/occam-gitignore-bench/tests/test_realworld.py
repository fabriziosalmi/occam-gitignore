# SPDX-License-Identifier: MIT
"""The real-world dry run: read-only, faithful to git, and gated."""

from __future__ import annotations

import subprocess
from pathlib import Path  # noqa: TC003 - used at runtime by pytest fixture

import pytest

from occam_gitignore_bench import realworld
from occam_gitignore_bench.__main__ import main


def _git(repo: Path, *args: str) -> None:
    subprocess.run(  # noqa: S603
        ["git", "-C", str(repo), *args], check=True, capture_output=True,  # noqa: S607
    )


def _repo(base: Path, name: str, files: dict[str, str], *, add: tuple[str, ...]) -> Path:
    repo = base / name
    repo.mkdir(parents=True)
    _git(repo, "init", "-q")
    for rel, content in files.items():
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (repo / rel).write_text(content, "utf-8")
    if add:
        _git(repo, "add", "--", *add)
    return repo


def _templates(tmp: Path, **templates: str) -> tuple[Path, Path]:
    tdir = tmp / "templates"
    tdir.mkdir()
    for name, body in templates.items():
        (tdir / f"{name}.gitignore").write_text(body, "utf-8")
    rules = tmp / "rules_table.json"
    rules.write_text('{"version":"t","rules":[]}', "utf-8")
    return tdir, rules


def _analyse(repo: Path, tdir: Path, rules: Path, tmp: Path) -> realworld.RepoReport:
    scratch = tmp / "scratch"
    scratch.mkdir(exist_ok=True)
    return realworld.analyse_repo(repo, tdir, rules, scratch)


def test_never_writes_into_the_target_repo(tmp_path: Path) -> None:
    repo = _repo(
        tmp_path / "fleet", "r",
        {"pyproject.toml": "", ".gitignore": "x\n"},
        add=("pyproject.toml", ".gitignore"),
    )
    tdir, rules = _templates(tmp_path, common="*.tmp\n", python="__pycache__/\n")
    before = (repo / ".gitignore").read_bytes(), (repo / ".git" / "index").read_bytes()
    report = _analyse(repo, tdir, rules, tmp_path)
    assert report.error is None
    assert report.untouched
    assert ((repo / ".gitignore").read_bytes(), (repo / ".git" / "index").read_bytes()) == before


def test_tracked_file_matched_by_new_rule_is_collateral(tmp_path: Path) -> None:
    repo = _repo(
        tmp_path / "fleet", "r",
        {"pyproject.toml": "", "app.py": "", "docs/out.txt": "", "scratch.tmp": ""},
        add=("pyproject.toml", "app.py", "docs/out.txt"),
    )
    tdir, rules = _templates(tmp_path, common="*.tmp\n", python="docs/\n")
    report = _analyse(repo, tdir, rules, tmp_path)
    # `scratch.tmp` becomes ignored too, but it is untracked: hiding junk is the point.
    assert [p for p, _ in report.collateral] == ["docs/out.txt"]
    assert report.collateral[0][1].endswith(":docs/")


def test_own_ignore_in_gitignore_survives_a_canonical_negation(tmp_path: Path) -> None:
    repo = _repo(
        tmp_path / "fleet", "r",
        {"pyproject.toml": "", ".gitignore": "*.env\n", "keep.env": "SECRET=1\n"},
        add=("pyproject.toml", ".gitignore"),
    )
    tdir, rules = _templates(tmp_path, common="*.env\n!keep.env\n", python="")
    report = _analyse(repo, tdir, rules, tmp_path)
    assert report.reexposed == ()


def test_negation_that_unignores_an_info_exclude_entry_is_reexposed(tmp_path: Path) -> None:
    # .git/info/exclude ranks below any .gitignore, so a canonical `!keep.env`
    # still beats it. The harness must see that.
    repo = _repo(
        tmp_path / "fleet", "r",
        {"pyproject.toml": "", "keep.env": "SECRET=1\n"},
        add=("pyproject.toml",),
    )
    (repo / ".git" / "info" / "exclude").write_text("*.env\n", "utf-8")
    tdir, rules = _templates(tmp_path, common="*.env\n!keep.env\n", python="")
    report = _analyse(repo, tdir, rules, tmp_path)
    assert [p for p, _ in report.reexposed] == ["keep.env"]
    assert realworld.gate((report,), frozenset()) == realworld.EXIT_REEXPOSED


def test_replace_mode_counts_paths_it_would_unignore(tmp_path: Path) -> None:
    repo = _repo(
        tmp_path / "fleet", "r",
        {"pyproject.toml": "", ".gitignore": "private/\n", "private/a.txt": ""},
        add=("pyproject.toml", ".gitignore"),
    )
    tdir, rules = _templates(tmp_path, common="*.tmp\n", python="")
    report = _analyse(repo, tdir, rules, tmp_path)
    assert report.reexposed == ()  # apply keeps the user's lines
    assert report.replace_reexposed == 1  # generate > .gitignore would drop them


def test_mirror_reproduces_self_ignoring_dirs(tmp_path: Path) -> None:
    repo = _repo(
        tmp_path / "fleet", "r",
        {
            "pyproject.toml": "",
            ".cache/.gitignore": "*\n",
            ".cache/blob": "",
            ".gitignore": "data/*.db\n",
            "data/x.db": "",
        },
        add=("pyproject.toml", ".gitignore"),
    )
    tdir, rules = _templates(tmp_path, common="*.tmp\n", python="")
    report = _analyse(repo, tdir, rules, tmp_path)
    assert report.error is None
    assert report.mirror_mismatch == ()


def test_untracked_visible_file_is_legitimate_evidence(tmp_path: Path) -> None:
    repo = _repo(
        tmp_path / "fleet", "r",
        {"pyproject.toml": "", "new_tool.go": ""},
        add=("pyproject.toml",),
    )
    tdir, rules = _templates(tmp_path, common="*.tmp\n", python="", go="*.test\n")
    report = _analyse(repo, tdir, rules, tmp_path)
    assert "go" in report.features
    assert report.spurious == ()


def test_evidence_found_only_in_ignored_paths_is_spurious(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Simulate a scanner that walks the disk and ignores git's ignore rules.
    monkeypatch.setattr(
        realworld, "scan_tree", lambda root: tuple(sorted(
            p.relative_to(root).as_posix() for p in root.rglob("*")
            if p.is_file() and ".git" not in p.relative_to(root).parts
        )),
    )
    repo = _repo(
        tmp_path / "fleet", "r",
        {"pyproject.toml": "", ".gitignore": ".venv-x/\n", ".venv-x/pip/worker.go": ""},
        add=("pyproject.toml", ".gitignore"),
    )
    tdir, rules = _templates(tmp_path, common="*.tmp\n", python="", go="*.test\n")
    report = _analyse(repo, tdir, rules, tmp_path)
    assert report.spurious == (("go", ".venv-x/pip/worker.go"),)
    assert realworld.gate((report,), frozenset()) == realworld.EXIT_SPURIOUS


def test_accepted_collateral_passes_the_gate(tmp_path: Path) -> None:
    report = realworld.RepoReport(repo="r", collateral=(("key.pem", ".gitignore:9:*.pem"),))
    assert realworld.gate((report,), frozenset()) == realworld.EXIT_COLLATERAL
    accepted_file = tmp_path / "accepted.txt"
    accepted_file.write_text("# committed by mistake\nr:key.pem\n", "utf-8")
    assert realworld.gate((report,), realworld.load_accepted(accepted_file)) == 0


@pytest.mark.parametrize(
    ("report", "code"),
    [
        (realworld.RepoReport(repo="r", error="boom"), realworld.EXIT_ERROR),
        (realworld.RepoReport(repo="r", mirror_mismatch=("x",)), realworld.EXIT_MIRROR),
        (realworld.RepoReport(repo="r", idempotent=False), realworld.EXIT_ERROR),
        (realworld.RepoReport(repo="r"), 0),
    ],
)
def test_gate_codes(report: realworld.RepoReport, code: int) -> None:
    assert realworld.gate((report,), frozenset()) == code


def test_cli_end_to_end(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    fleet = tmp_path / "fleet"
    _repo(fleet, "clean", {"pyproject.toml": ""}, add=("pyproject.toml",))
    (fleet / "not-a-repo").mkdir()
    tdir, rules = _templates(tmp_path, common="*.tmp\n", python="")
    out = tmp_path / "report.json"
    rc = main([
        "realworld", str(fleet), "--templates", str(tdir), "--rules-table", str(rules),
        "--out", str(out), "--workers", "1",
    ])
    assert rc == 0
    assert "repos=1 errors=0" in capsys.readouterr().out
    assert '"repo": "clean"' in out.read_text("utf-8")
    assert main([
        "realworld", str(fleet), "--templates", str(tdir), "--rules-table", str(rules),
        "--repo", "nope",
    ]) == 2
