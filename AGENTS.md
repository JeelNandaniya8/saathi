# Saathi agent guidance

Saathi is a privacy-first student workspace built with Flask, PostgreSQL, vanilla JavaScript and Gemini. Read README.md and the relevant code before changing behaviour. Preserve existing features and EN/GU/HI support. The live site is not a test database.

## Product standard
- Optimize for a student completing a real task: clarity, calm, speed, accessibility and trust. Visual polish must improve comprehension and control. Do not claim that colour, animation or a premium aesthetic alone causes purchases; validate choices with users and outcomes.
- Treat Apple-level care as attention to typography, hierarchy, responsiveness, motion, feedback, consistency and edge cases. Keep Saathi's own identity. Avoid copying another product's protected visual assets.
- For UI changes, use the `saathi-design-review` skill. For persistence or async flows, use `saathi-trust-flows`. For release claims, use `saathi-release-review`.

## Architecture and safety
- Backend routes, validation, authorization and storage live in Python modules including app.py; signed-in pages use chat.html/dashboard.html and vanilla JS. Inspect existing controllers before editing. study-desk.css owns the signed-in composition and semantic themes; workspace-hub.css owns shared tool controls. Follow docs/STUDENT_WORKSPACE_UI.md.
- Keep Gemini, database, email, billing and scheduler secrets server-side. Never put keys, private content, credentials or real student data in commits, prompts, logs or screenshots. Use .env.example for variable names only.
- Maintain account ownership checks, CSRF/session protections, privacy toggles, consent, attachment isolation and service-worker API no-cache rules. Do not turn on checkout or alter billing modes as a side effect of UI work.
- User-facing AI and wellbeing claims must match observed capabilities. Do not imply medical care, guaranteed reminder delivery or that an unsaved AI response was saved.
- Migrations are numbered, transactional and idempotent. Use only a disposable TEST_DATABASE_URL ending in _test for database tests; back up before production migrations.

## Work process
1. Reproduce the problem or document the intended user flow and acceptance criteria. Inspect the current implementation and related tests.
2. Make the smallest coherent change across the actual flow. Check loading, empty, success, error, retry and cancellation states; preserve drafts and attachments.
3. Validate with focused tests, then applicable gates: `python -m py_compile app.py`, `pytest -q`, `bash scripts/check_javascript.sh`. CI also runs `node tests/workspace_browser.cjs` with Playwright and a separate `SAATHI_UI_REVIEW=1` pass. See .github/workflows/ci.yml for exact setup.
4. For UI, inspect desktop and mobile screenshots including 1280, 768, 390, 360 and 320px, light/dark, EN/GU/HI, short viewports, keyboard and reduced motion where applicable. Synthetic browser fixtures do not prove real-device behaviour.
5. State exact observed results and limitations. Never say “fixed”, “saved”, “deployed” or “10/10” on the basis of code changes alone.

## Production and release
- Render blueprint is render.yaml: build `pip install -r requirements.txt`, start `gunicorn --worker-class gthread --workers 1 --threads 8 --timeout 120 app:app`, health `/api/health`. Auto-deploy may occur from main; review production impact before merging.
- Keep `COOKIE_SECURE=true`, `FLASK_DEBUG=false`; secrets belong in Render settings. Never use production as a test fixture.
- Before deployment with schema changes, arrange a PostgreSQL backup. After deploy, verify health, the actual release identifier from current code, protected source paths and read-only smoke test `python scripts/smoke_test.py https://saathi-md5w.onrender.com`. The README may contain stale release labels; do not hardcode one here.
- Live AI, Classroom, reminders, payment and device-specific flows require their own authorized end-to-end checks. Label untested flows explicitly.
