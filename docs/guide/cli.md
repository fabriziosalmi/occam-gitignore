# CLI

The Typer-based CLI is the most common entry point for local use.

## Install

```bash
uv sync
```

`occam-gitignore` is registered as a workspace script.

## `generate`

```bash
uv run occam-gitignore generate <PATH> [OPTIONS]
```

Walks the given path, fingerprints features, and writes a `.gitignore` to
`<PATH>/.gitignore` (unless `--stdout`).

### Options

| Flag                  | Type   | Default                         | Description                                |
|-----------------------|--------|---------------------------------|--------------------------------------------|
| `--templates DIR`     | path   | `data/templates`                | Directory of `<feature>.gitignore` files   |
| `--rules-table FILE`  | path   | `data/rules_table.json`         | Mined rules table                          |
| `--no-comments`       | flag   | `false`                         | Suppress header and section comments       |
| `--provenance`        | flag   | `false`                         | Append `# <feature>` to each rule          |
| `--extra PATTERN`     | repeat | none                            | Add a user pattern (sorted last)           |
| `--stdout`            | flag   | `false`                         | Print to stdout instead of writing a file  |

### Example

```bash
uv run occam-gitignore generate ./services/api \
  --provenance \
  --extra "secrets/" \
  --extra "*.env.local"
```

## `inspect`

```bash
uv run occam-gitignore inspect <PATH>
```

Prints the fingerprint result without generating a file. Useful when you
want to check what was detected before committing to an output.

## `version`

```bash
uv run occam-gitignore version
```

Prints `core_version` and the loaded `rules_table_version`.

## Exit codes

| Code | Meaning                                  |
|------|------------------------------------------|
| `0`  | Success                                  |
| `1`  | Generic error (I/O, missing template)    |
| `2`  | Argument parsing error (Typer default)   |
