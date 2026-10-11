# Troubleshooting

This guide provides diagnostic steps and solutions for errors encountered while running Synapse.

## Error Index

| Symptom / Emitted Message | Cause | Resolution Command |
| :--- | :--- | :--- |
| `Error: Not in a git repository.` | Command was run outside a Git work tree. | `git init` or navigate to a repository directory. |
| `Error: Synapse not initialized. Run 'synapse init' first.` | `.synapse/index.db` does not exist in the repository root. | `synapse init` |
| `Synapse directory exists but database is corrupt: <detail>` | The SQLite database header or schema is invalid. | `synapse index --rebuild` or delete `.synapse/index.db` and run `synapse init`. |
| `File too large (<size> bytes, max 10485760)` | File exceeds the default 10 MB size limit. | Add file pattern to `.synapseignore` or reduce file size. |
| `Ambiguous symbol query '<symbol>'. Multiple symbols match:` | Multiple definitions share the same identifier name. | Qualify the target identifier: `synapse inspect ClassName.method_name`. |
| `Symbol '<symbol>' not found.` | Symbol is missing from indexed committed files. | Run `synapse status` to verify index state, or search with `synapse search <query>`. |
| `Error: Unknown export format '<format>'` | Invalid export argument passed. | Specify one of: `synapse export json`, `synapse export md`, or `synapse export zip`. |
| `Error: writing output file: <detail>` | Destination path is non-writable or directory is missing. | Verify filesystem write permissions and create parent directories. |

## Diagnostic Procedures

### 1. Repository Not Detected

When Synapse fails with `Error: Not in a git repository.`, the current working directory is not recognized as a Git root.

Verify Git status:

```bash
git rev-parse --is-inside-work-tree
```

If Git returns `false` or an error:
1. Navigate to the directory containing your `.git` folder.
2. If this is a new project, run `git init` and create an initial commit.

### 2. Missing Index

Commands requiring an existing index (`status`, `search`, `inspect`, `context`, `export`) exit with code 1 if `.synapse/index.db` has not been generated.

Check if `.synapse` exists:

```bash
ls -la .synapse
```

Initialize the database:

```bash
synapse init
synapse index
```

### 3. Database Corruption or Schema Mismatch

If a system crash or manual file editing corrupts `.synapse/index.db`, rebuild the database from the Git repository state.

Run a clean rebuild:

```bash
synapse index --rebuild
```

If the rebuild command cannot open the corrupted database:
1. Remove the damaged database file:
   ```bash
   rm .synapse/index.db
   ```
2. Re-initialize and index:
   ```bash
   synapse init
   synapse index
   ```

### 4. Unindexed Code Changes

If symbols from recently modified files do not appear in `synapse search` or `synapse inspect`, check whether your changes have been committed.

Synapse reads file states from Git commits at `HEAD`. Staged or untracked changes in the working tree are not indexed until committed:

```bash
git status
git add -A
git commit -m "Update symbols"
synapse index
```

### 5. Large File Exclusions

Files exceeding 10,485,760 bytes (10 MB) are skipped during indexing to prevent memory exhaustion during Tree-sitter AST construction.

When a file exceeds this cap, Synapse logs a skipped file warning during indexing and records the skip reason in the database metadata table.

To inspect skipped files, check the JSON output:

```bash
synapse status --json
```
