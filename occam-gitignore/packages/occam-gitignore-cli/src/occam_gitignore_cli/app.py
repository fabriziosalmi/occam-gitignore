# SPDX-License-Identifier: MIT
"""Typer application. Keeps wiring (composition root) here, logic in core."""

from __future__ import annotations

import contextlib
import os
import sys
import tempfile
from pathlib import Path

import typer

from occam_gitignore_core import (
    CORE_VERSION,
    DefaultFingerprinter,
    FileSystemTemplateRepository,
    GenerateOptions,
    JsonRulesTable,
    ManagedBlockError,
    apply_managed_block,
    generate,
    missing_patterns,
)

from .paths import data_root, rules_table_path, templates_root
from .scanner import scan_tree

app = typer.Typer(
    name="occam-gitignore",
    help="Deterministic .gitignore generation.",
    no_args_is_help=True,
    add_completion=False,
)

serve_app = typer.Typer(help="Run a server adapter (api / mcp).", no_args_is_help=True)
train_app = typer.Typer(help="Offline training pipelines.", no_args_is_help=True)
bench_app = typer.Typer(help="Reproducible benchmarks.", no_args_is_help=True)
app.add_typer(serve_app, name="serve")
app.add_typer(train_app, name="train")
app.add_typer(bench_app, name="bench")


def _build_pipeline() -> tuple[DefaultFingerprinter, FileSystemTemplateRepository, JsonRulesTable]:
    templates = FileSystemTemplateRepository(templates_root())
    rules = JsonRulesTable.from_file(rules_table_path())
    return DefaultFingerprinter(), templates, rules


def _atomic_write_text(target: Path, content: str) -> None:
    """Write ``content`` to ``target`` atomically (no torn writes on crash)."""
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=str(target.parent),
    )
    tmp_path = Path(tmp)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())
        tmp_path.replace(target)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            tmp_path.unlink()
        raise


@app.command()
def fingerprint(path: Path = typer.Argument(..., exists=True, file_okay=False)) -> None:
    """Print detected features for a repository."""
    fp = DefaultFingerprinter().fingerprint(scan_tree(path))
    for feature in fp.features:
        typer.echo(feature.name)


@app.command()
def generate_(
    path: Path = typer.Argument(..., exists=True, file_okay=False),
    extras: list[str] = typer.Option([], "--extra", "-e", help="Extra patterns."),
    write: bool = typer.Option(False, "--write", help="Write to <path>/.gitignore."),
    explain: bool = typer.Option(False, "--explain", help="Annotate provenance."),
) -> None:
    """Generate a deterministic .gitignore for the given repository."""
    fingerprinter, templates, rules = _build_pipeline()
    fp = fingerprinter.fingerprint(scan_tree(path))
    output = generate(
        fp,
        GenerateOptions(extras=tuple(extras), include_provenance=explain),
        templates=templates,
        rules_table=rules,
    )
    if write:
        target = path / ".gitignore"
        _atomic_write_text(target, output.content)
        typer.echo(
            f"wrote {target} content={output.content_hash} "
            f"provenance={output.provenance_hash}",
            err=True,
        )
    else:
        sys.stdout.write(output.content)


# Typer derives the CLI name from the function; rename the command explicitly.
app.command(name="generate")(generate_)


@app.command()
def diff(path: Path = typer.Argument(..., exists=True, file_okay=False)) -> None:
    """Diff the existing .gitignore vs the generated one."""
    existing = path / ".gitignore"
    fingerprinter, templates, rules = _build_pipeline()
    output = generate(
        fingerprinter.fingerprint(scan_tree(path)),
        GenerateOptions(),
        templates=templates,
        rules_table=rules,
    )
    have = existing.read_text("utf-8") if existing.is_file() else ""
    want_lines = {ln for ln in output.content.splitlines() if ln and not ln.startswith("#")}
    have_lines = {ln.strip() for ln in have.splitlines() if ln.strip() and not ln.startswith("#")}
    missing = sorted(want_lines - have_lines)
    extra = sorted(have_lines - want_lines)
    for line in missing:
        typer.echo(f"+ {line}")
    for line in extra:
        typer.echo(f"- {line}")


@app.command()
def check(
    path: Path = typer.Argument(Path(), exists=True, file_okay=False),
) -> None:
    """Fail if `<path>/.gitignore` is missing any canonical pattern (drift guard).

    Coverage check: every canonical pattern for the detected stack must be
    present. Extra, project-specific lines are allowed and never cause a
    failure. Exit 0 when all canonical patterns are covered; otherwise exit 1
    and list the missing canonical lines on stdout (one per line).
    """
    fingerprinter, templates, rules = _build_pipeline()
    output = generate(
        fingerprinter.fingerprint(scan_tree(path)),
        GenerateOptions(),
        templates=templates,
        rules_table=rules,
    )
    target = path / ".gitignore"
    existing = target.read_text("utf-8") if target.is_file() else ""
    missing = missing_patterns((r.pattern for r in output.rules), existing)
    if not missing:
        typer.echo(
            f"ok: {target} covers all {len(output.rules)} canonical patterns "
            f"({output.content_hash})",
            err=True,
        )
        return
    typer.echo(
        f"drift: {len(missing)} canonical pattern(s) missing from {target}",
        err=True,
    )
    for pattern in missing:
        typer.echo(pattern)
    raise typer.Exit(1)


@app.command()
def apply(
    path: Path = typer.Argument(Path(), exists=True, file_okay=False),
    extras: list[str] = typer.Option([], "--extra", "-e", help="Extra patterns."),
    explain: bool = typer.Option(False, "--explain", help="Annotate provenance."),
) -> None:
    """Merge the canonical output into a managed block in `<path>/.gitignore`.

    Only the delimited occam-gitignore block is written or updated; every line
    outside the block is preserved. Creates the file if absent. Idempotent and
    deterministic: re-running yields byte-identical output.
    """
    fingerprinter, templates, rules = _build_pipeline()
    output = generate(
        fingerprinter.fingerprint(scan_tree(path)),
        GenerateOptions(extras=tuple(extras), include_provenance=explain),
        templates=templates,
        rules_table=rules,
    )
    target = path / ".gitignore"
    existing = target.read_text("utf-8") if target.is_file() else ""
    try:
        merged = apply_managed_block(existing, output.content)
    except ManagedBlockError as exc:
        typer.echo(f"error: {target}: {exc}", err=True)
        raise typer.Exit(2) from exc
    _atomic_write_text(target, merged)
    typer.echo(
        f"wrote managed block in {target} content={output.content_hash} "
        f"provenance={output.provenance_hash}",
        err=True,
    )


@app.command()
def version() -> None:
    """Print versions of core and bundled rules table."""
    rules = JsonRulesTable.from_file(rules_table_path())
    typer.echo(f"core={CORE_VERSION} rules_table={rules.version()}")


@serve_app.command("api")
def serve_api(host: str = "127.0.0.1", port: int = 8080) -> None:
    """Start the HTTP API adapter (occam-gitignore-api)."""
    try:
        from occam_gitignore_api.__main__ import main as api_main  # noqa: PLC0415
    except ImportError as exc:
        typer.echo(f"occam-gitignore-api not installed: {exc}", err=True)
        raise typer.Exit(2) from exc
    raise typer.Exit(
        api_main(
            ["--host", host, "--port", str(port), "--data-dir", str(data_root())],
        ),
    )


@serve_app.command("mcp")
def serve_mcp(
    transport: str = "stdio",
    host: str = "127.0.0.1",
    port: int = 8765,
) -> None:
    """Start the MCP server adapter (occam-gitignore-mcp)."""
    try:
        from occam_gitignore_mcp.__main__ import main as mcp_main  # noqa: PLC0415
    except ImportError as exc:
        typer.echo(f"occam-gitignore-mcp not installed: {exc}", err=True)
        raise typer.Exit(2) from exc
    raise typer.Exit(
        mcp_main(
            [
                "--transport", transport,
                "--host", host,
                "--port", str(port),
                "--data-dir", str(data_root()),
            ],
        ),
    )


@train_app.command(
    "mine",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def train_mine(ctx: typer.Context) -> None:
    """Mine a rules table from JSONL records (delegates to occam-gitignore-train)."""
    try:
        from occam_gitignore_training.__main__ import main as train_main  # noqa: PLC0415
    except ImportError as exc:
        typer.echo(f"occam-gitignore-training not installed: {exc}", err=True)
        raise typer.Exit(2) from exc
    raise typer.Exit(train_main(["mine", *ctx.args]))


@bench_app.command(
    "run",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def bench_run(ctx: typer.Context) -> None:
    """Run reproducible benchmarks (delegates to occam-gitignore-bench)."""
    try:
        from occam_gitignore_bench.__main__ import main as bench_main  # noqa: PLC0415
    except ImportError as exc:
        typer.echo(f"occam-gitignore-bench not installed: {exc}", err=True)
        raise typer.Exit(2) from exc
    raise typer.Exit(bench_main(["run", *ctx.args]))


def _not_implemented(package: str, **ctx: object) -> int:
    typer.echo(f"{package} not yet installed/implemented. ctx={ctx}", err=True)
    return 2
