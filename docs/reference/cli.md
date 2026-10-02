# CLI flags

See also [Guide → CLI](../guide/cli) for tutorial-style usage.

## `occam-gitignore generate`

```
Usage: occam-gitignore generate [OPTIONS] PATH

  Generate a deterministic .gitignore for the given repository.

  Prints to stdout. To update a repository, prefer `apply`: it keeps every
  hand-written line. `--write` replaces the whole file, so it refuses to
  clobber an existing, different `.gitignore` unless `--force` is given.

Options:
  --extra, -e TEXT   Extra pattern (repeatable)
  --write            Write to PATH/.gitignore
  --force            With --write, replace an existing, different .gitignore
  --explain          Append # <feature> to each rule
  --help             Show this message and exit
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

  Merge the canonical output into a delimited "managed block" at the top of
  PATH/.gitignore. Lines outside the block are preserved (merge, not replace)
  and kept below it, so they override it (git: last matching pattern wins).
  An existing block is replaced and moved to the top. Idempotent and
  deterministic.

Options:
  --extra, -e TEXT   User pattern (repeatable)
  --explain          Append # <feature> to each rule
```

## `occam-gitignore audit`

```
Usage: occam-gitignore audit [PATH]

  List tracked files that PATH/.gitignore would ignore after `apply`, one
  per line: `secret|tracked <TAB> path <TAB> rule`. Likely credentials come
  first. Files are never opened; git's own matcher decides.

  Exit 0  — no tracked file is matched.
  Exit 1  — at least one is; the list is on stdout.
  Exit 2  — PATH is not inside a git work tree, or the managed block is malformed.
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
