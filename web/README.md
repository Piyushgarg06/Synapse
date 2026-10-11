# Synapse Documentation Website

The documentation website for Synapse, a local-first Repository Intelligence Engine.

Stack choice: Built with VitePress using client-side MiniSearch.
Reason: Delivers zero-server static HTML output with reproducible offline search,
strict dead-link checking, and fast native component integration
without external runtime network dependencies.

---

## Commands

### 1. Install Toolchain Dependencies
```bash
npm install
```

### 2. Run Local Development Server
```bash
npm run docs:dev
```
Starts local live-reloading dev server at `http://localhost:5173`.

### 3. Build Static Documentation
```bash
npm run docs:build
```
Builds static HTML distribution to `web/docs/.vitepress/dist`. Warnings and broken links are treated as errors.

### 4. Preview Production Build
```bash
npm run docs:preview
```
Serves the built distribution locally for verification.

### 5. Run Quality and Verification Checks
```bash
# Run the anti-slop linter
npm run lint:slop

# Run the slop linter self-test
npm run test:lint

# Regenerate all command outputs from the sample repo
npm run capture

# Verify documentation outputs have not drifted from CLI output
npm run check:drift

# Run the full validation suite
npm run check
```
