"""Data models for Synapse."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class SymbolKind(Enum):
    """Types of symbols extracted from source code."""
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"


class EdgeType(Enum):
    """Types of relationships between graph nodes."""
    CONTAINS = "CONTAINS"
    DEFINES = "DEFINES"
    IMPORTS = "IMPORTS"
    CALLS = "CALLS"
    INHERITS_FROM = "INHERITS_FROM"
    REFERENCES = "REFERENCES"


class ReferenceStatus(Enum):
    """Resolution status of a reference."""
    SYNTACTIC = "syntactic"      # Found in source, resolution not attempted
    RESOLVED = "resolved"        # Linked to a known repo symbol ID
    UNRESOLVED = "unresolved"    # Kept with the raw name text


@dataclass
class SourceLocation:
    """Source location with byte offsets and line/column."""
    start_byte: int
    end_byte: int
    start_line: int  # 1-based
    start_column: int  # 0-based
    end_line: int  # 1-based
    end_column: int  # 0-based


@dataclass
class SymbolInfo:
    """A symbol extracted from source code."""
    name: str
    qualified_name: str
    kind: SymbolKind
    file_path: str  # repo-relative, POSIX forward slashes
    location: SourceLocation
    ordinal: int = 0  # For disambiguating duplicate names within a file

    @property
    def symbol_id(self) -> str:
        """Deterministic symbol ID from (path, qualified_name, kind, ordinal)."""
        raw = f"{self.file_path}::{self.qualified_name}::{self.kind.value}::{self.ordinal}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


@dataclass
class ReferenceInfo:
    """A reference found in source code."""
    name: str
    file_path: str  # repo-relative POSIX path
    location: SourceLocation
    status: ReferenceStatus = ReferenceStatus.SYNTACTIC
    resolved_symbol_id: Optional[str] = None
    context_qualified_name: str = ""  # The qualified name of the containing symbol


@dataclass
class ImportInfo:
    """An import statement found in source code."""
    module_name: str
    imported_names: list[str] = field(default_factory=list)
    alias: Optional[str] = None
    file_path: str = ""  # repo-relative POSIX path
    location: Optional[SourceLocation] = None
    is_default: bool = False  # JS/TS default import
    is_namespace: bool = False  # JS/TS namespace import (import * as X)


@dataclass
class InheritanceInfo:
    """A class inheritance relationship."""
    class_name: str
    base_class_name: str
    file_path: str = ""  # repo-relative POSIX path


@dataclass
class CallInfo:
    """A function/method call found in source."""
    caller_qualified_name: str
    callee_name: str
    file_path: str = ""  # repo-relative POSIX path
    location: Optional[SourceLocation] = None


@dataclass
class FileAnalysis:
    """Complete analysis results for a single file."""
    file_path: str  # repo-relative POSIX path
    language: str
    symbols: list[SymbolInfo] = field(default_factory=list)
    references: list[ReferenceInfo] = field(default_factory=list)
    imports: list[ImportInfo] = field(default_factory=list)
    inheritance: list[InheritanceInfo] = field(default_factory=list)
    calls: list[CallInfo] = field(default_factory=list)
    parse_error: bool = False
    parse_error_message: str = ""
    has_errors: bool = False  # tree-sitter found errors but partial extraction was done
