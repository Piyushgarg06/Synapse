# Synapse: Repository Intelligence Engine

Synapse is a local-first Repository Intelligence Engine that builds and maintains a persistent, structured representation of a software repository—including files, symbols, and statically identifiable relationships.

## Quick Start

```bash
pip install .
cd /path/to/your/git/repo
synapse init
synapse index
synapse status
synapse search "my_function"
synapse inspect "my_function"
synapse context "my_function"
synapse export json
synapse export md
synapse export zip
```

## Supported Languages

- Python (`.py`)
- JavaScript (`.js`, `.jsx`, `.mjs`, `.cjs`)
- TypeScript (`.ts`, `.tsx`)

## Index Semantics

The index represents the **committed state at HEAD**. The `status` command reports whether the working tree has uncommitted changes that the index does not reflect. The index checkpoint is the last successfully indexed commit SHA.

## More Documentation

Full documentation is being prepared. Run `synapse --help` for command details.
