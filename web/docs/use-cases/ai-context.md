---
title: AI Assistant Context
description: Generating focused, bounded context documents for LLMs and coding agents
---

# AI Assistant Context

Goal: Provide focused repository context to an external AI assistant without copying large file trees or exceeding prompt token limits.

---

## Scenario

You are asking an external AI assistant to add logging or validation to `get_user`. Supplying the entire codebase wastes tokens and risks hallucination. You need to supply only `get_user`, its direct callers, and its base dependencies.

---

## Commands and Workflow

### 1. Generate bounded context
Run `synapse context` with bounds tailored for an LLM prompt:

```bash
synapse context get_user --max-results 5 --max-bytes 4096 --depth 2 -o prompt_context.md
```

Output:

```
Context written to prompt_context.md
```

### 2. Inspect generated document
The generated `prompt_context.md` file contains:

```markdown
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

You can append this file directly to your prompt or pass it to an agent tool.

---

## What This Answers

- Supplies the exact, verified code snippet of the target method.
- Shows immediate upstream and downstream dependencies up to the specified depth.
- Explicitly enumerates unresolved calls so the AI does not hallucinate internal definitions for external APIs.

---

## What This Does Not Tell You

- **External library source**: Does not paste the full implementation of Python standard library functions or third-party packages.
- **Runtime values**: Does not provide live database records, runtime payloads, or environment configuration.
