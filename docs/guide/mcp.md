# MCP server

`occam-gitignore-mcp` exposes the same generator as a
[Model Context Protocol](https://modelcontextprotocol.io/) server. LLM
clients can call it as a tool, without inheriting non-determinism from the
model itself.

## Run

```bash
# stdio (default)
uv run occam-gitignore-mcp

# streamable HTTP
uv run occam-gitignore-mcp --transport streamable-http --host 127.0.0.1 --port 8765

# Server-Sent Events
uv run occam-gitignore-mcp --transport sse --port 8765
```

## Tools

### `occam_gitignore.generate`

```jsonc
{
  "tree": ["pyproject.toml", "Dockerfile"],
  "include_comments": true,
  "include_provenance": false,
  "extras": ["secrets/"]
}
```

Returns the structured `GitignoreOutput` (content + hash + versions +
rules). The LLM never has to invent patterns.

### `occam_gitignore.diff_against`

```jsonc
{ "existing": "*.pyc\n", "tree": ["pyproject.toml"] }
```

Returns `{ "added": [...], "removed": [...] }`.

### `occam_gitignore.inspect`

```jsonc
{ "tree": ["pyproject.toml", "src/main.py"] }
```

Returns the fingerprint result (features + evidence), useful when an LLM
wants to reason about which features were detected before committing to a
generation.

## Why MCP for a deterministic tool?

The MCP adapter exists precisely **because** the rest of the stack is
deterministic. It gives an LLM a way to delegate the part of the task that
should never be guessed (the actual ignore patterns) to a verifiable
function, while keeping the LLM in charge of the parts that legitimately
need judgement (which user extras to add, which paths to scan, how to
explain the result to the user).
