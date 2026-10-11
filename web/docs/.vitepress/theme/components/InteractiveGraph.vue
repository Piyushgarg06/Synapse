<template>
  <div class="graph-container" role="region" aria-label="Interactive Knowledge Graph">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
      <span style="font-weight: 600; font-size: 0.875rem;">Sample Repository Knowledge Graph (Real AST Export)</span>
      <span style="font-size: 0.75rem; color: var(--vp-c-text-2);">Click or hover nodes to inspect</span>
    </div>

    <svg
      class="graph-svg"
      viewBox="0 0 800 420"
      xmlns="http://www.w3.org/2000/svg"
      role="img"
      aria-labelledby="graphTitle graphDesc"
    >
      <title id="graphTitle">Synapse Sample Repository Structural Graph</title>
      <desc id="graphDesc">
        Graph representing files, classes, methods, and relationships extracted from sample repository.
      </desc>

      <defs>
        <!-- Arrowhead markers -->
        <marker id="arrow-calls" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M 0 1 L 9 5 L 0 9 z" fill="#d97706" />
        </marker>
        <marker id="arrow-inherits" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M 0 1 L 9 5 L 0 9 z" fill="#2563eb" />
        </marker>
        <marker id="marker-unresolved" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto">
          <circle cx="5" cy="5" r="3" fill="none" stroke="#dc2626" stroke-width="1.5" />
        </marker>
      </defs>

      <!-- Edges -->
      <g class="edges">
        <!-- UserService -> BaseService (INHERITS_FROM) -->
        <line x1="280" y1="160" x2="160" y2="160" stroke="#2563eb" stroke-width="2" stroke-dasharray="4,3" marker-end="url(#arrow-inherits)" />

        <!-- AuthService -> BaseService (INHERITS_FROM) -->
        <line x1="280" y1="280" x2="160" y2="180" stroke="#2563eb" stroke-width="2" stroke-dasharray="4,3" marker-end="url(#arrow-inherits)" />

        <!-- get_user -> execute (CALLS) -->
        <line x1="420" y1="140" x2="160" y2="190" stroke="#d97706" stroke-width="2" marker-end="url(#arrow-calls)" />

        <!-- UserCard -> formatName (CALLS) -->
        <line x1="680" y1="150" x2="550" y2="280" stroke="#d97706" stroke-width="2" marker-end="url(#arrow-calls)" />

        <!-- App.tsx -> types.ts (IMPORTS) -->
        <line x1="680" y1="120" x2="550" y2="120" stroke="#64748b" stroke-width="1.5" stroke-dasharray="2,2" />

        <!-- dynamic_call -> unresolved getattr (UNRESOLVED) -->
        <line x1="420" y1="190" x2="420" y2="250" stroke="#dc2626" stroke-width="1.5" stroke-dasharray="3,3" marker-end="url(#marker-unresolved)" />
      </g>

      <!-- Nodes -->
      <g class="nodes">
        <!-- BaseService (Class) -->
        <g
          tabindex="0"
          role="button"
          :aria-label="'BaseService class in backend/base.py'"
          @click="selectNode('BaseService', 'class', 'backend/base.py', 'Base class defining execute and calculate_hash')"
          @keydown.enter="selectNode('BaseService', 'class', 'backend/base.py', 'Base class defining execute and calculate_hash')"
          style="cursor: pointer;"
        >
          <rect x="90" y="130" width="120" height="50" rx="6" fill="#1e293b" stroke="#3b82f6" stroke-width="2" />
          <text x="150" y="160" fill="#f8fafc" text-anchor="middle" font-size="12" font-family="monospace">BaseService</text>
        </g>

        <!-- UserService (Class) -->
        <g
          tabindex="0"
          role="button"
          :aria-label="'UserService class in backend/services/user_service.py'"
          @click="selectNode('UserService', 'class', 'backend/services/user_service.py', 'Subclass of BaseService with get_user and delete_user')"
          @keydown.enter="selectNode('UserService', 'class', 'backend/services/user_service.py', 'Subclass of BaseService with get_user and delete_user')"
          style="cursor: pointer;"
        >
          <rect x="260" y="130" width="120" height="50" rx="6" fill="#1e293b" stroke="#3b82f6" stroke-width="2" />
          <text x="320" y="160" fill="#f8fafc" text-anchor="middle" font-size="12" font-family="monospace">UserService</text>
        </g>

        <!-- get_user (Method) -->
        <g
          tabindex="0"
          role="button"
          :aria-label="'get_user method in UserService'"
          @click="selectNode('get_user', 'method', 'backend/services/user_service.py:4', 'Calls BaseService.execute')"
          @keydown.enter="selectNode('get_user', 'method', 'backend/services/user_service.py:4', 'Calls BaseService.execute')"
          style="cursor: pointer;"
        >
          <circle cx="420" cy="140" r="24" fill="#0f172a" stroke="#d97706" stroke-width="2" />
          <text x="420" y="144" fill="#f8fafc" text-anchor="middle" font-size="10" font-family="monospace">get_user</text>
        </g>

        <!-- dynamic_call (Method) -->
        <g
          tabindex="0"
          role="button"
          :aria-label="'dynamic_call method in UserService'"
          @click="selectNode('dynamic_call', 'method', 'backend/services/user_service.py:7', 'Contains unresolved runtime getattr invocation')"
          @keydown.enter="selectNode('dynamic_call', 'method', 'backend/services/user_service.py:7', 'Contains unresolved runtime getattr invocation')"
          style="cursor: pointer;"
        >
          <circle cx="420" cy="190" r="24" fill="#0f172a" stroke="#dc2626" stroke-width="2" />
          <text x="420" y="194" fill="#f8fafc" text-anchor="middle" font-size="9" font-family="monospace">dynamic</text>
        </g>

        <!-- Unresolved getattr marker -->
        <g tabindex="0" role="button" aria-label="Unresolved target: getattr">
          <circle cx="420" cy="265" r="14" fill="#450a0a" stroke="#dc2626" stroke-width="1.5" stroke-dasharray="2,2" />
          <text x="420" y="269" fill="#fca5a5" text-anchor="middle" font-size="9" font-family="monospace">?</text>
        </g>

        <!-- AuthService (Class) -->
        <g
          tabindex="0"
          role="button"
          :aria-label="'AuthService class in backend/services/auth_service.py'"
          @click="selectNode('AuthService', 'class', 'backend/services/auth_service.py', 'Subclass of BaseService added in incremental commit')"
          @keydown.enter="selectNode('AuthService', 'class', 'backend/services/auth_service.py', 'Subclass of BaseService added in incremental commit')"
          style="cursor: pointer;"
        >
          <rect x="260" y="260" width="120" height="50" rx="6" fill="#1e293b" stroke="#3b82f6" stroke-width="2" />
          <text x="320" y="290" fill="#f8fafc" text-anchor="middle" font-size="12" font-family="monospace">AuthService</text>
        </g>

        <!-- formatName (Function) -->
        <g
          tabindex="0"
          role="button"
          :aria-label="'formatName function in frontend/utils/string_formatter.js'"
          @click="selectNode('formatName', 'function', 'frontend/utils/string_formatter.js:1', 'Exported JavaScript function called by UserCard')"
          @keydown.enter="selectNode('formatName', 'function', 'frontend/utils/string_formatter.js:1', 'Exported JavaScript function called by UserCard')"
          style="cursor: pointer;"
        >
          <circle cx="550" cy="280" r="28" fill="#0f172a" stroke="#d97706" stroke-width="2" />
          <text x="550" y="284" fill="#f8fafc" text-anchor="middle" font-size="10" font-family="monospace">formatName</text>
        </g>

        <!-- User (Interface/Type) -->
        <g
          tabindex="0"
          role="button"
          :aria-label="'User interface in frontend/types.ts'"
          @click="selectNode('User', 'interface', 'frontend/types.ts:1', 'TypeScript interface imported into App.tsx')"
          @keydown.enter="selectNode('User', 'interface', 'frontend/types.ts:1', 'TypeScript interface imported into App.tsx')"
          style="cursor: pointer;"
        >
          <rect x="490" y="100" width="100" height="40" rx="6" fill="#1e293b" stroke="#10b981" stroke-width="2" />
          <text x="540" y="125" fill="#f8fafc" text-anchor="middle" font-size="11" font-family="monospace">User</text>
        </g>

        <!-- UserCard (TSX Component) -->
        <g
          tabindex="0"
          role="button"
          :aria-label="'UserCard function in frontend/App.tsx'"
          @click="selectNode('UserCard', 'function', 'frontend/App.tsx:4', 'TSX component importing User and calling formatName')"
          @keydown.enter="selectNode('UserCard', 'function', 'frontend/App.tsx:4', 'TSX component importing User and calling formatName')"
          style="cursor: pointer;"
        >
          <rect x="630" y="120" width="110" height="50" rx="6" fill="#1e293b" stroke="#f59e0b" stroke-width="2" />
          <text x="685" y="150" fill="#f8fafc" text-anchor="middle" font-size="12" font-family="monospace">UserCard</text>
        </g>
      </g>
    </svg>

    <!-- Node Inspector Box -->
    <div v-if="selected" style="margin-top: 0.75rem; padding: 0.75rem; border: 1px solid var(--vp-c-border); border-radius: 4px; background: var(--vp-c-bg);">
      <div style="font-weight: 600; font-size: 0.875rem;">{{ selected.name }} <span style="font-size: 0.75rem; color: var(--vp-c-brand-1);">({{ selected.kind }})</span></div>
      <div style="font-size: 0.75rem; color: var(--vp-c-text-2); margin-top: 0.25rem;">Defined in: <code>{{ selected.file }}</code></div>
      <div style="font-size: 0.75rem; margin-top: 0.25rem;">{{ selected.desc }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const selected = ref<{ name: string; kind: string; file: string; desc: string } | null>({
  name: 'UserService',
  kind: 'class',
  file: 'backend/services/user_service.py',
  desc: 'Subclass of BaseService with get_user and delete_user',
})

function selectNode(name: string, kind: string, file: string, desc: string) {
  selected.value = { name, kind, file, desc }
}
</script>
