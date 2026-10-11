"""Default file exclusion patterns for Synapse."""

from __future__ import annotations

import os
import re
from pathlib import PurePosixPath

# Directories to always exclude
EXCLUDED_DIRS: set[str] = {
    ".git",
    ".synapse",
    ".venv",
    "venv",
    "env",
    ".env",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".tox",
    ".nox",
    "build",
    "dist",
    ".eggs",
    "*.egg-info",
    ".cache",
    ".hypothesis",
    "htmlcov",
    "coverage",
    ".coverage",
}

# File patterns to exclude (compiled as regexes)
EXCLUDED_FILE_PATTERNS: list[str] = [
    r"\.min\.(js|css)$",       # Minified files
    r"\.bundle\.(js|css)$",    # Bundled files
    r"\.map$",                 # Source maps
    r"\.pyc$",                 # Compiled Python
    r"\.pyo$",                 # Optimized Python
    r"\.so$",                  # Shared objects
    r"\.dll$",                 # Windows DLLs
    r"\.dylib$",               # macOS dynamic libs
    r"\.exe$",                 # Windows executables
    r"\.o$",                   # Object files
    r"\.a$",                   # Archives
    r"\.class$",               # Java class files
    r"\.jar$",                 # Java archives
    r"\.war$",                 # Web archives
    r"\.zip$",                 # Zip archives
    r"\.tar\.gz$",             # Tarballs
    r"\.whl$",                 # Python wheels
    r"\.egg$",                 # Python eggs
    r"\.png$",                 # Images
    r"\.jpg$",                 # Images
    r"\.jpeg$",                # Images
    r"\.gif$",                 # Images
    r"\.ico$",                 # Icons
    r"\.svg$",                 # Vector images
    r"\.pdf$",                 # PDFs
    r"\.lock$",                # Lock files
    r"^synapse_export\.",      # Export files
]

_COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in EXCLUDED_FILE_PATTERNS]


def should_exclude_path(rel_path: str) -> bool:
    """Check if a repo-relative path should be excluded from indexing.
    
    Args:
        rel_path: Repository-relative path with forward slashes.
    
    Returns:
        True if the path should be excluded.
    """
    parts = PurePosixPath(rel_path).parts
    
    # Check directory exclusions
    for part in parts[:-1]:  # All but the last component (the filename)
        if part in EXCLUDED_DIRS:
            return True
        # Match wildcard patterns like *.egg-info
        for excluded in EXCLUDED_DIRS:
            if "*" in excluded:
                pattern = excluded.replace(".", r"\.").replace("*", ".*")
                if re.match(pattern, part):
                    return True
    
    # Check if the filename itself is an excluded directory name
    # (e.g., a file named ".synapse" at the root)
    filename = parts[-1] if parts else rel_path
    
    # Check file patterns
    for pattern in _COMPILED_PATTERNS:
        if pattern.search(filename):
            return True
    
    return False
