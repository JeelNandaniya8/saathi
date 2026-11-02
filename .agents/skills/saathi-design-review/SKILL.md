---
name: saathi-design-review
description: Design or review Saathi's UI, visual system, mobile layouts, onboarding, chat, dashboard or interaction details using student behaviour, accessibility and measurable usability. Use for UI redesigns and visual polish, not backend-only work.
---

# Saathi design review

1. Identify the target student, job, context and current screen. Inspect the actual HTML, CSS, JS, screenshots and docs/STUDENT_WORKSPACE_UI.md. Preserve the existing right-side history, one composer and Saathi identity unless the user requests change.
2. Describe the intended hierarchy in one sentence: what should be noticed first, what action follows, and what feedback confirms it. Prefer progressive disclosure, legible typography, restrained colour, consistent spacing and clear affordances. Use colour for meaning and hierarchy, never as the sole carrier of meaning.
3. Define design tokens for surfaces, text, accent, semantic states, spacing, radius, typography and motion. Check light/dark and English/Gujarati/Hindi native-script rendering. Avoid decorative gradients, unnecessary shadows and motion that compete with reading or studying.
4. Make all actions understandable: label them, keep primary action obvious, show actual status and recovery path. Cover empty, loading, success, partial, error, retry, offline and keyboard states. Preserve draft and attachment continuity.
5. Check mobile widths 320, 360, 390 and 768px, desktop 1280px and a 520px-high viewport. Verify touch targets, focus order, contrast, zoom, reduced motion, screen reader names and physical keyboard/upload where available. Use existing browser fixtures, then inspect screenshots rather than trusting assertions alone.
6. When choosing among visual options, state the hypothesis and test it with real users: task completion, time to first useful action, confusion points, return use and willingness to pay. Do not equate aesthetic preference with conversion. Keep brand language calm and honest.
7. Deliver changed files, screenshots or evidence, exact checks, unresolved device/live gaps, and one next experiment. Do not claim universal appeal or “best ever” without comparative evidence.
