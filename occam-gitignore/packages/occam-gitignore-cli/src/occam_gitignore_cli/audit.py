# SPDX-License-Identifier: MIT
"""Which *tracked* files would a `.gitignore` ignore? git decides.

A `.gitignore` never untracks anything, so a rule matching a committed file
is silent: the file stays in the repo, while new files like it are quietly
skipped by `git add`. Either the rule is wrong for this project, or the file
should never have been committed (a key, a `.env`, a vendored dependency).
This module surfaces both, without ever opening the files.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

__all__ = ["SECRET_PATTERNS", "Finding", "tracked_ignored"]

# Patterns of the `common` template's secrets section. A tracked file matched
# by one of these is a credential that is already in the history.
SECRET_PATTERNS = frozenset({
    ".env", ".env.*", "*.pem", "*.key", "*.p12", "*.pfx", "*.keystore",
    "id_rsa", "id_ed25519",
})

# Conventional names for credential-free templates of a secrets file.
_PLACEHOLDERS = (".example", ".sample", ".template")

_GIT_TIMEOUT_S = 120
_ENV = {**os.environ, "GIT_OPTIONAL_LOCKS": "0"}


@dataclass(frozen=True, slots=True)
class Finding:
    path: str
    pattern: str
    line: int

    @property
    def secret(self) -> bool:
        # `.env.example` ignored by a project's own `.env.*` is not a credential.
        return self.pattern in SECRET_PATTERNS and not self.path.endswith(_PLACEHOLDERS)


def tracked_ignored(root: Path, gitignore: str) -> tuple[Finding, ...] | None:
    """Tracked files under ``root`` that ``gitignore`` (placed at ``root``) ignores.

    Only ``gitignore`` is consulted, judged by git's own matcher on a scratch
    repository, so negations and directory rules mean exactly what git makes
    of them. Returns ``None`` when ``root`` is not inside a git work tree.
    """
    tracked = _run(["git", "-C", str(root), "-c", "core.quotepath=off", "ls-files", "-z"])
    if tracked is None:
        return None
    paths = [p for p in tracked.decode("utf-8", "surrogateescape").split("\0") if p]
    if not paths:
        return ()
    with tempfile.TemporaryDirectory(prefix="occam-audit-") as td:
        scratch = Path(td)
        if _run(["git", "init", "-q", str(scratch)]) is None:
            return None
        (scratch / ".gitignore").write_text(gitignore, "utf-8")
        out = _run(
            [
                "git", "-C", str(scratch), "-c", "core.excludesFile=/dev/null",
                "check-ignore", "--no-index", "--stdin", "-z", "-v", "-n",
            ],
            stdin="\0".join(paths).encode("utf-8", "surrogateescape") + b"\0",
            ok=(0, 1),
        )
    if out is None:
        return None
    fields = out.decode("utf-8", "surrogateescape").split("\0")
    found: list[Finding] = []
    # -z -v -n: source, line, pattern, path per entry; empty pattern = no match.
    for i in range(0, len(fields) - 3, 4):
        _src, line, pattern, path = fields[i : i + 4]
        if pattern and not pattern.startswith("!"):
            found.append(Finding(path=path, pattern=pattern, line=int(line)))
    return tuple(sorted(found, key=lambda f: (not f.secret, f.path)))


def _run(
    argv: list[str], *, stdin: bytes | None = None, ok: tuple[int, ...] = (0,),
) -> bytes | None:
    try:
        res = subprocess.run(  # noqa: S603 - fixed argv, no shell
            argv, input=stdin, capture_output=True, env=_ENV,
            check=False, timeout=_GIT_TIMEOUT_S,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return res.stdout if res.returncode in ok else None
