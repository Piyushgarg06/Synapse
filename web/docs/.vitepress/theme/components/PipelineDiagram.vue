<template>
  <div class="pipeline-container" role="region" aria-label="Pipeline Architecture Flow">
    <div style="display: flex; gap: 0.5rem; margin-bottom: 1rem; flex-wrap: wrap;">
      <button
        v-for="(st, idx) in stages"
        :key="st.name"
        type="button"
        @click="activeIdx = idx"
        :style="{
          padding: '0.4rem 0.8rem',
          borderRadius: '4px',
          fontSize: '0.8125rem',
          cursor: 'pointer',
          border: '1px solid ' + (activeIdx === idx ? 'var(--vp-c-brand-1)' : 'var(--vp-c-border)'),
          backgroundColor: activeIdx === idx ? 'var(--vp-c-brand-soft)' : 'var(--vp-c-bg-alt)',
          color: activeIdx === idx ? 'var(--vp-c-brand-1)' : 'var(--vp-c-text-1)',
          fontWeight: activeIdx === idx ? '600' : '400'
        }"
      >
        {{ idx + 1 }}. {{ st.name }}
      </button>
    </div>

    <div style="border: 1px solid var(--vp-c-border); border-radius: 6px; padding: 1.25rem; background: var(--vp-c-bg);">
      <div style="font-weight: 600; font-size: 1rem; color: var(--vp-c-brand-1); margin-bottom: 0.5rem;">
        Stage {{ activeIdx + 1 }}: {{ currentStage.name }}
      </div>
      <p style="font-size: 0.875rem; color: var(--vp-c-text-1); line-height: 1.6; margin-bottom: 1rem;">
        {{ currentStage.description }}
      </p>

      <div style="font-size: 0.75rem; font-weight: 600; color: var(--vp-c-text-2); margin-bottom: 0.25rem;">
        STAGE OUTPUT (SAMPLE REPOSITORY):
      </div>
      <pre style="background: #0d1117; color: #e6edf3; padding: 0.75rem; border-radius: 4px; font-size: 0.8125rem; overflow-x: auto;"><code>{{ currentStage.output }}</code></pre>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

const activeIdx = ref(0)

const stages = [
  {
    name: 'Git Change Detection',
    description: 'Runs git diff -M -z against the last indexed checkpoint SHA to detect file additions, modifications, deletions, and renames with zero filename quoting issues.',
    output: ':100644 100644 ... R100\0frontend/utils/formatter.js\0frontend/utils/string_formatter.js\0',
  },
  {
    name: 'Tree-sitter Parsing',
    description: 'Loads language grammar binaries (Python, JavaScript, TypeScript, TSX) and parses changed source files into Abstract Syntax Trees without executing any code.',
    output: '(module (class_definition name: (identifier) @class.def body: (block ...)))',
  },
  {
    name: 'Structural Analysis',
    description: 'AST visitors extract declared classes, functions, methods, explicit imports, base class names, and call sites. Disallowed syntax and large files are flagged cleanly.',
    output: 'Symbol(name="UserService", kind="class", qualified="UserService", lines=3-12)',
  },
  {
    name: 'SQLite Indexing',
    description: 'Atomically stores files, symbols, imports, calls, and references in .synapse/index.db with WAL mode and foreign key constraints. Transactions rollback on error.',
    output: 'INSERT OR REPLACE INTO symbols VALUES ("57992df372a7a124", "UserService", ...);',
  },
  {
    name: 'Knowledge Graph & Resolution',
    description: 'Constructs CALLS, INHERITS_FROM, CONTAINS, and IMPORTS edges. Resolves cross-file symbol targets. Marks dynamic or external references as explicitly unresolved.',
    output: 'Edge(type="INHERITS_FROM", source="UserService", target="BaseService")',
  },
  {
    name: 'Deterministic Retrieval & Export',
    description: 'Serves search, inspection, bounded LLM context with source verification, and emits byte-identical JSON, Markdown, and ZIP snapshots.',
    output: 'Indexed 6 files, 11 symbols. Edges: 27. Checkpoint: acab2080.',
  },
]

const currentStage = computed(() => stages[activeIdx.value])
</script>
