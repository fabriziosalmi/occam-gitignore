# MCP tools

See also [Guide → MCP server](../guide/mcp).

The MCP adapter exposes three tools, all of which delegate to
`occam_gitignore_core.generate(...)` (or its fingerprint helper). They are
pure projections of the core; no LLM is involved on the server side.

## `occam_gitignore.generate`

### Input schema

```json
{
  "type": "object",
  "properties": {
    "tree":               { "type": "array", "items": { "type": "string" } },
    "features":           { "type": "array", "items": { "type": "string" } },
    "include_comments":   { "type": "boolean", "default": true },
    "include_provenance": { "type": "boolean", "default": false },
    "extras":             { "type": "array", "items": { "type": "string" } }
  }
}
```

### Output

The structured payload mirrors the HTTP `POST /generate` response.

## `occam_gitignore.diff_against`

### Input

```json
{
  "existing": "string",
  "tree":     ["string", "..."]
}
```

### Output

```json
{ "added": ["..."], "removed": ["..."] }
```

## `occam_gitignore.inspect`

### Input

```json
{ "tree": ["pyproject.toml", "src/main.py"] }
```

### Output

```json
{
  "features": ["python"],
  "evidence": [["python", "pyproject.toml"]]
}
```

## Transports

| Transport            | Flag                                     | Use case                       |
|----------------------|------------------------------------------|--------------------------------|
| `stdio` (default)    | `occam-gitignore-mcp`                    | Local LLM clients (Claude, etc.) |
| `streamable-http`    | `--transport streamable-http --port N`   | Remote, long-lived sessions    |
| `sse`                | `--transport sse --port N`               | Browser-side clients            |
