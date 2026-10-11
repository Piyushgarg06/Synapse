# Synapse Documentation Design System

This document specifies the design tokens, visual identity, and typography rationale for the Synapse documentation site.

---

## 1. Visual Identity Rationale

Synapse derives its visual language directly from the terminal, Git DAGs, and structured syntax graphs. Instead of decorative gradients or neon glows, the interface emphasizes high-contrast typography, crisp structural borders, and calm neutral surfaces.

- **Palette rationale**: Neutral slate surfaces paired with a focused amber/orange accent (`#d97706` / `#f59e0b`) reflect build checkpoints and terminal alerts without relying on clichéd purple/indigo gradients.
- **Typography rationale**: System variable sans-serif body type ensures sub-second render times with zero layout shift; monospace tabular numerals ensure numeric data in tables and CLI line numbers align perfectly.
- **Motion rationale**: Animations exist strictly to communicate state changes (tab shifts, copy confirmations, graph exploration) with durations capped below 300ms.

---

## 2. Design Tokens (CSS Custom Properties)

```css
:root {
  /* Surface Colors - Light */
  --syn-bg: #ffffff;
  --syn-surface: #f8fafc;
  --syn-surface-raised: #f1f5f9;
  --syn-border: #e2e8f0;
  --syn-border-focus: #94a3b8;
  --syn-text: #0f172a;
  --syn-text-muted: #64748b;

  /* Accent & Status */
  --syn-accent: #d97706;
  --syn-accent-hover: #b45309;
  --syn-accent-light: #fef3c7;
  --syn-success: #16a34a;
  --syn-error: #dc2626;

  /* Typography */
  --syn-font-sans: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --syn-font-mono: ui-monospace, "SF Mono", Monaco, "Cascadia Code", "Roboto Mono", monospace;
  
  /* Fluid Type Scale */
  --syn-text-xs: clamp(0.75rem, 0.7rem + 0.25vw, 0.8125rem);
  --syn-text-sm: clamp(0.875rem, 0.8rem + 0.35vw, 0.9375rem);
  --syn-text-base: clamp(1rem, 0.95rem + 0.25vw, 1.0625rem);
  --syn-text-lg: clamp(1.125rem, 1.05rem + 0.35vw, 1.25rem);
  --syn-text-xl: clamp(1.25rem, 1.15rem + 0.5vw, 1.5rem);
  --syn-text-2xl: clamp(1.5rem, 1.35rem + 0.75vw, 1.875rem);

  /* Spacing */
  --syn-space-1: 0.25rem;
  --syn-space-2: 0.5rem;
  --syn-space-3: 0.75rem;
  --syn-space-4: 1rem;
  --syn-space-6: 1.5rem;
  --syn-space-8: 2rem;
  --syn-space-12: 3rem;

  /* Geometry */
  --syn-radius-sm: 4px;
  --syn-radius-md: 6px;
  --syn-radius-lg: 8px;

  /* Motion */
  --syn-ease-out: cubic-bezier(0.16, 1, 0.3, 1);
  --syn-duration-fast: 150ms;
  --syn-duration-normal: 250ms;
}

.dark {
  /* Surface Colors - Dark */
  --syn-bg: #0b0f19;
  --syn-surface: #111827;
  --syn-surface-raised: #1f2937;
  --syn-border: #374151;
  --syn-border-focus: #6b7280;
  --syn-text: #f9fafb;
  --syn-text-muted: #9ca3af;

  /* Accent & Status */
  --syn-accent: #f59e0b;
  --syn-accent-hover: #fbbf24;
  --syn-accent-light: #78350f;
  --syn-success: #22c55e;
  --syn-error: #ef4444;
}
```

---

## 3. Reduced Motion Support

When `prefers-reduced-motion: reduce` is detected or the user toggles off motion, all transitions and animations instantly resolve to their final static values (`transition-duration: 0.01ms; animation-duration: 0.01ms;`).
