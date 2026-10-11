---
title: Generating Context for LLMs
description: How to generate bounded, verified source context documents for AI assistants
---

# Generating Context for LLMs

Goal: Produce a focused context document containing source snippets, call relationships, and unresolved references for code generation or review.

---

## Prerequisites

- An indexed repository with an active index checkpoint.

---

## Steps

### Step 1: Generate basic context
Run `synapse context` with your target symbol name:

```bash
synapse context get_user
```

Output:

```
# Synapse Repository Context: get_user

Note: This context document was generated deterministically from static analysis. Snippets reflect indexed files. Dynamic calls, runtime reflection, and unindexed files remain unresolved and must not be assumed to be fully understood.

Found 1 item(s):

## Method: UserService.get_user
Path: `backend/services/user_service.py` (Lines 4-5)
Reason: exact match
```
    def get_user(self, user_id: int):
        return self.execute()
```
Calls:
  - BaseService.execute (backend/base.py:4)
```

The output extracts the snippet from disk and correlates calls to `BaseService.execute`.

### Step 2: Enforce byte and result bounds
To keep token counts small when preparing context for AI models, configure `--max-bytes` and `--max-results`:

```bash
synapse context get_user --max-results 5 --max-bytes 4096 --depth 2
```

- `--max-results 5`: Limits total returned items to 5.
- `--max-bytes 4096`: Truncates any individual snippet exceeding 4,096 bytes.
- `--depth 2`: Includes 2-hop callers and callees in the relationship list.

### Step 3: Write context to a file
Use `-o` to save the output directly to a file:

```bash
synapse context get_user -o prompt_context.md
```

Output:

```
Context written to prompt_context.md
```

---

## Stale Working Tree Detection

Synapse checks whether the source file on disk differs from the indexed commit at `HEAD`. If a file has been modified in your working tree since the last index run, Synapse inserts a warning:

```
Warning: [!] File changed on disk since last indexing; snippet may not reflect working tree.
```

This alerts you that the snippet reflects uncommitted edits that may differ from indexed AST records.

---

## Related Guides

- For complete context options, see [synapse context Reference](/reference/cli/context).
- To export full repository snapshots, see [Exporting Data](/guides/exporting-data).
