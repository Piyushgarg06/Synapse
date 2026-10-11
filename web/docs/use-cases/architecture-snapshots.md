---
title: Architecture Snapshots
description: Exporting structured architectural documentation and portable snapshots
---

# Architecture Snapshots

Goal: Generate an architectural snapshot of code structure, symbols, and cross-file relationships for version control or team review.

---

## Scenario

Before tagging a software release, your team requires an updated summary of all declared classes, functions, and cross-file dependencies.

---

## Commands and Workflow

### 1. Export human-readable Markdown architecture document
Generate an architectural reference:

```bash
synapse export md -o ARCHITECTURE.md
```

Output:

```
Exported Markdown overview to ARCHITECTURE.md
```

The resulting `ARCHITECTURE.md` file contains tables of indexed files, language distributions, symbols, and references that can be committed directly to version control.

### 2. Export portable archive snapshot
Export a self-contained ZIP archive:

```bash
synapse export zip -o release_snapshot.zip
```

Output:

```
Exported ZIP snapshot to release_snapshot.zip
```

The archive packages `index.json`, `index.md`, and `README.txt` with normalized timestamps so team members can inspect the graph without cloning the source code.

---

## What This Answers

- Lists every declared symbol across all supported files in a single table.
- Documents the exact commit checkpoint from which the architecture was generated.
- Provides a portable, offline representation of the system structure.

---

## What This Does Not Tell You

- **Non-code assets**: Does not index Markdown documentation, configuration YAML, or dockerfiles.
- **Dynamic behavior**: Does not represent runtime memory layouts or execution timings.
