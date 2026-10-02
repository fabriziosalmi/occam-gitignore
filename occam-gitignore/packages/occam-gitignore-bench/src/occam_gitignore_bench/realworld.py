# SPDX-License-Identifier: MIT
"""Read-only dry run of the real CLI pipeline against real git repositories.

The corpus benchmark (``run``) measures the generator against hand-written
expectations. This module answers a different question: *what would happen to
an actual repository if we ran ``occam-gitignore apply`` on it today?*

Nothing is ever written inside a target repository. For each repo, every
``.gitignore`` file (plus ``.git/info/exclude``) is mirrored into a scratch
git repository and git's own matcher (``git check-ignore --no-index``) decides,
path by path, what is ignored *before* and *after* the change. The mirror is
validated against git's real view of the repo; any divergence fails the run,
because a measurement that does not reproduce reality cannot be trusted.

Gates (exit codes of the ``realworld`` subcommand):

* ``1`` — a repository could not be analysed (crash, git error, bad encoding).
* ``6`` — ``apply`` would *un-ignore* a path that is ignored today.
* ``7`` — a stack was detected only from paths git ignores.
* ``8`` — ``apply`` would ignore a tracked file not in the accepted list.
* ``9`` — the mirror did not reproduce git's real view (harness untrusted).
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass, field
from pathlib import Path

from occam_gitignore_cli.scanner import scan_tree
from occam_gitignore_core import (
    DefaultFingerprinter,
    FileSystemTemplateRepository,
    GenerateOptions,
    JsonRulesTable,
    ManagedBlockError,
    apply_managed_block,
    generate,
    missing_patterns,
)

__all__ = [
    "EXIT_COLLATERAL",
    "EXIT_ERROR",
    "EXIT_MIRROR",
    "EXIT_REEXPOSED",
    "EXIT_SPURIOUS",
    "RepoReport",
    "analyse_repo",
    "discover_repos",
    "gate",
    "load_accepted",
    "run_fleet",
]

EXIT_ERROR = 1
EXIT_REEXPOSED = 6
EXIT_SPURIOUS = 7
EXIT_COLLATERAL = 8
EXIT_MIRROR = 9

# Never take locks or refresh the index of a target repository.
_GIT_ENV = {**os.environ, "GIT_OPTIONAL_LOCKS": "0"}
# Cap on files listed per collapsed ignored directory (e.g. a huge venv).
_EXPAND_CAP = 3000
_GIT_TIMEOUT_S = 300


@dataclass(frozen=True, slots=True)
class RepoReport:
    """Everything the dry run learned about one repository."""

    repo: str
    error: str | None = None
    n_tracked: int = 0
    n_untracked: int = 0
    n_ignored: int = 0
    scan_ms: float = 0.0
    scan_entries: int = 0
    deterministic: bool = True
    features: tuple[str, ...] = ()
    features_visible: tuple[str, ...] = ()
    spurious: tuple[tuple[str, str], ...] = ()
    check_missing: int = 0
    idempotent: bool = True
    mirror_mismatch: tuple[str, ...] = ()
    # (path, "source:line:pattern") — the rule responsible.
    collateral: tuple[tuple[str, str], ...] = ()
    reexposed: tuple[tuple[str, str], ...] = ()
    replace_reexposed: int = 0
    untouched: bool = True
    notes: tuple[str, ...] = field(default=())


# --------------------------------------------------------------------------- #
# git plumbing                                                                 #
# --------------------------------------------------------------------------- #


def _git_list(repo: Path, cmd: str, *args: str) -> list[str]:
    out = subprocess.run(  # noqa: S603 - fixed argv, no shell
        ["git", "-C", str(repo), "-c", "core.quotepath=off", cmd, "-z", *args],  # noqa: S607
        capture_output=True,
        env=_GIT_ENV,
        check=True,
        timeout=_GIT_TIMEOUT_S,
    ).stdout
    return [p for p in out.decode("utf-8", "surrogateescape").split("\0") if p]


def _excludes_file(repo: Path) -> str | None:
    res = subprocess.run(  # noqa: S603
        ["git", "-C", str(repo), "config", "--path", "--get", "core.excludesFile"],  # noqa: S607
        capture_output=True,
        env=_GIT_ENV,
        check=False,
        timeout=_GIT_TIMEOUT_S,
    )
    value = res.stdout.decode("utf-8", "surrogateescape").strip()
    return value or None


def _check_ignored(
    mirror: Path, paths: list[str], excludes_file: str | None,
) -> dict[str, str]:
    """Map each *ignored* path to the rule ignoring it. Absent => not ignored."""
    if not paths:
        return {}
    cfg = ["-c", f"core.excludesFile={excludes_file}"] if excludes_file else []
    res = subprocess.run(  # noqa: S603
        [  # noqa: S607
            "git", "-C", str(mirror), *cfg,
            "check-ignore", "--no-index", "--stdin", "-z", "-v", "-n",
        ],
        input="\0".join(paths).encode("utf-8", "surrogateescape") + b"\0",
        capture_output=True,
        env=_GIT_ENV,
        check=False,
        timeout=_GIT_TIMEOUT_S,
    )
    if res.returncode not in (0, 1):
        raise RuntimeError(res.stderr.decode("utf-8", "replace").strip())
    fields = res.stdout.decode("utf-8", "surrogateescape").split("\0")
    out: dict[str, str] = {}
    # -z -v -n emits 4 fields per path: source, line, pattern, path.
    for i in range(0, len(fields) - 3, 4):
        src, line, pattern, path = fields[i : i + 4]
        if pattern and not pattern.startswith("!"):
            out[path] = f"{src}:{line}:{pattern}"
    return out


def _write_mirror(mirror: Path, files: dict[str, bytes], info_exclude: bytes | None) -> None:
    for rel, content in files.items():
        dst = mirror / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(content)
    if info_exclude is not None:
        (mirror / ".git" / "info").mkdir(parents=True, exist_ok=True)
        (mirror / ".git" / "info" / "exclude").write_bytes(info_exclude)


def _signature(repo: Path) -> tuple[tuple[int, int] | None, ...]:
    """mtime+size of the files a careless run could touch. Proves read-only."""
    out: list[tuple[int, int] | None] = []
    for p in (repo / ".gitignore", repo / ".git" / "index"):
        try:
            st = p.stat()
            out.append((st.st_mtime_ns, st.st_size))
        except FileNotFoundError:
            out.append(None)
    return tuple(out)


def _is_gitignore(rel: str) -> bool:
    return rel == ".gitignore" or rel.endswith("/.gitignore")


# --------------------------------------------------------------------------- #
# analysis                                                                     #
# --------------------------------------------------------------------------- #


def analyse_repo(repo: Path, templates_dir: Path, rules_table: Path, scratch: Path) -> RepoReport:
    """Dry-run ``apply`` on ``repo``. Never writes inside ``repo``."""
    before_sig = _signature(repo)
    try:
        report = _analyse(repo, templates_dir, rules_table, scratch)
    except (OSError, subprocess.SubprocessError, RuntimeError, ManagedBlockError) as exc:
        report = RepoReport(repo=repo.name, error=f"{type(exc).__name__}: {exc}")
    untouched = _signature(repo) == before_sig
    if not untouched:
        return RepoReport(repo=repo.name, error="target repository was modified", untouched=False)
    return report


def _analyse(repo: Path, templates_dir: Path, rules_table: Path, scratch: Path) -> RepoReport:
    templates = FileSystemTemplateRepository(templates_dir)
    rules = JsonRulesTable.from_file(rules_table)
    fingerprinter = DefaultFingerprinter()

    tracked = _git_list(repo, "ls-files")
    untracked = _git_list(repo, "ls-files", "-o", "--exclude-standard")
    ignored = _git_list(repo, "ls-files", "-o", "-i", "--exclude-standard", "--directory")

    t0 = time.perf_counter()
    tree = scan_tree(repo)
    scan_ms = (time.perf_counter() - t0) * 1000.0
    deterministic = scan_tree(repo) == tree

    fp = fingerprinter.fingerprint(tree)
    # What git itself shows: tracked + untracked-not-ignored. A stack whose
    # only evidence lies in ignored paths (a venv, an agent worktree) is spurious.
    fp_visible = fingerprinter.fingerprint(tuple(sorted({*tracked, *untracked})))
    evidence = dict(fp.evidence)
    visible_names = {f.name for f in fp_visible.features}
    spurious = tuple(
        (f.name, evidence[f.name]) for f in fp.features if f.name not in visible_names
    )

    output = generate(fp, GenerateOptions(), templates=templates, rules_table=rules)
    root = repo / ".gitignore"
    existing = root.read_bytes().decode("utf-8") if root.is_file() else ""
    merged = apply_managed_block(existing, output.content)
    idempotent = apply_managed_block(merged, output.content) == merged
    check_missing = len(missing_patterns((r.pattern for r in output.rules), existing))

    gi_files = {
        rel: (repo / rel).read_bytes()
        for rel in {*tracked, *untracked, *ignored}
        if _is_gitignore(rel) and (repo / rel).is_file()
    }
    paths, expanded, before, after_apply, after_replace = _mirror_verdicts(
        repo, scratch, gi_files, (tracked, untracked, ignored), (merged, output.content),
    )

    mismatch = tuple(
        sorted(
            [p for p in expanded if p not in before]
            + [p for p in untracked if p in before],
        ),
    )
    tracked_set = set(tracked)
    collateral = tuple(
        (p, after_apply[p]) for p in paths
        if p in tracked_set and p in after_apply and p not in before
    )
    reexposed = tuple((p, before[p]) for p in paths if p in before and p not in after_apply)
    replace_reexposed = sum(1 for p in paths if p in before and p not in after_replace)

    return RepoReport(
        repo=repo.name,
        n_tracked=len(tracked),
        n_untracked=len(untracked),
        n_ignored=len(expanded),
        scan_ms=round(scan_ms, 3),
        scan_entries=len(tree),
        deterministic=deterministic,
        features=tuple(f.name for f in fp.features),
        features_visible=tuple(sorted(visible_names)),
        spurious=spurious,
        check_missing=check_missing,
        idempotent=idempotent,
        mirror_mismatch=mismatch,
        collateral=collateral,
        reexposed=reexposed,
        replace_reexposed=replace_reexposed,
    )


Verdicts = dict[str, str]


def _mirror_verdicts(
    repo: Path,
    scratch: Path,
    gi_files: dict[str, bytes],
    listing: tuple[list[str], list[str], list[str]],
    candidates: tuple[str, str],
) -> tuple[list[str], list[str], Verdicts, Verdicts, Verdicts]:
    """Judge every path before, after ``apply`` and after a full replace."""
    tracked, untracked, ignored = listing
    merged, replaced = candidates
    info = repo / ".git" / "info" / "exclude"
    info_bytes = info.read_bytes() if info.is_file() else None
    excludes = _excludes_file(repo)
    with tempfile.TemporaryDirectory(dir=scratch) as td:
        mirror = Path(td)
        subprocess.run(  # noqa: S603
            ["git", "init", "-q", str(mirror)],  # noqa: S607
            check=True, env=_GIT_ENV, timeout=_GIT_TIMEOUT_S,
        )
        _write_mirror(mirror, gi_files, info_bytes)
        # `--directory` collapses a dir whose contents are all ignored even when
        # no rule matches the dir itself (e.g. a self-ignoring cache with an
        # inner `*`). Expand those into files so the mirror can judge them.
        probe = _check_ignored(mirror, ignored, excludes)
        expanded: list[str] = []
        for rel in ignored:
            if rel in probe or not rel.endswith("/"):
                expanded.append(rel)
                continue
            inner = _git_list(repo, "ls-files", "-o", "-i", "--exclude-standard", "--", rel)
            inner = inner[:_EXPAND_CAP]
            for f in inner:
                if _is_gitignore(f) and (repo / f).is_file():
                    gi_files[f] = (repo / f).read_bytes()
            expanded.extend(inner)
        _write_mirror(mirror, gi_files, info_bytes)

        paths = sorted({*tracked, *untracked, *expanded})
        before = _check_ignored(mirror, paths, excludes)
        (mirror / ".gitignore").write_text(merged, "utf-8")
        after_apply = _check_ignored(mirror, paths, excludes)
        (mirror / ".gitignore").write_text(replaced, "utf-8")
        after_replace = _check_ignored(mirror, paths, excludes)
    return paths, expanded, before, after_apply, after_replace


# --------------------------------------------------------------------------- #
# fleet + gates                                                                #
# --------------------------------------------------------------------------- #


def discover_repos(base: Path) -> tuple[Path, ...]:
    """Direct children of ``base`` that are git work trees, sorted by name."""
    return tuple(sorted(d for d in base.iterdir() if d.is_dir() and (d / ".git").exists()))


def run_fleet(
    repos: tuple[Path, ...],
    templates_dir: Path,
    rules_table: Path,
    scratch: Path,
    *,
    workers: int = 8,
) -> tuple[RepoReport, ...]:
    scratch.mkdir(parents=True, exist_ok=True)
    with ProcessPoolExecutor(max_workers=max(1, workers)) as ex:
        futures = [
            ex.submit(analyse_repo, r, templates_dir, rules_table, scratch) for r in repos
        ]
        reports = [f.result() for f in futures]
    return tuple(sorted(reports, key=lambda r: r.repo))


def load_accepted(path: Path | None) -> frozenset[tuple[str, str]]:
    """Accepted collateral: ``repo:path`` per line, ``#`` comments allowed.

    Use it for tracked files the canonical rules are *right* to flag (a
    committed key, a vendored ``node_modules``): the repo is wrong, not the
    tool. Keep this file outside the repository.
    """
    if path is None:
        return frozenset()
    out: set[tuple[str, str]] = set()
    for raw in path.read_text("utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        repo, _, rel = line.partition(":")
        out.add((repo, rel))
    return frozenset(out)


def gate(reports: tuple[RepoReport, ...], accepted: frozenset[tuple[str, str]]) -> int:
    """Most severe failing gate's exit code, or 0. Order = severity."""
    checks = (
        (EXIT_ERROR, any(r.error for r in reports)),
        (EXIT_MIRROR, any(r.mirror_mismatch for r in reports)),
        (EXIT_REEXPOSED, any(r.reexposed for r in reports)),
        (EXIT_SPURIOUS, any(r.spurious for r in reports)),
        (
            EXIT_COLLATERAL,
            any((r.repo, p) not in accepted for r in reports for p, _ in r.collateral),
        ),
        (EXIT_ERROR, any(not r.idempotent or not r.deterministic for r in reports)),
    )
    return next((code for code, failed in checks if failed), 0)


def to_json(reports: tuple[RepoReport, ...]) -> str:
    return json.dumps([asdict(r) for r in reports], indent=1, ensure_ascii=False) + "\n"


def to_text(reports: tuple[RepoReport, ...], accepted: frozenset[tuple[str, str]]) -> str:
    ok = [r for r in reports if not r.error]
    lines = [
        f"repos={len(reports)} errors={len(reports) - len(ok)} "
        f"paths={sum(r.n_tracked + r.n_untracked + r.n_ignored for r in ok)}",
        f"mirror mismatches: {sum(1 for r in ok if r.mirror_mismatch)} repos",
        f"apply re-exposes:  {sum(len(r.reexposed) for r in ok)} paths "
        f"in {sum(1 for r in ok if r.reexposed)} repos",
        f"spurious stacks:   {sum(len(r.spurious) for r in ok)} "
        f"in {sum(1 for r in ok if r.spurious)} repos",
    ]
    new_coll = [
        (r.repo, p, src) for r in ok for p, src in r.collateral if (r.repo, p) not in accepted
    ]
    acc_coll = sum(1 for r in ok for p, _ in r.collateral if (r.repo, p) in accepted)
    lines += [
        f"collateral:        {len(new_coll)} unaccepted tracked paths "
        f"in {len({c[0] for c in new_coll})} repos (+{acc_coll} accepted)",
        f"replace (generate > .gitignore) re-exposes: "
        f"{sum(r.replace_reexposed for r in ok)} paths "
        f"in {sum(1 for r in ok if r.replace_reexposed)} repos",
        f"check passes as-is: {sum(1 for r in ok if r.check_missing == 0)} repos",
        f"idempotent: {sum(r.idempotent for r in ok)}/{len(ok)}  "
        f"deterministic scan: {sum(r.deterministic for r in ok)}/{len(ok)}  "
        f"scan max={max((r.scan_ms for r in ok), default=0):.0f}ms",
    ]
    for r in reports:
        if r.error:
            lines.append(f"  ERROR    {r.repo}: {r.error}")
        for p in r.mirror_mismatch[:5]:
            lines.append(f"  MIRROR   {r.repo}: {p}")
        for p, src in r.reexposed:
            lines.append(f"  REEXPOSE {r.repo}: {p}  (was {src})")
        for feat, ev in r.spurious:
            lines.append(f"  SPURIOUS {r.repo}: {feat}  (evidence {ev})")
    lines.extend(f"  COLLAT   {repo}: {p}  ({src})" for repo, p, src in new_coll)
    return "\n".join(lines) + "\n"
