# Changelog

All notable changes to `occam-gitignore` are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/) and the project adheres to
[Semantic Versioning](https://semver.org/).

## [0.2.0] — 2026-07-19

### Security
- **`.env` and secret patterns are now emitted for every ecosystem**, not just
  Python. Previously the `.env` rule was attached to the Python feature (via the
  mined rules table), so a Rust/Go/Node repository with no Python generated a
  `.gitignore` with **no `.env` line** — applying it could silently commit
  secrets. `.env`, `.env.*` and `!.env.example` now live in the `common`
  template, which is part of every non-empty fingerprint.
- Added common secret patterns to the `common` template: `*.pem`, `*.key`,
  `*.p12`, `*.pfx`, `*.keystore`, `id_rsa`, `id_ed25519`. Public keys such as
  `id_rsa.pub` remain trackable.

### Added
- `ml` ecosystem, detected conservatively from the presence of model weight
  files (`*.pt`, `*.onnx`, `*.gguf`, `*.safetensors`). Ignores model artifacts
  and caches: `*.onnx`, `*.pt`, `*.pth`, `*.gguf`, `*.safetensors`, `*.ckpt`,
  `.fastembed_cache/`. Detection is a pure function of the path list and never
  reads file contents, so dependency-based signals (e.g. `torch` in
  `requirements.txt`) are intentionally out of scope.
- Python template: `.Python` and `.dmypy.json`.

### Fixed
- Negation patterns (`!…`) are now rendered **after** the positive patterns in
  their section, so git's "last matching pattern wins" makes them effective.
  Alphabetical sorting previously placed `!` (0x21) before `.`/`*`, silently
  neutering every negation (e.g. `!gradle/wrapper/gradle-wrapper.jar` was
  overridden by `*.jar`). This also makes the new `!.env.example` re-include work.

### Changed
- The shipped `data/rules_table.json` is now empty. Its only non-redundant entry
  was the Python `.env` rule (now in `common`); every other pattern was already
  provided by the `common` template and deduplicated away. The training/mining
  pipeline and the rules-table mechanism are unchanged.
- Because the rules table, templates and core version all changed, every
  output's provenance line and content hash change. This is expected and
  deterministic: the 5 snapshots and the 34-case conformance suite were
  regenerated, and generating the same repository twice is still byte-identical.
- Bumped `occam-gitignore` and `occam-gitignore-core` from 0.1.3 to 0.2.0.

## [0.1.3] — 2026-04-27

### Fixed
- `occam-gitignore serve api` and `occam-gitignore serve mcp` now auto-resolve
  the bundled data directory and pass it through to the adapter, so a fresh
  `pip install occam-gitignore` works out-of-the-box for both servers (no more
  manual `OCCAM_GITIGNORE_DATA_DIR=...`).

### Changed
- All Python sources now carry an `SPDX-License-Identifier: MIT` header.

## [0.1.2] — 2026-04-27

### Fixed
- Published CLI wheel now bundles `data/templates/` and `data/rules_table.json`
  (previous wheels were broken: `occam-gitignore generate .` raised
  `FileNotFoundError`). A hatch build hook copies the data into the package
  source tree at build time; runtime resolution falls back to the bundled
  `_data/` directory before walking the monorepo layout.

## [0.1.0] — 2026-04-27

### Added
- Initial public release.
- `occam-gitignore-core`: deterministic generator (frozen merkle of
  rules table + templates + core version).
- `occam-gitignore` CLI (`generate`, `fingerprint`, `diff`, `version`,
  `serve api|mcp`).
- `occam-gitignore-api`: FastAPI HTTP adapter, hash-in-header.
- `occam-gitignore-mcp`: Model Context Protocol server (FastMCP).
- `occam-gitignore-bench`: corpus benchmark with quality + latency gates.
- `occam-gitignore-training`: offline pipeline to mine rules from JSONL.
- 32-case conformance suite with locked output hashes.
- 5 snapshot tests + property-based tests (Hypothesis).
- PyPI publishing via OIDC trusted publisher.
- SBOM (SPDX) + SLSA build provenance attestations on every release.
- Composite GitHub Action (`uses: fabriziosalmi/gitignore@v0.1.x`) for
  drift check / auto-fix in CI.

[0.2.0]: https://github.com/fabriziosalmi/gitignore/releases/tag/v0.2.0
[0.1.3]: https://github.com/fabriziosalmi/gitignore/releases/tag/v0.1.3
[0.1.2]: https://github.com/fabriziosalmi/gitignore/releases/tag/v0.1.2
[0.1.0]: https://github.com/fabriziosalmi/gitignore/releases/tag/v0.1.0
