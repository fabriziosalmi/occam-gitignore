# occam-gitignore

> Generate the canonical `.gitignore` for any repo — **deterministic**, **fast**, **hash-verifiable**.

[![PyPI](https://img.shields.io/pypi/v/occam-gitignore.svg)](https://pypi.org/project/occam-gitignore/)
[![CI](https://github.com/fabriziosalmi/gitignore/actions/workflows/ci.yml/badge.svg)](https://github.com/fabriziosalmi/gitignore/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Same files in your repo → same `.gitignore`, byte-for-byte, every time. No randomness, no LLM, no
network. The output carries a `sha256` hash so you can verify it in CI.

---

## Why?

Every project ends up with a hand-rolled `.gitignore` that is:

- **Drifting**: someone adds `node_modules/`, someone else adds `.venv/`, nobody removes the dead lines.
- **Inconsistent across repos**: 50 repos in your org, 50 different flavors.
- **Unreviewable**: you can't tell whether a change is "the right one" or just noise.

`occam-gitignore` fixes all three: one tool, one deterministic output, one hash to verify.

---

## Install (30 seconds)

You need Python 3.11 or newer.

### Option A — pip (works everywhere)

```bash
pip install occam-gitignore
```

### Option B — pipx / uv (recommended, isolated)

```bash
pipx install occam-gitignore
# or
uv tool install occam-gitignore
```

Verify the install:

```bash
occam-gitignore version
# core=0.1.3 rules_table=sha256:72fd0c323cc1
```

---

## Quick start: generate a `.gitignore` for your project

From inside any repo:

```bash
cd /path/to/your/repo
occam-gitignore generate . > .gitignore
```

That's it. The tool looked at your files, decided which ecosystems you use (Python? Node? Docker?
Rust? …), and wrote the right `.gitignore`.

### See what it detected

```bash
occam-gitignore fingerprint .
# python (evidence: pyproject.toml)
# docker (evidence: Dockerfile)
# common (evidence: implicit)
```

### See the diff against your current `.gitignore`

```bash
occam-gitignore diff .
```

If the output is empty, your `.gitignore` is up to date. If not, you can review the proposed
changes and apply them.

### Guard against drift (`check`)

`check` is a **coverage guard**: it succeeds when every canonical pattern is present and fails
(exit code 1), listing the missing lines, when one is not. Extra project-specific lines are
allowed — great for CI and pre-commit hooks.

```bash
occam-gitignore check .
# exit 0: nothing missing
# exit 1: prints the canonical patterns your .gitignore is missing (e.g. .env)
```

### Merge without clobbering (`apply`)

`apply` writes the canonical rules into a single delimited **managed block** and leaves every
line outside it untouched. It is idempotent and deterministic, so it is safe to re-run and to
commit:

```bash
occam-gitignore apply .
```

```gitignore
# your hand-written rules stay here, untouched
/local-secrets/

# >>> occam-gitignore >>>
# managed by occam-gitignore — do not edit inside this block
# ...canonical, deterministic output...
# <<< occam-gitignore <<<
```

---

## Use it in CI (GitHub Action)

Drop this in `.github/workflows/gitignore.yml` and your `.gitignore` will be checked on every PR:

```yaml
name: gitignore drift check
on: [pull_request, push]

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: fabriziosalmi/occam-gitignore@v0.3.0
        with:
          path: '.'
          mode: 'check'   # fail the build if a canonical pattern is missing
```

The check is a **coverage guard**: it fails only when your `.gitignore` is *missing* a
canonical pattern (e.g. `.env` slipped out). Extra, project-specific lines you added by hand
are always allowed. To **auto-fix**, use `mode: 'fix'` — it merges the canonical rules into a
delimited managed block and leaves your custom lines untouched — then commit the result with
one of the common "auto-commit" actions.

| Input            | Default          | Description                                  |
| ---------------- | ---------------- | -------------------------------------------- |
| `path`           | `.`              | Repo path to scan.                           |
| `mode`           | `check`          | `check` fails on missing canonical patterns; `fix` merges the managed block. |
| `python-version` | `3.12`           | Python used to install the CLI.              |
| `version`        | `>=0.3.0,<0.4`   | PEP 440 spec for the CLI package.            |

| Output         | Description                                          |
| -------------- | ---------------------------------------------------- |
| `drift`        | `true` if your file is missing any canonical pattern. |
| `output-hash`  | `sha256:<digest>` of the generated content.          |

---

## Use it as an API (HTTP)

Run the HTTP adapter locally:

```bash
occam-gitignore serve api --port 8080
```

Then:

```bash
# Detect features
curl -s -X POST http://127.0.0.1:8080/v1/occam-gitignore/fingerprint \
  -H 'Content-Type: application/json' \
  -d '{"tree": ["pyproject.toml", "Dockerfile"]}'

# Generate
curl -s -X POST http://127.0.0.1:8080/v1/occam-gitignore/generate \
  -H 'Content-Type: application/json' \
  -d '{"tree": ["pyproject.toml"], "include_provenance": true}'
```

Every response carries verification headers:

```
x-occam-gitignore-hash: sha256:<digest of content>
x-occam-gitignore-rules-version: sha256:<rules table version>
x-occam-gitignore-templates-version: sha256:<templates version>
```

Endpoints:

| Method | Path                                      | Purpose                                    |
| ------ | ----------------------------------------- | ------------------------------------------ |
| GET    | `/healthz`                                | Liveness probe.                            |
| GET    | `/v1/occam-gitignore/version`             | Versions of core / rules / templates.      |
| POST   | `/v1/occam-gitignore/fingerprint`         | `tree[]` → detected features + evidence.   |
| POST   | `/v1/occam-gitignore/generate`            | `tree[]` or `features[]` → `.gitignore`.   |

---

## Use it from an LLM (MCP server)

`occam-gitignore` ships an [MCP](https://modelcontextprotocol.io) server so any MCP-aware
assistant (Claude Desktop, Cursor, Continue, …) can call it as a tool.

### Run it

```bash
# stdio transport (default — used by Claude Desktop, Cursor, ...)
occam-gitignore serve mcp

# streamable HTTP transport
occam-gitignore serve mcp --transport streamable-http --port 8765
```

### Hook it into Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "occam-gitignore": {
      "command": "occam-gitignore",
      "args": ["serve", "mcp"]
    }
  }
}
```

Then in chat: *"Use occam-gitignore to generate a .gitignore for this repo."*
The model will call `fingerprint_repo`, then `generate`, and paste the result.

### Tools exposed

| Tool                                | Purpose                                       |
| ----------------------------------- | --------------------------------------------- |
| `occam_gitignore.fingerprint_repo`  | `tree[]` → features + evidence.               |
| `occam_gitignore.generate`          | `tree[]` or `features[]` → text + hash.       |
| `occam_gitignore.diff_against`      | Compare an existing `.gitignore` to canonical.|

---

## What does "deterministic" actually mean?

Three guarantees:

1. **Same inputs → same bytes.** Same file list and same version pins ⇒ identical output, every
   time, on every machine.
2. **Hash-verified.** Every output is content-addressed by `sha256(content)`. The CI Action and
   the API both expose this hash.
3. **Versioned data.** The rules table and templates have their own `sha256` versions. If they
   change, the output hash changes — there are no silent updates.

This means you can:

- Pin a version in CI and treat any drift as a bug.
- Cache outputs by hash without ever invalidating incorrectly.
- Audit *why* a line is in your `.gitignore` (every line carries an inline `# feature` comment when
  comments are enabled).

---

## Supported ecosystems (today)

`common`, `python`, `node`, `go`, `rust`, `java`, `csharp`, `ruby`, `swift`, `docker`,
`terraform`, `jupyter`. The fingerprinter looks at sentinel files (`pyproject.toml`,
`package.json`, `Cargo.toml`, `pom.xml`, `Dockerfile`, …) plus a small set of "implicit" rules
(macOS `.DS_Store`, editor swap files, etc.).

Adding a new ecosystem = a `.gitignore` template + a fingerprint rule + a snapshot test. PRs
welcome.

---

## Architecture (for the curious)

```
core         — pure deterministic generator (no I/O beyond what the adapters give it)
cli          — Typer CLI; ships templates + rules table inside the wheel
api          — FastAPI HTTP adapter
mcp          — Model Context Protocol server (FastMCP)
bench        — corpus-based quality + latency benchmark with gates
training     — offline pipeline to mine new rules from JSONL of real repos
```

Determinism is enforced by:

- A canonical sort + dedupe pass on every output.
- A frozen, content-addressed rules table and templates directory.
- A 32-case [conformance suite](occam-gitignore/conformance/README.md) with locked output hashes.
- 5 snapshot tests that fail loudly on any drift.
- Property-based tests (Hypothesis) for idempotence, determinism, and merge associativity.

Full developer docs: <https://fabriziosalmi.github.io/gitignore/>

---

## FAQ

**Q: Will it overwrite my hand-written `.gitignore`?**
Only if you tell it to. `occam-gitignore generate .` writes to stdout. The Action with
`mode: check` only fails the build; `mode: fix` rewrites the file in place.

**Q: Can I add custom rules?**
Yes. Append your project-specific lines below the generated block, or pass them as `extras` via
the API/MCP. The deterministic block is regenerated; your tail is preserved by convention (keep
your local rules below the last generated line).

**Q: Does it call out to any service?**
No. It's a pure local tool. The HTTP adapter is something *you* run; it never calls anywhere.

**Q: What about `.dockerignore`, `.npmignore`, …?**
Not yet. The architecture is general enough; if you need them, open an issue.

---

## Contributing

```bash
git clone https://github.com/fabriziosalmi/gitignore
cd gitignore/occam-gitignore
uv sync
uv run pytest
uv run ruff check .
uv run mypy .
```

The project is a uv workspace with 6 packages. See
[occam-gitignore/README.md](occam-gitignore/README.md) for the developer-facing details.

---

## License

MIT — see [LICENSE](LICENSE).
