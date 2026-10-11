---
title: Supported Languages
description: Supported source languages, file extensions, and extraction capabilities
---

# Supported Languages

Synapse parses source files into ASTs using official Tree-sitter language grammar bindings.

---

## Language Support Matrix

| Language | Recognized Extensions | Tree-sitter Grammar Package | Extracted Symbols | Captured Relationships |
|---|---|---|---|---|
| **Python** | `.py` | `tree-sitter-python` | `class`, `function`, `method` | `CONTAINS`, `DEFINES`, `INHERITS_FROM`, `CALLS`, `IMPORTS`, `REFERENCES` |
| **JavaScript** | `.js`, `.jsx`, `.mjs`, `.cjs` | `tree-sitter-javascript` | `class`, `function`, `method` | `CONTAINS`, `DEFINES`, `INHERITS_FROM`, `CALLS`, `IMPORTS`, `REFERENCES` |
| **TypeScript** | `.ts` | `tree-sitter-typescript` (`typescript`) | `class`, `interface`, `function`, `method` | `CONTAINS`, `DEFINES`, `INHERITS_FROM`, `CALLS`, `IMPORTS`, `REFERENCES` |
| **TSX** | `.tsx` | `tree-sitter-typescript` (`tsx`) | `class`, `interface`, `function`, `method` | `CONTAINS`, `DEFINES`, `INHERITS_FROM`, `CALLS`, `IMPORTS`, `REFERENCES` |

---

## Language Extraction Details

### Python
- **Classes**: Extracts class names and identifies base classes listed in parenthesized definitions (`class Child(Base):`).
- **Methods & Functions**: Extracts `def` declarations, capturing parameter names and bodies.
- **Calls**: Detects invocations (`func()` and `obj.method()`).
- **Imports**: Extracts `import module`, `from module import name`, and aliases (`as alias`).

### JavaScript
- **Classes**: Extracts ES6 `class` definitions and `extends` heritage clauses.
- **Methods & Functions**: Extracts function declarations, class methods, constructor methods, and exported function expressions.
- **Imports**: Extracts ES module `import` statements and CommonJS `require()` expressions with string literals.

### TypeScript & TSX
- **Classes & Interfaces**: Extracts both `class` and `interface` declarations, tracking `extends` and `implements` clauses.
- **Methods & Functions**: Extracts typed functions, arrow functions, and class methods.
- **TSX Components**: Parses JSX elements and extracts embedded component calls and props.

---

## Per-Language Gaps

Static analysis has defined boundaries in dynamic languages:

- **Dynamic Python calls**: `getattr()`, `eval()`, and `locals()` calls remain marked as unresolved.
- **Dynamic JavaScript imports**: `import(variable)` and `require(variable)` with non-literal arguments remain unresolved.
- **TypeScript type-only symbols**: Type aliases (`type X = ...`) that are erased at compile time and do not generate callable symbols are not indexed as callable nodes.
