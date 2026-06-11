# SPDX-License-Identifier: MIT
"""Immutable value objects. Make illegal states unrepresentable."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

__all__ = [
    "Feature",
    "FingerprintResult",
    "GenerateOptions",
    "GitignoreOutput",
    "Rule",
    "RuleSource",
]

_VALID_NAME_CHARS = frozenset("abcdefghijklmnopqrstuvwxyz0123456789-_")


class RuleSource(StrEnum):
    """Provenance of a rule. Drives stable section ordering in the output."""

    TEMPLATE = "template"
    MINED = "mined"
    USER_EXTRA = "user_extra"


@dataclass(frozen=True, slots=True, order=True)
class Feature:
    """A canonical feature name (e.g. 'python', 'docker'). Lowercase, slug-like."""

    name: str

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("feature name must be non-empty")
        if self.name != self.name.lower():
            raise ValueError(f"feature name must be lowercase: {self.name!r}")
        if not set(self.name).issubset(_VALID_NAME_CHARS):
            raise ValueError(f"invalid feature name: {self.name!r}")


@dataclass(frozen=True, slots=True, order=True)
class Rule:
    """A single line in a `.gitignore`, with provenance."""

    pattern: str
    source: RuleSource
    feature: str | None = None
    comment: str | None = None

    def __post_init__(self) -> None:
        if not self.pattern or self.pattern != self.pattern.strip():
            raise ValueError(f"invalid rule pattern: {self.pattern!r}")
        if "\n" in self.pattern:
            raise ValueError("rule pattern must be a single line")


@dataclass(frozen=True, slots=True)
class FingerprintResult:
    """Output of a `Fingerprinter`. Features are sorted; evidence is sorted."""

    features: tuple[Feature, ...]
    evidence: tuple[tuple[str, str], ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class GenerateOptions:
    """Knobs for `generate`. All defaults are deterministic-friendly."""

    extras: tuple[str, ...] = ()
    include_comments: bool = True
    include_provenance: bool = False

    def __post_init__(self) -> None:
        # Ensure each extra is a non‑empty string; this mirrors the validation
        # performed for Feature names without imposing the same character set.
        for extra in self.extras:
            if not isinstance(extra, str):
                raise TypeError(f"extras must contain strings, got {type(extra)!r}")
            if not extra:
                raise ValueError("extras entries must be non‑empty strings")


@dataclass(frozen=True, slots=True)
class GitignoreOutput:
    """The full result of generation. Self-describing, hash-stable.

    Hash semantics
    --------------
    - ``content_hash``  = sha256 of ``content``. Identifies the bytes only.
    - ``provenance_hash`` = sha256 of the canonical concatenation
      ``core_version || rules_table_version || templates_version || content_hash``.
      Two outputs with the same ``content`` but coming from different
      ``(core, rules_table, templates)`` triples have **different**
      ``provenance_hash``. Use it for audit trails.
    - ``output_hash`` is preserved as an alias of ``content_hash`` for
      backwards compatibility with API/MCP clients.
    """

    content: str
    rules: tuple[Rule, ...]
    content_hash: str
    provenance_hash: str
    rules_table_version: str
    templates_version: str
    core_version: str

    @property
    def output_hash(self) -> str:  # backwards compat
        return self.content_hash
