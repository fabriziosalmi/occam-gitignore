# Architecture

`occam-gitignore` is a hexagonal monorepo: one **pure core** plus thin
**adapters**. Adapters depend on the core. The core depends on nothing.

```
┌─────────────────────────────────────────────────────────────┐
│                     occam-gitignore-core                    │
│                                                             │
│   generate(fingerprint, options, *, templates, rules_table) │
│        ↓ pure, deterministic, hash-verifiable               │
│        GitignoreOutput                                      │
└─────────────────────────────────────────────────────────────┘
            ▲              ▲              ▲             ▲
            │              │              │             │
        ┌───┴────┐   ┌─────┴────┐   ┌─────┴─────┐  ┌────┴─────┐
        │  CLI   │   │   API    │   │    MCP    │  │  Bench   │
        │ Typer  │   │ FastAPI  │   │  FastMCP  │  │ harness  │
        └────────┘   └──────────┘   └───────────┘  └──────────┘
```

The training package `occam-gitignore-training` is offline-only: it consumes
JSONL records and produces a `rules_table.json` used by the core at runtime.

## Packages

| Package | Role | Dependencies |
|---|---|---|
| `occam-gitignore-core`     | Pure generator, schema, ports, default fingerprinter | _none_ |
| `occam-gitignore-cli`      | Typer entry point | core, typer |
| `occam-gitignore-api`      | FastAPI HTTP service | core, fastapi |
| `occam-gitignore-mcp`      | MCP server (stdio, SSE, streamable-http) | core, mcp |
| `occam-gitignore-training` | Offline mining (lift, support, pair detection) | core |
| `occam-gitignore-bench`    | Recall/precision/F1/stability/latency harness | core |

## Ports

Two protocols define everything the core needs:

```python
class TemplateRepository(Protocol):
    def get(self, feature: Feature) -> tuple[Rule, ...]: ...
    def features(self) -> tuple[Feature, ...]: ...
    def version(self) -> str: ...

class RulesTable(Protocol):
    def extras_for(self, features: frozenset[Feature]) -> tuple[Rule, ...]: ...
    def version(self) -> str: ...
```

The core ships two adapters for each: `FileSystemTemplateRepository` /
`InMemoryTemplateRepository`, and `JsonRulesTable` / `InMemoryRulesTable`.

## Generation pipeline

1. **Fingerprint** the input tree. The default detector recognises 11
   features: `python`, `node`, `go`, `rust`, `docker`, `terraform`,
   `jupyter`, `java`, `ruby`, `csharp`, `swift`. Detection is pure (path
   matching only).
2. **Inject implicit features.** When any feature matches and the template
   repository provides a `common` feature, OS/IDE patterns are added.
3. **Collect rules** from templates, then from the rules table, then from
   user extras, in that fixed precedence order.
4. **Stable dedupe.** The first occurrence wins (preserves provenance from
   the highest-priority source). Output sorted by `(source, pattern)`.
5. **Render.** Optional header, optional section comments, optional
   provenance suffix per rule. Output finalised with a trailing newline.
6. **Hash.** `sha256(content)` is computed and returned in `output_hash`.

The whole pipeline is one pure function: no I/O, no clock, no allocations
that depend on PYTHONHASHSEED.
