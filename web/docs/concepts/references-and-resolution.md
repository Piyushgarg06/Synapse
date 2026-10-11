---
title: References and Resolution
description: Understanding syntactic, resolved, and unresolved references in Synapse
---

# References and Resolution

Synapse classifies every identifier reference into one of three explicit states: syntactic, resolved, or unresolved.

---

## The Three Reference States

### 1. Syntactic Reference
A syntactic reference is an identifier found during parsing that appears to be a call or name access:

```python
res = self.execute()
```

Here, `execute` is detected as an invocation inside `UserService.get_user`. At the parsing phase, it is recorded as a syntactic reference before cross-file resolution occurs.

### 2. Resolved Reference
A reference becomes resolved when Synapse correlates it with an actual symbol defined within the repository:

- `UserService` inherits from `BaseService` in `backend/base.py`.
- `BaseService` defines the method `execute`.
- Synapse resolves the call site `self.execute()` to the symbol ID of `BaseService.execute`.
- A directed `CALLS` edge is recorded in the `edges` table.

### 3. Unresolved Reference
A reference remains unresolved when static analysis cannot substantiate its target within the indexed files:

```python
def dynamic_call(self, handler, action: str):
    return getattr(handler, action)()
```

In this snippet, `getattr` is an external built-in, and `action` is a runtime variable. Synapse does not invent a target or guess runtime bindings. It records the reference as `status = 'unresolved'`.

---

## Why Unresolved References Matter

Many code analysis tools discard unresolved calls or fabricate hypothetical links. Synapse explicitly tracks unresolved references because they define the boundaries of your codebase:

- **External dependencies**: Calls to Python standard library modules (`os.path.join`, `json.dumps`) or npm packages (`react`, `express`) are recorded as unresolved.
- **Dynamic dispatches**: Calls mediated by `getattr`, `eval`, or dynamic imports are marked as unresolved.
- **Missing index records**: If a file was excluded or had a parse error, calls to its functions remain marked as unresolved until the file is indexed.

---

## Verifying Reference Status

You can query the resolution status of any reference using the CLI.

When running `synapse inspect UserService`:

```
Unresolved References:
  - getattr (backend/services/user_service.py:9)
```

When running `synapse context get_user`:

```
Calls:
  - BaseService.execute (backend/base.py:4)

Unresolved References:
  - os.path.join in analyze_file (synapse/analysis/dispatcher.py:38)
```

The output distinguishes confirmed internal calls from external references.

---

## Related Reference

- To inspect references in a symbol, see [synapse inspect](/reference/cli/inspect).
- For table schemas, see [Storage Schema](/reference/storage-schema).
