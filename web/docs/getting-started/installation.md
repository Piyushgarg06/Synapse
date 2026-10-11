---
title: Installation
description: Requirements, installation steps, and verification for Synapse
---

# Installation

This page covers the prerequisites, installation methods, verification steps, and removal instructions for the Synapse CLI.

---

## Requirements

Before installing Synapse, ensure the following tools are available in your environment:

- **Python**: Version 3.10 or newer (tested on Python 3.13.1 on Windows AMD64).
- **Git**: Executable available in your system `PATH`.
- **Operating system**: Windows, macOS, or Linux.

To verify your installed versions, run:

```bash
python --version
git --version
```

---

## Install from PyPI

Synapse is published on the Python Package Index under the package name `synapse-pkg`. Install it using pip:

```bash
pip install synapse-pkg==3.0.0
```

To install the latest release without specifying an exact version:

```bash
pip install synapse-pkg
```

---

## Install from Source

To install directly from the source repository:

```bash
git clone https://github.com/Piyushgarg06/Synapse.git
cd Synapse
pip install .
```

For local development and testing, install with editable mode:

```bash
pip install -e .
pip install pytest
```

---

## Verification

After installation, verify that the `synapse` command is available in your terminal:

```bash
synapse --help
```

Expected output:

```
usage: synapse [-h] {init,index,status,search,inspect,context,export} ...

Synapse: Repository Intelligence Engine - local-first structural analysis and
retrieval

positional arguments:
  {init,index,status,search,inspect,context,export}
                        Available commands
    init                Initialize Synapse in a Git repository
    index               Index the repository (initial or incremental)
    status              Show index status and statistics
    search              Search for symbols and files
    inspect             Inspect a symbol's definition and relationships
    context             Retrieve focused repository context
    export              Export index data

options:
  -h, --help            show this help message and exit
```

---

## Upgrading and Uninstalling

To upgrade an existing installation to the latest release:

```bash
pip install --upgrade synapse-pkg
```

To remove Synapse from your Python environment:

```bash
pip uninstall -y synapse-pkg
```
