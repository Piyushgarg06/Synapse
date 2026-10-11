---
title: Exclusions and Limits
description: Understanding default path exclusions, file patterns, and size caps
---

# Exclusions and Limits

Goal: Identify which files Synapse excludes from indexing and understand the maximum file size limit.

---

## Prerequisites

- Access to the repository where Synapse is running.

---

## Default Directory Exclusions

Synapse automatically ignores files located within known non-source or dependency directories:

- Version control: `.git`
- Synapse metadata: `.synapse`
- Package managers: `node_modules`, `site-packages`
- Virtual environments: `.venv`, `venv`, `env`, `.env`
- Build outputs: `build`, `dist`, `.eggs`, `*.egg-info`
- Caches and test coverage: `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.cache`, `htmlcov`, `.coverage`

---

## Default File Pattern Exclusions

In addition to directory rules, Synapse ignores specific file types:

- **Minified and bundled code**: `*.min.js`, `*.min.css`, `*.bundle.js`, `*.bundle.css`, `*.map`
- **Compiled binaries**: `*.pyc`, `*.so`, `*.dll`, `*.dylib`, `*.exe`, `*.o`, `*.class`
- **Archives**: `*.zip`, `*.tar.gz`, `*.whl`, `*.jar`
- **Images and media**: `*.png`, `*.jpg`, `*.jpeg`, `*.svg`, `*.ico`, `*.pdf`
- **Export files**: `^synapse_export\.`

---

## Maximum File Size Cap

Synapse enforces an upper limit on individual source file sizes:

- **Limit**: `10 MB` (`10,485,760 bytes`).
- **Behavior**: If a source file exceeds 10 MB, Synapse does not pass it to Tree-sitter. Instead, it records a parse error in the `files` table:
  ```
  File too large (12485760 bytes, max 10485760)
  ```
- **Rationale**: Prevents excessive memory consumption and potential parser freezes on generated bundle artifacts.

---

## Related Reference

- For the full compiled exclusion list, see [Default Exclusions Reference](/reference/exclusions).
- To inspect files with parse errors, run [synapse status](/reference/cli/status).
