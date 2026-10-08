# Render startup and release check

The repository still selects the free service. This change does not purchase or activate hosting.
Render documents free-service spin-down after 15 idle minutes and approximately one minute to wake: https://render.com/docs/free . Changing a workspace plan alone does not remove that service limitation.

The reviewed alternative is `render-always-on.yaml.example`: same service, Python/Gunicorn, Neon connection and domain; only the service compute plan changes to Starter. Review current service pricing in Render before applying. Do not create a second service or database. Apply to the existing service only after owner approval and confirm the actual eight-thread start command. Keep a copy of the previous configuration for rollback.

Run `python scripts/measure_latency.py --base-url https://saathi-md5w.onrender.com --samples 5` before and after changing the service. The probe fetches only public health/account assets, never sends an AI prompt or credentials. First sample is reported separately; repeated samples measure warm HTTP response time, not browser LCP or provider generation. Test another first visit after an idle interval. Use Account → Reply performance for authenticated first-text/full-reply measurements from actual user requests; no extra AI calls are needed.

Verify /api/health, login, streamed reply/Stop, reminders cron and rollback readiness. A paid compute plan still cannot guarantee provider latency or notification delivery. Real devices and actual Render configuration remain unverified from this workspace.

## Confirmed service inspection (8 October 2026)

The connected existing Saathi service uses main, autoDeploy=yes, Free compute, `python app.py`, and no configured health-check path. The latest live deployment was c4f5353b (PR #13); logs confirm the Flask development-server warning. The legacy entry point now detects documented RENDER=true and runs the already-loaded WSGI app through Gunicorn, one gthread worker/eight threads/120-second timeout, with debug off and request access logs off (OAuth callback query strings should not enter access logs). Local Flask development remains available. This avoids recreating the service or changing existing secrets. The repository Gunicorn start command also remains supported. Verify the new worker log and deployed SHA after merge.

Recent Render memory samples were approximately 83 MiB; HTTP latency metrics were empty, so they cannot prove user-facing speed. The actual compute plan remains Free. Paid compute and any new paid cron require a separately reviewed cost decision.
