# Synapse Documentation Site - Final Verification Report

This report summarizes the implementation, verification gates, empirical findings, and operational checks for the Synapse documentation site located in `web/`.

---

## 1. Directory Tree Summary

The documentation site is organized under `web/`:

```
web/
├── package.json                          # Pinned toolchain dependencies
├── package-lock.json                     # Dependency lockfile
├── README.md                             # Setup, build, preview, and verification instructions
├── FACTS.md                              # Source-of-truth verification table
├── DECISIONS.md                          # Architecture and design decision log
├── DESIGN.md                             # Design system tokens and palette
├── REPORT.md                             # This final verification report
├── scripts/
│   ├── slop_terms.txt                    # Banned marketing and slop terms
│   ├── slop_lint.py                      # Prose and design pattern linter
│   ├── test_slop_lint.py                 # Self-test suite for slop linter
│   ├── capture_pipeline.py               # Deterministic CLI capture pipeline
│   ├── check_drift.py                    # Byte-identical output drift verifier
│   └── check_json_schemas.py             # Schema validator for captured JSON
└── docs/
    ├── .vitepress/
    │   ├── config.mts                    # Site configuration, clean URLs, navigation tree
    │   └── theme/
    │       ├── index.ts                  # Theme entry point registering custom components
    │       ├── custom.css                # Custom design system tokens and typography
    │       └── components/
    │           ├── TerminalPlayer.vue    # Interactive session player
    │           ├── InteractiveGraph.vue  # SVG knowledge graph explorer
    │           └── PipelineDiagram.vue   # Architecture pipeline diagram
    ├── public/
    │   └── favicon.svg                   # Brand SVG favicon
    ├── _generated/                       # 33 captured CLI text outputs and manifests
    ├── index.md                          # Home page with graph and terminal replay
    ├── limitations.md                    # Static analysis boundaries with examples
    ├── troubleshooting.md                # Error catalogue and recovery procedures
    ├── faq.md                            # Operational questions and guarantees
    ├── cheatsheet.md                     # Compact commands matrix and exit codes
    ├── architecture.md                   # Contributor architecture and pipeline flow
    ├── license.md                        # MIT License
    ├── getting-started/
    │   ├── installation.md
    │   └── quickstart.md
    ├── concepts/
    │   ├── how-synapse-works.md
    │   ├── the-index.md
    │   ├── symbols-and-ids.md
    │   ├── references-and-resolution.md
    │   ├── graph.md
    │   ├── incremental-indexing.md
    │   └── determinism.md
    ├── guides/
    │   ├── index-a-repository.md
    │   ├── keep-the-index-current.md
    │   ├── inspecting-symbols.md
    │   ├── context-generation.md
    │   ├── exporting-data.md
    │   ├── exclusions-and-limits.md
    │   └── index-recovery.md
    ├── use-cases/
    │   ├── onboarding.md
    │   ├── impact-analysis.md
    │   ├── ai-context.md
    │   └── architecture-snapshots.md
    └── reference/
        ├── storage-schema.md
        ├── json-output.md
        ├── exports.md
        ├── configuration.md
        ├── exclusions.md
        ├── languages.md
        ├── error-messages.md
        └── cli/
            ├── overview.md
            ├── init.md
            ├── index.md
            ├── status.md
            ├── search.md
            ├── inspect.md
            ├── context.md
            ├── export.md
            └── exit-codes.md
```

---

## 2. Tooling Choice and Rationale

- **Framework**: VitePress `1.6.4`.
- **Search Provider**: Built-in local offline MiniSearch (`provider: 'local'`).
- **Rationale**: VitePress compiles to static HTML with zero external runtime dependencies. Local search indexes directly at build time without downloading platform-specific binaries or contacting external networks. Route-level Vue islands allow embedding interactive diagrams without loading components globally.

---

## 3. Decisions and Deviations from Prompt

1. **Backdrop-Filter Single Exemption**: A single functional `backdrop-filter: blur(12px)` was implemented on the sticky navigation header (`.VPNav`).
2. **Page Tree Consolidation**: Subcommand reference pages are consolidated under `reference/cli/<subcommand>.md` with an `overview.md` page.
3. **Capture Scenario Determinism**: Git author and committer dates (`2026-01-01T00:00:00Z`) and Git ceiling directories were injected during capture to ensure byte-identical commit SHAs across independent runs.
4. **Color Palette**: Deep slate background (`#0b0f19`) with warm amber accents (`#d97706`, `#f59e0b`), avoiding banned purple-to-blue gradients.

---

## 4. FACTS.md Summary and Discrepancies

- **PyPI Package**: `synapse-pkg==3.0.0` confirmed published and verified via HTTP query.
- **Python Compatibility**: Python `>= 3.10` confirmed in `pyproject.toml`. Verified running on Python `3.13.1`.
- **Test Suite**: Exact count verified at 70 passed tests (`70 passed in 49.92s`).
- **File Size Cap**: Default 10 MB cap verified at 10,485,760 bytes in `synapse/exclusions.py`.
- **ZIP Export Contents**: Verified to contain `index.json`, `index.md`, and `README.txt`.
- **Schema Version**: `schema v1` verified in `synapse/index/store.py`.

### Discrepancies Documented
- `README.md` claimed "tested on 3.10 to 3.13 on Windows and Linux". The test suite was verified locally on Windows 11 with Python 3.13.1; other OS/version combinations are noted as unverified locally.

---

## 5. Bugs or Surprising Behavior in Synapse

1. **Working Tree Changes**: `synapse index` inspects only committed Git states at `HEAD`. Staged or untracked changes are ignored without warnings.
2. **Dynamic Invocations**: Methods dispatched dynamically via `getattr()` or JavaScript computed properties remain unresolved in the knowledge graph.
3. **External Dependencies**: Standard library and third-party modules outside the repository tree remain marked as unresolved external symbols.

---

## 6. Verification and Quality Assurance Results

| Check | Tool / Method | Result | Notes |
| :--- | :--- | :--- | :--- |
| Strict Build | `npm run docs:build` | Passed | 0 errors, all pages rendered in 17.81s |
| Drift Check | `python web/scripts/check_drift.py` | Passed | 100% byte-identical re-run output |
| JSON Schema | `python web/scripts/check_json_schemas.py` | Passed | All 33 CLI JSON outputs validate |
| Slop Linter | `python web/scripts/slop_lint.py` | Passed | 0 hard failures |
| Slop Self-Test | `python web/scripts/test_slop_lint.py` | Passed | All violations accurately detected |
| Pytest Suite | `python -m pytest` | Passed | 70 passed in 49.92s |
| Offline Mode | Preview on `localhost:4173` | Passed | Zero external network calls |

---

## 7. Commands to Reproduce

```bash
# 1. Install toolchain dependencies
cd web
npm ci

# 2. Build the documentation site
npm run docs:build

# 3. Preview locally
npm run docs:preview

# 4. Regenerate captured terminal outputs
npm run capture

# 5. Check for output drift
npm run check:drift

# 6. Validate JSON schemas
npm run check:schemas

# 7. Run slop linter
npm run check:slop
```
