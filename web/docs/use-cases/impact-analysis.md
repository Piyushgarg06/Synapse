---
title: Impact Analysis and Refactoring
description: Evaluating callers and downstream dependencies before modifying code
---

# Impact Analysis and Refactoring

Goal: Identify all internal callers and dependent subclasses before modifying a function signature or deleting a class.

---

## Scenario

You need to change the method signature of `execute` in `BaseService`. Before altering its arguments, you must know every method that invokes it across the codebase.

---

## Commands and Workflow

### 1. Inspect the target symbol
Run `synapse inspect` on `BaseService.execute`:

```bash
synapse inspect BaseService.execute
```

Output:

```
Symbol: BaseService.execute (method)
  File:     backend/base.py:4-5
  ID:       4bfc70378e3f43a9
  Callers:
    - UserService.get_user (backend/services/user_service.py:4)
```

The output identifies that `UserService.get_user` directly calls `BaseService.execute`.

### 2. Inspect dependent subclasses
Inspect `BaseService` to see every class that inherits from it:

```bash
synapse inspect BaseService
```

Output:

```
Symbol: BaseService (class)
  File:     backend/base.py:1-8
  ID:       50877967954a0126
  Subclasses:
    - UserService (backend/services/user_service.py:3)
    - AuthService (backend/services/auth_service.py:3)
```

The output identifies both `UserService` and `AuthService` as subclasses that might be affected by changes to `BaseService`.

---

## What This Answers

- Lists all statically resolvable callers across Python, JavaScript, and TypeScript.
- Pinpoints the exact files and line numbers where the calls occur.
- Identifies all subclasses inheriting from the target class.

---

## What This Does Not Tell You

- **Dynamic invocations**: Does not identify callers that use reflection, such as `getattr(service, "execute")()` or `service[methodName]()`.
- **Runtime monkey-patching**: If code dynamically replaces a method at runtime, those patches are not captured.
- **External consumers**: If your repository is a library, Synapse cannot detect callers located in separate, external repositories that import your package. You must verify external API compatibility separately.
