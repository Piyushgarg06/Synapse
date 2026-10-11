# Known Limitations

Synapse operates strictly via static syntax tree analysis without executing code or loading language runtimes. This architecture provides determinism and speed, but imposes specific functional boundaries.

## Dynamic Invocations

Static analysis cannot infer identifiers constructed at runtime. In languages such as Python, JavaScript, and TypeScript, methods invoked via reflection or dynamic attribute access cannot be resolved to concrete symbol declarations.

### Python Reflection Example

Consider `dynamic_call` in `backend/services/user_service.py`:

```python
class UserService(BaseService):
    def get_user(self, user_id: int):
        return self.execute()

    def dynamic_call(self, handler, action: str):
        # Dynamic invocation cannot be resolved at parse time
        return getattr(handler, action)()
```

When Synapse indexes this file, `getattr` is parsed as a call expression referencing the built-in identifier `getattr`. The runtime method target specified in variable `action` is invisible to Tree-sitter:

```bash
$ synapse inspect UserService.dynamic_call
Symbol: UserService.dynamic_call
Kind: method
File: backend/services/user_service.py:7
Defined: lines 7-9

Outbound References:
  getattr (unresolved built-in)
```

The method referenced by `action` does not receive an incoming edge in the knowledge graph.

### JavaScript Computed Properties Example

Computed property access in JavaScript produces identical limitations:

```javascript
export function executeAction(handler, actionName) {
    return handler[actionName]();
}
```

The call target is resolved as a MemberExpression with a computed property, not a direct reference to a declared function symbol.

## External and Standard Library Dependencies

Synapse indexes files contained within the repository root. Third-party packages installed in virtual environments, system paths, or `node_modules` are not indexed into `.synapse/index.db`.

```python
import requests

def fetch_data(url: str):
    response = requests.get(url)
    return response.json()
```

Indexing this file creates:
1. An import entry for module `requests`.
2. A reference to `requests.get`.

Because `requests` is an external dependency located outside the repository boundaries, the reference status remains `unresolved`:

```json
{
  "source_symbol": "fetch_data",
  "target_identifier": "requests.get",
  "resolved": false,
  "reason": "external_package"
}
```

Synapse does not parse external libraries, wheel archives, or system headers.

## Metaprogramming and Code Generation

Symbols created dynamically during module execution do not exist in the source code on disk.

Examples include:
1. Python `namedtuple` factory functions creating synthetic classes.
2. Dynamic decorators that attach attributes to functions at import time.
3. C-extensions, Cython extensions, or native shared objects (`.so`, `.dll`).
4. Macros expanded by external build steps before compilation.

Because Synapse parses source files directly with Tree-sitter, it only recognizes symbols that exist explicitly in the abstract syntax tree.

## Structural Typing and Duck Typing

Synapse tracks calls by qualified names and local imports. It does not run a type-checker or flow-sensitive type inference engine.

If two unrelated classes define identical method names:

```python
class PaymentGateway:
    def process(self):
        pass

class BackgroundTask:
    def process(self):
        pass

def run_job(worker):
    worker.process()
```

Without explicit type declarations or local module bindings, Synapse records an identifier reference to `process`. It cannot guarantee which class instance is provided to `worker` at runtime without full type inference.

## Dirty Working Tree Changes

Synapse only indexes committed files tracked by Git at `HEAD`.

Modifications that exist only in your working tree or staging index are ignored until committed. If you modify a function signature without creating a Git commit, `synapse status` reports the index as up to date relative to `HEAD`, and `synapse search` returns the symbol definition as of the latest commit.

For workflows requiring fresh indexing, create a commit or stash changes before running `synapse index`.
