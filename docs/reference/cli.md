# CLI flags

See also [Guide → CLI](../guide/cli) for tutorial-style usage.

## `occam-gitignore generate`

```
Usage: occam-gitignore generate [OPTIONS] PATH

  Generate a deterministic .gitignore for the project at PATH.

Options:
  --templates DIR        Templates directory  [default: data/templates]
  --rules-table FILE     Rules table JSON     [default: data/rules_table.json]
  --no-comments          Suppress header and section comments
  --provenance           Append # <feature> to each rule
  --extra TEXT           User pattern (repeatable)
  --stdout               Print to stdout instead of writing a file
  --help                 Show this message and exit
```

## `occam-gitignore inspect`

```
Usage: occam-gitignore inspect [OPTIONS] PATH

  Print the FingerprintResult for the tree at PATH (no file is written).
```

## `occam-gitignore check`

```
Usage: occam-gitignore check [PATH]

  Coverage drift-guard. Detect the stack, compute the canonical pattern set,
  and verify that PATH/.gitignore CONTAINS every canonical pattern.

  Exit 0  — all canonical patterns are present.
  Exit 1  — one or more are missing; the missing lines are printed to stdout.

  Extra, project-specific lines are always allowed and never cause a failure.
  PATH defaults to the current directory.
```

## `occam-gitignore apply`

```
Usage: occam-gitignore apply [OPTIONS] [PATH]

  Merge the canonical output into a delimited "managed block" in
  PATH/.gitignore. Lines outside the block are preserved (merge, not replace);
  an existing block is replaced in place; if absent, the block is appended.
  Idempotent and deterministic.

Options:
  --extra, -e TEXT   User pattern (repeatable)
  --explain          Append # <feature> to each rule
```

## `occam-gitignore version`

```
Usage: occam-gitignore version

  Print core_version and rules_table_version.
```

## `occam-gitignore-bench run`

See [Benchmark methodology](../guide/benchmark) for full options.

```
Usage: occam-gitignore-bench run [OPTIONS] CORPUS_DIR

Options:
  --templates DIR        Templates directory
  --rules-table FILE     Rules table JSON
  --repeats INT          Repeat each case to measure stability + latency [default: 1]
  --diff                 Print false negatives / false positives per case
  --min-recall FLOAT     Fail with code 2 if macro recall is below this
  --min-precision FLOAT  Fail with code 5 if macro precision is below this
  --min-f1 FLOAT         Fail with code 3 if macro F1 is below this
  --max-p99-ms FLOAT     Fail with code 4 if p99 latency exceeds this
  --json                 Emit JSON instead of text
```
