---
name: saathi-release-review
description: Review Saathi pull requests or prepare a release with reproducible tests, UI screenshots, privacy and trust checks, Render deployment verification and evidence-based readiness reporting.
---

# Saathi release review

1. Compare the diff with user-facing acceptance criteria. Inspect touched routes, state controllers, SQL migrations, CSS, localization and existing tests. Prioritize data loss, authorization, misleading receipts and broken mobile flows.
2. Run relevant focused checks and the applicable repo gates in AGENTS.md. Check CI results. For visual work, run desktop/mobile browser checks and inspect generated images for layout, clipping, contrast and actual user hierarchy.
3. Use synthetic fixtures for repeatability; do not present them as evidence of live Gemini, Classroom, email/push, payment or real-device behaviour. Document each untested gate.
4. Before production migration ensure a backup/restore plan. Review Render env variable names without exposing values. Do not enable checkout, change billing or send test reminders to real users during a release check.
5. After an authorized deploy, confirm health and current release, protected paths, read-only smoke test and relevant signed-in flows with authorized test accounts. Diagnose mismatch before declaring success.
6. Return a short evidence table: check, action, observed result, pass/fail/blocked, remaining risk. Give a release recommendation based on evidence, not a numeric score without a defined rubric.
