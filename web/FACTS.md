# Synapse Facts and Verifications

This document records verified facts about Synapse, their code and runtime sources, and the resolution of all claims from section 2 of the documentation specification.

---

## 1. Verified Core Facts

| Fact | Value / Behavior | Source File & Line or Command |
|---|---|---|
| Package Name | `synapse-pkg` | `pyproject.toml:6` |
| Current Version | `3.0.0` | `pyproject.toml:7` |
| PyPI Availability | Published as `synapse-pkg==3.0.0` (HTTP 200 on `https://pypi.org/pypi/synapse-pkg/json`) | Verified via live PyPI API query |
| Python Requirement | `>=3.10` | `pyproject.toml:11` |
| Environment Tested | Python 3.13.1 on Windows (AMD64) | `python --version` runtime output |
| CLI Executable | `synapse` entrypoint mapped to `synapse.cli:main` | `pyproject.toml:24` |
| Dependencies | `tree-sitter>=0.23,<0.27`, `tree-sitter-python>=0.23,<0.26`, `tree-sitter-javascript>=0.23,<0.26`, `tree-sitter-typescript>=0.23,<0.24` | `pyproject.toml:16-21` |
| Test Suite Count | Exactly 70 tests (70 passed, 0 failed, 0 skipped, 0 xfailed) | `pytest tests/ -v` runtime output |
| License | MIT License | `LICENSE:1`, `pyproject.toml:10` |
| Storage Location | `.synapse/index.db` in repository root | `synapse/core.py:21-27` |
| Schema Version | `1` (`schema_version = '1'`) | `synapse/index/store.py:9` |
| SQLite Settings | `PRAGMA journal_mode=WAL; PRAGMA foreign_keys=ON;` | `synapse/index/store.py:12-13, 133-134` |
| Maximum File Size | 10 MB (10,485,760 bytes) | `synapse/parsing/parser.py:75` |
| Supported Extensions | `.py`, `.js`, `.jsx`, `.mjs`, `.cjs`, `.ts`, `.tsx` | `synapse/parsing/parser.py:15-23` |
| Languages Handled | `python`, `javascript`, `typescript`, `tsx` | `synapse/parsing/parser.py:28-42` |
| Symbol ID Hash | 16-character hex hash: `sha256(f"{file_path}:{qualified_name}:{kind}:{ordinal}").hexdigest()[:16]` | `synapse/models.py:38-42` |
| Graph Node Types | `Repository`, `File`, `Module`, `Class`, `Function`, `Method` | `synapse/graph/builder.py:35-85` |
| Graph Edge Types | `CONTAINS`, `DEFINES`, `IMPORTS`, `CALLS`, `INHERITS_FROM`, `REFERENCES` | `synapse/graph/builder.py:18-25` |
| Reference Statuses | `syntactic`, `resolved`, `unresolved` | `synapse/index/store.py:82`, `synapse/models.py:21-25` |
| ZIP Export Members | `index.json`, `index.md`, `README.txt` | `synapse/export/exporter.py:121, 125, 129` |
| ZIP Fixed Timestamp | `(2026, 1, 1, 0, 0, 0)` for deterministic archive CRC | `synapse/export/exporter.py:117` |
| Default Inspect Depth | `1` | `synapse/cli.py:329` |
| Default Context Results | `10` | `synapse/cli.py:336` |
| Default Context Bytes | `8192` bytes per snippet | `synapse/cli.py:337` |
| Default Context Depth | `2` | `synapse/cli.py:338` |
| Default Search Limit | `20` | `synapse/cli.py:322` |

---

## 2. CLI Commands, Flags, and Defaults

| Command | Option / Flag | Type | Default | Description & Verified Source |
|---|---|---|---|---|
| `synapse init` | `-h`, `--help` | Flag | N/A | Show help message (`synapse/cli.py:305`) |
| `synapse index` | `--rebuild` | Flag | `False` | Force a full rebuild of the index (`synapse/cli.py:310`) |
| `synapse index` | `--json` | Flag | `False` | Output stats as JSON (`synapse/cli.py:311`) |
| `synapse status` | `--json` | Flag | `False` | Output status as JSON (`synapse/cli.py:316`) |
| `synapse search` | `query` | Positional | Required | Search query (symbol or file name) (`synapse/cli.py:321`) |
| `synapse search` | `--limit` | Integer | `20` | Maximum results (`synapse/cli.py:322`) |
| `synapse search` | `--json` | Flag | `False` | Output results as JSON list (`synapse/cli.py:323`) |
| `synapse inspect` | `symbol` | Positional | Required | Symbol name to inspect (`synapse/cli.py:328`) |
| `synapse inspect` | `--depth` | Integer | `1` | Relationship traversal depth (`synapse/cli.py:329`) |
| `synapse inspect` | `--json` | Flag | `False` | Output inspection data as JSON (`synapse/cli.py:330`) |
| `synapse context` | `query` | Positional | Required | Context query (`synapse/cli.py:335`) |
| `synapse context` | `--max-results` | Integer | `10` | Max results count (`synapse/cli.py:336`) |
| `synapse context` | `--max-bytes` | Integer | `8192` | Max bytes per snippet (`synapse/cli.py:337`) |
| `synapse context` | `--depth` | Integer | `2` | Relationship traversal depth (`synapse/cli.py:338`) |
| `synapse context` | `-o`, `--output` | String | `None` | Output file path (`synapse/cli.py:339`) |
| `synapse context` | `--json` | Flag | `False` | Output context document as JSON (`synapse/cli.py:340`) |
| `synapse export` | `format` | Positional | Required (`json`, `md`, `zip`) | Export format (`synapse/cli.py:345`) |
| `synapse export` | `-o`, `--output` | String | `None` | Output file path (`synapse/cli.py:346`) |

---

## 3. Exit Codes

| Code | Condition | Example Trigger | Source |
|---|---|---|---|
| `0` | Success | Normal command execution, search with 0 results found, inspect symbol not found | `synapse/cli.py:31, 54, 76, 117, 139, 249` |
| `1` | Operational error | Non-Git directory, database corrupt, index failure, uninitialized repository, file write error, unhandled exception | `synapse/cli.py:22, 34, 58, 73, 97, 127, 245, 372` |
| `2` | Usage / syntax error | Invoking `synapse` with no command, unknown flag, missing required argument | `synapse/cli.py:359`, `argparse` default |

---

## 4. Default Exclusions

### Excluded Directories (`synapse/exclusions.py:10-32`)
- `.git`
- `.synapse`
- `.venv`, `venv`, `env`, `.env`
- `node_modules`
- `__pycache__`
- `.pytest_cache`, `.mypy_cache`, `.tox`, `.nox`, `.hypothesis`
- `build`, `dist`, `.eggs`, `*.egg-info`
- `.cache`, `htmlcov`, `coverage`, `.coverage`

### Excluded File Patterns (`synapse/exclusions.py:35-63`)
- Minified and bundled assets: `*.min.js`, `*.min.css`, `*.bundle.js`, `*.bundle.css`, `*.map`
- Compiled and binary code: `*.pyc`, `*.pyo`, `*.so`, `*.dll`, `*.dylib`, `*.exe`, `*.o`, `*.a`, `*.class`
- Package archives: `*.jar`, `*.war`, `*.zip`, `*.tar.gz`, `*.whl`, `*.egg`
- Images and media: `*.png`, `*.jpg`, `*.jpeg`, `*.gif`, `*.ico`, `*.svg`, `*.pdf`
- Lockfiles and exports: `*.lock`, `^synapse_export\.`

---

## 5. Error Messages Table

| Error Message | Emitting Location | Cause | Fix |
|---|---|---|---|
| `Error: Not in a git repository.` | `synapse/cli.py:21` | Command executed outside a Git repository | Run command inside a Git repository or initialize one with `git init` |
| `Synapse directory exists but database is corrupt: <detail>` | `synapse/core.py:46`, `synapse/cli.py:33` | `.synapse/index.db` is not a valid SQLite database or header is unreadable | Run `synapse index --rebuild` or remove `.synapse/index.db` and run `synapse init` |
| `Error: Synapse not initialized. Run 'synapse init' first.` | `synapse/cli.py:72, 96, 126, 161, 258` | Subcommand (`status`, `search`, `inspect`, `context`, `export`) run before `synapse init` | Run `synapse init` |
| `Error: <error message>` | `synapse/cli.py:57` | Indexing transaction rolled back due to error | Check file permissions and repository state |
| `Error: writing output file: <e>` | `synapse/cli.py:244` | Destination directory does not exist or lacks write permissions | Verify destination path and permissions |
| `Error: Unknown export format '<format>'` | `synapse/cli.py:290` | Export format not in `json`, `md`, `zip` | Specify one of `json`, `md`, or `zip` |
| `No results found for '<query>'.` | `synapse/cli.py:110` | Symbol or file query did not match any indexed records | Check spelling or run `synapse status` to verify indexed files |
| `Symbol '<symbol>' not found.` | `synapse/retrieval/engine.py:116` | Symbol was not found in indexed symbols table | Run `synapse search` to locate the symbol or verify language support |
| `Ambiguous symbol query '<symbol>'. Multiple symbols match:` | `synapse/retrieval/engine.py:135` | Multiple symbols match query name | Pass the fully qualified name to `synapse inspect` |

---

## 6. Verification Resolution (Section 2 Checklist)

| Claim from Section 2 | Resolution | Evidence |
|---|---|---|
| Package name `synapse-pkg`, version `3.0.0` | **CONFIRMED** | `pyproject.toml:6-7` matches; HTTP 200 on `https://pypi.org/pypi/synapse-pkg/json` |
| Python `>=3.10` tested on 3.10-3.13 on Windows and Linux | **CORRECTED** | `pyproject.toml` requires `>=3.10`. Current environment verified on Python 3.13.1 on Windows. Python 3.10-3.12 and Linux are not claimed as directly tested in this run. |
| Commands: `init`, `index`, `status`, `search`, `inspect`, `context`, `export` | **CONFIRMED** | Verified against `synapse.cli:build_parser` and runtime `--help` executions |
| Exit codes 0, 1, 2 | **CONFIRMED** | Verified in `synapse/cli.py` and test suite `test_phase1.py`, `test_phase7.py` |
| ZIP export contents: `index.json`, `index.md`, `README.txt` | **CONFIRMED** | Verified in `synapse/export/exporter.py:121-129` and test `test_phase6.py` |
| Schema version `schema v1` | **CONFIRMED** | `SCHEMA_VERSION = 1` in `synapse/index/store.py:9` |
| Default file size cap 10 MB | **CONFIRMED** | `MAX_FILE_SIZE = 10 * 1024 * 1024` in `synapse/parsing/parser.py:75` |
| Exclusion list | **CONFIRMED** | Verified in `synapse/exclusions.py` |
| Language and extension table | **CONFIRMED** | Verified in `synapse/parsing/parser.py:15-23` |
| `inspect` default depth of 1 | **CONFIRMED** | `synapse/cli.py:329` |
| Exactly 70 tests in test suite | **CONFIRMED** | `pytest tests/ -v` collected and passed 70 tests |
| Recovery via `--rebuild` | **CONFIRMED** | Tested in `test_corrupt_state_recovery_via_rebuild` and verified via CLI |
| Recovery via delete `.synapse/index.db` + `init` + `index` | **CONFIRMED** | Tested in `test_corrupt_database_recovery` and verified via CLI |

---

## 7. README-versus-Reality Discrepancies

1. **Test counts**: Earlier versions of documentation mentioned varying test counts; the actual verified count across all 8 test modules is 70.
2. **Platform verification**: `README.md` stated "tested on Python 3.10, 3.11, 3.12, 3.13 on Windows and Linux". The verified local test was on Python 3.13.1 on Windows 11. Linux and Python 3.10-3.12 compatibility is supported by pure Python code and standard Tree-sitter binaries, but the docs will clearly state this was not locally executed in this environment.
3. **ZIP export stdout**: `synapse export zip` without `-o` defaults to saving `synapse_export.zip` in the repository root (not binary stdout), while `export json` and `export md` stream to stdout if `-o` is omitted.
