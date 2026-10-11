"""Tree-sitter parsing interface for Synapse."""

from __future__ import annotations

import os
from typing import Optional

import tree_sitter_python as tspython
import tree_sitter_javascript as tsjavascript
import tree_sitter_typescript as tstypescript
from tree_sitter import Language, Parser, Node


# Supported language extensions
LANGUAGE_MAP: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
}

# Language objects (loaded once)
_LANGUAGES: dict[str, Language] = {}


def _get_language(lang_name: str) -> Language:
    """Get or create a Language object."""
    if lang_name not in _LANGUAGES:
        if lang_name == "python":
            _LANGUAGES[lang_name] = Language(tspython.language())
        elif lang_name == "javascript":
            _LANGUAGES[lang_name] = Language(tsjavascript.language())
        elif lang_name == "typescript":
            _LANGUAGES[lang_name] = Language(tstypescript.language_typescript())
        elif lang_name == "tsx":
            _LANGUAGES[lang_name] = Language(tstypescript.language_tsx())
        else:
            raise ValueError(f"Unsupported language: {lang_name}")
    return _LANGUAGES[lang_name]


def get_language_for_file(file_path: str) -> Optional[str]:
    """Get the language name for a file based on extension.
    
    Returns None if the file extension is not supported.
    """
    _, ext = os.path.splitext(file_path)
    return LANGUAGE_MAP.get(ext.lower())


def parse_source(source: bytes, language: str) -> Optional[Node]:
    """Parse source bytes using tree-sitter.
    
    Returns the root node of the parse tree, or None if parsing fails completely.
    """
    lang = _get_language(language)
    parser = Parser(lang)
    tree = parser.parse(source)
    return tree.root_node


def has_parse_errors(root_node: Node) -> bool:
    """Check if the parse tree contains any ERROR nodes."""
    if root_node.type == "ERROR":
        return True
    if root_node.has_error:
        return True
    return False


# Maximum file size to parse (10 MB)
MAX_FILE_SIZE = 10 * 1024 * 1024
