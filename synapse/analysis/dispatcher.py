"""Analysis dispatcher — routes files to language-specific analyzers."""

from __future__ import annotations

import os
import sys
from typing import Optional

from synapse.models import FileAnalysis
from synapse.parsing.parser import (
    get_language_for_file, parse_source, has_parse_errors, MAX_FILE_SIZE,
)
from synapse.analysis.python_analyzer import analyze_python


def analyze_file(file_path: str, repo_root: str) -> Optional[FileAnalysis]:
    """Analyze a source file and return the analysis results.
    
    Args:
        file_path: Repo-relative path (POSIX forward slashes).
        repo_root: Absolute path to the repository root.
    
    Returns:
        FileAnalysis or None if the file cannot be analyzed.
    """
    language = get_language_for_file(file_path)
    if language is None:
        return None  # Unsupported extension
    
    # Build absolute path
    abs_path = os.path.join(repo_root, file_path.replace("/", os.sep))
    
    # Check file exists
    if not os.path.isfile(abs_path):
        return None
    
    # Check file size
    file_size = os.path.getsize(abs_path)
    if file_size > MAX_FILE_SIZE:
        analysis = FileAnalysis(
            file_path=file_path,
            language=language,
            parse_error=True,
            parse_error_message=f"File too large ({file_size} bytes, max {MAX_FILE_SIZE})",
        )
        return analysis
    
    # Read file as bytes
    try:
        with open(abs_path, "rb") as f:
            source = f.read()
    except (OSError, IOError) as e:
        analysis = FileAnalysis(
            file_path=file_path,
            language=language,
            parse_error=True,
            parse_error_message=f"Cannot read file: {e}",
        )
        return analysis
    
    # Parse
    root_node = parse_source(source, language)
    if root_node is None:
        analysis = FileAnalysis(
            file_path=file_path,
            language=language,
            parse_error=True,
            parse_error_message="Failed to parse file",
        )
        return analysis
    
    # Route to language analyzer
    if language == "python":
        analysis = analyze_python(root_node, source, file_path)
    else:
        # Placeholder for JS/TS - will be implemented in Phase 2
        analysis = FileAnalysis(
            file_path=file_path,
            language=language,
            parse_error=True,
            parse_error_message=f"Language '{language}' analysis not yet implemented",
        )
    
    # Check for parse errors
    if has_parse_errors(root_node):
        analysis.has_errors = True
    
    return analysis
