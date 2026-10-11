import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'Synapse',
  description: 'Local-first Repository Intelligence Engine for codebases',
  cleanUrls: true,
  base: '/',
  head: [
    ['meta', { name: 'theme-color', content: '#d97706' }],
    ['link', { rel: 'icon', type: 'image/svg+xml', href: '/favicon.svg' }],
  ],
  themeConfig: {
    siteTitle: 'synapse',
    logo: false,
    nav: [
      { text: 'Overview', link: '/' },
      { text: 'Installation', link: '/getting-started/installation' },
      { text: 'Quickstart', link: '/getting-started/quickstart' },
      { text: 'Concepts', link: '/concepts/how-synapse-works' },
      { text: 'Guides', link: '/guides/index-a-repository' },
      { text: 'Reference', link: '/reference/cli/overview' },
    ],
    sidebar: {
      '/': [
        {
          text: 'Getting Started',
          items: [
            { text: 'Overview', link: '/' },
            { text: 'Installation', link: '/getting-started/installation' },
            { text: 'Quickstart', link: '/getting-started/quickstart' },
          ],
        },
        {
          text: 'Core Concepts',
          items: [
            { text: 'How Synapse Works', link: '/concepts/how-synapse-works' },
            { text: 'The Index & State', link: '/concepts/the-index' },
            { text: 'Symbols & Identifiers', link: '/concepts/symbols-and-ids' },
            { text: 'References & Resolution', link: '/concepts/references-and-resolution' },
            { text: 'Knowledge Graph', link: '/concepts/graph' },
            { text: 'Incremental Indexing', link: '/concepts/incremental-indexing' },
            { text: 'Determinism', link: '/concepts/determinism' },
          ],
        },
        {
          text: 'Guides',
          items: [
            { text: 'Indexing a Repository', link: '/guides/index-a-repository' },
            { text: 'Keeping the Index Current', link: '/guides/keep-the-index-current' },
            { text: 'Inspecting Symbols', link: '/guides/inspecting-symbols' },
            { text: 'Generating Context for LLMs', link: '/guides/context-generation' },
            { text: 'Exporting Data', link: '/guides/exporting-data' },
            { text: 'Exclusions & File Limits', link: '/guides/exclusions-and-limits' },
            { text: 'Index Recovery', link: '/guides/index-recovery' },
          ],
        },
        {
          text: 'Use Cases',
          items: [
            { text: 'Codebase Onboarding', link: '/use-cases/onboarding' },
            { text: 'Impact Analysis & Refactoring', link: '/use-cases/impact-analysis' },
            { text: 'AI Assistant Context', link: '/use-cases/ai-context' },
            { text: 'Architecture Snapshots', link: '/use-cases/architecture-snapshots' },
          ],
        },
        {
          text: 'CLI Reference',
          items: [
            { text: 'CLI Overview', link: '/reference/cli/overview' },
            { text: 'synapse init', link: '/reference/cli/init' },
            { text: 'synapse index', link: '/reference/cli/index' },
            { text: 'synapse status', link: '/reference/cli/status' },
            { text: 'synapse search', link: '/reference/cli/search' },
            { text: 'synapse inspect', link: '/reference/cli/inspect' },
            { text: 'synapse context', link: '/reference/cli/context' },
            { text: 'synapse export', link: '/reference/cli/export' },
            { text: 'Exit Codes', link: '/reference/cli/exit-codes' },
          ],
        },
        {
          text: 'Technical Reference',
          items: [
            { text: 'Storage Schema', link: '/reference/storage-schema' },
            { text: 'JSON Output Specifications', link: '/reference/json-output' },
            { text: 'Exports (JSON, MD, ZIP)', link: '/reference/exports' },
            { text: 'Configuration', link: '/reference/configuration' },
            { text: 'Default Exclusions', link: '/reference/exclusions' },
            { text: 'Supported Languages', link: '/reference/languages' },
            { text: 'Error Messages', link: '/reference/error-messages' },
          ],
        },
        {
          text: 'Project Information',
          items: [
            { text: 'Known Limitations', link: '/limitations' },
            { text: 'Troubleshooting', link: '/troubleshooting' },
            { text: 'FAQ', link: '/faq' },
            { text: 'Cheat Sheet', link: '/cheatsheet' },
            { text: 'Contributor Architecture', link: '/architecture' },
            { text: 'License', link: '/license' },
          ],
        },
      ],
    },
    search: {
      provider: 'local',
    },
    outline: {
      level: [2, 3],
      label: 'On this page',
    },
    socialLinks: [
      { icon: 'github', link: 'https://github.com/Piyushgarg06/Synapse' },
    ],
  },
})
