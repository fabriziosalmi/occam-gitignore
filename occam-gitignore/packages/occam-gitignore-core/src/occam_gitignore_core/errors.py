# SPDX-License-Identifier: MIT
"""Typed exception hierarchy. No bare excepts allowed downstream."""

from __future__ import annotations


class OccamGitignoreError(Exception):
    """Base class for all errors raised by occam-gitignore."""


class FingerprintError(OccamGitignoreError):
    """Raised when fingerprinting fails on malformed input."""


class TemplateNotFoundError(OccamGitignoreError):
    """Raised when a requested template is missing from the repository."""


class RulesTableError(OccamGitignoreError):
    """Raised when the rules table payload is malformed."""


class DeterminismError(OccamGitignoreError):
    """Raised when a determinism invariant is violated at runtime."""


class ManagedBlockError(OccamGitignoreError):
    """Raised when an existing `.gitignore` has malformed managed-block markers.

    For example a start marker without a matching end marker, or an end marker
    that precedes its start. The file is left untouched so a human can fix it.
    """
