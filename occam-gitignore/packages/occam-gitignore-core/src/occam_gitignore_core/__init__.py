# SPDX-License-Identifier: MIT
"""occam-gitignore-core: pure, deterministic core.

No I/O, no time, no randomness. All public types are immutable.
"""

from .errors import (
    DeterminismError,
    FingerprintError,
    ManagedBlockError,
    OccamGitignoreError,
    RulesTableError,
    TemplateNotFoundError,
)
from .fingerprint import DefaultFingerprinter, Detector
from .generate import generate
from .ports import Fingerprinter, RulesTable, TemplateRepository
from .reconcile import (
    apply_managed_block,
    build_managed_block,
    missing_patterns,
)
from .rules_table import JsonRulesTable
from .schema import (
    Feature,
    FingerprintResult,
    GenerateOptions,
    GitignoreOutput,
    Rule,
    RuleSource,
)
from .templates import FileSystemTemplateRepository, InMemoryTemplateRepository
from .version import CORE_VERSION

__all__ = [
    "CORE_VERSION",
    "DefaultFingerprinter",
    "Detector",
    "DeterminismError",
    "Feature",
    "FileSystemTemplateRepository",
    "FingerprintError",
    "FingerprintResult",
    "Fingerprinter",
    "GenerateOptions",
    "GitignoreOutput",
    "InMemoryTemplateRepository",
    "JsonRulesTable",
    "ManagedBlockError",
    "OccamGitignoreError",
    "Rule",
    "RuleSource",
    "RulesTable",
    "RulesTableError",
    "TemplateNotFoundError",
    "TemplateRepository",
    "apply_managed_block",
    "build_managed_block",
    "generate",
    "missing_patterns",
]
