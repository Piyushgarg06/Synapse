---
title: Codebase Onboarding
description: Using Synapse to understand structure when joining an unfamiliar codebase
---

# Codebase Onboarding

Goal: Explore an unfamiliar repository to identify primary classes, entry points, and module relationships without reading every file manually.

---

## Scenario

You have joined a project containing backend services and frontend components. You need to identify where core business logic is declared and what base classes exist.

---

## Commands and Workflow

### 1. View overall repository scale
Run `synapse status` to inspect total files, symbols, and parse health:

```bash
synapse status
```

Output:

```
Synapse Status:
  HEAD commit:    acab2080
  Last indexed:   acab2080
  Up to date:     yes
  Files indexed:  6
  Symbols:        11
  Edges:          27
```

### 2. Search for high-level entities
Search for domain terms such as `Service` or `User`:

```bash
synapse search Service
```

Output:

```
Found 3 result(s) for 'Service':
  class     BaseService  (backend/base.py:1)
  class     UserService  (backend/services/user_service.py:3)
  class     AuthService  (backend/services/auth_service.py:3)
```

### 3. Inspect class hierarchies
Inspect `UserService` to view its inheritance structure:

```bash
synapse inspect UserService
```

Output:

```
Symbol: UserService (class)
  File:     backend/services/user_service.py:3-12
  ID:       57992df372a7a124
  Inherits from:
    - BaseService (backend/base.py:1)
```

The output reveals that `UserService` extends `BaseService` defined in `backend/base.py`.

---

## What This Answers

- Locates the files declaring key services in under two seconds.
- Identifies the base class hierarchy across files.
- Confirms which methods belong to which service classes.

---

## What This Does Not Tell You

- **Runtime configuration**: Does not show environment variables or database connection strings loaded at startup.
- **Dynamic handler registration**: If services are registered dynamically through a plugin loop or reflection, those runtime registrations will not appear in the static graph.
- **Execution order**: Does not tell you which service runs first when the application boots. You must inspect application entrypoints to determine boot order.
