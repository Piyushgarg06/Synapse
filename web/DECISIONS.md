# Architectural and Implementation Decisions

This log documents non-trivial decisions and deviations from the initial prompt specification, recorded as required by section 1.1.

---

### Decision 1: Documentation Toolchain Selection
- **Prompt:** Section 5 permitted Astro, Starlight, VitePress, or custom static generators with offline client-side search and no server requirements.
- **Choice:** Selected VitePress with built-in client-side MiniSearch provider (`provider: 'local'`).
- **Rationale:** VitePress generates pure static HTML/CSS/JS without requiring any background runtime server. Its local search compiles client-side search indices at build time with zero external network downloads or platform-specific binaries, guaranteeing reproducible offline builds across Windows and Linux.

### Decision 2: Single Allowed Backdrop-Filter Exception
- **Prompt:** Section 7.6 bans decorative glassmorphism and allows at most one functional use of `backdrop-filter`.
- **Choice:** Confined `backdrop-filter: blur(12px)` strictly to the sticky top navigation header (`.VPNav`) to preserve legibility when scrolling underneath content.
- **Rationale:** Standard functional requirement for fixed navigation bars with high-contrast text.

### Decision 3: Custom Typography Stack
- **Prompt:** Section 7.2 requires self-hosted or standard system-native variable fonts with verified licenses and zero layout shift.
- **Choice:** Defined clean system-first sans-serif stack (`ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`) with monospace tabular fonts (`ui-monospace, "SF Mono", Monaco, "Cascadia Code", "Roboto Mono", monospace`).
- **Rationale:** Guarantees zero layout shift, zero third-party font downloads, zero network latency, and pristine legibility across Windows, macOS, and Linux.

### Decision 4: Page Tree Structure
- **Prompt:** Section 6 outlined a comprehensive two-level documentation tree.
- **Choice:** Retained the full structure covering Getting Started, Concepts, Guides, Use Cases, and CLI Reference, while omitting speculative pages that have no verified code backing.
- **Rationale:** Adheres to section 1.1 rule: prefer an accurate concise page over a padded or unverified placeholder.
