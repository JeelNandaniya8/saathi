# Saathi

Saathi is a responsive Flask and PostgreSQL workspace for AI conversations, study planning, reminders, habits, private writing and everyday reflection. Google Gemini is the only AI reply provider. Gemini and Brevo keys stay on the server.

Saathi is not a doctor, therapist, emergency service or monitoring system. AI replies and reminder delivery can be wrong or fail, so important information and schedules need an independent check.

## What works

- email verified signup, explicit browser-session or 30-day login, current-session logout, all-device logout and hashed password reset codes
- separate conversations with immediate descriptive titles, recent previews, search, rename, pin, archive, delete and pagination
- low-latency Gemini response streaming with live Markdown, UTF-8 Gujarati/Hindi support, an in-composer Stop control and retry-safe final persistence
- Gemini replies using limited recent context and only user-approved memory
- real PDF, JPG, PNG and WebP chat attachments with server validation, private storage and Gemini analysis
- bounded per-page PDF text grounding, verified page chips and an optional file-only answer mode
- eight server-validated AI modes: Talk it through, Normal, Explain simply, Deep study, Summarise, Quiz me, Flashcards and Study plan
- drag, drop and clipboard image attachment with preview, upload status, cancellation and retry-safe request IDs
- reply actions for simpler, deeper, example and quiz follow-ups
- persistent quiz answers and flashcard review progress across page reloads
- safe Markdown rendering for headings, bold text, lists, tables, links and code blocks
- text download plus a branded Print / Save as PDF conversation export with user messages kept on the right
- reviewed chat actions that save a response as a Planner task or user-scheduled reminder
- privacy-safe AI cost records containing provider token counts, mode and attachment count without duplicating message or file content
- task creation, editing, completion and deletion
- once, daily and weekly reminders with edit, snooze, pause and completion
- optional reminder email delivery through a protected scheduler
- habits with local-day completion, pause, edit, deletion and streaks
- branded confirmation dialogs, accessible mobile bottom sheets and semantic success, info, warning and error notices
- private journal creation, search, editing and deletion
- private mood and energy check-ins, with optional care and reflection shortcuts on Today
- section-aware Dashboard Back/Forward navigation, safe sign-in return paths and independent loading with Retry
- natural heading spacing, readable form fields and keyboard-safe mobile navigation
- user-controlled memory with concise previews and a full View and Edit panel
- English, Gujarati and Hindi workspace preference and AI reply preference
- consent-based trusted-contact invitations with clear private-data boundaries
- account profile, password, JSON export and permanent deletion controls
- privacy, terms, AI limitations, support, SEO, PWA and custom error pages
- numbered, transactional and idempotent PostgreSQL migrations

Checkout is **disabled by default**. Optional Razorpay test mode validates orders without activating real paid access. Live mode requires the verified merchant configuration below; this code release does not enable it. Family remains Coming Soon. Plus passes expire and do not automatically renew.

## September reliability release

- Official Google identity verification replaces the insecure email-only fallback. `GOOGLE_CLIENT_ID` must be configured; otherwise email signup remains available.
- Pending or expired signup requests no longer reserve usernames. The final OTP verification still enforces unique confirmed usernames.
- Validated, owned mock tests hide answers before submission, preserve one scored attempt and enforce a server deadline. Mindmaps fail clearly when AI content is unavailable or malformed.
- Wellbeing tools provide general preparation prompts, optional sounds and comfortable 4-second inhale / 6-second exhale pacing. They do not diagnose, prescribe or promise healing. Reminders use the user’s actual saved schedule.
- Verified payment orders check ownership, amount, capture, signatures and expiry. Webhooks and repeated confirmations are idempotent; full refunds revoke the remaining purchased time.
- Referral rewards require a verified invitee, one day and a completed task or test, capped at 28 days. No automatic reward is issued merely for a Google login.
- Shared readable workspace styling, compact chat sound controls, signup first on mobile, optional completion sounds and name-free scorecards by default.

Migration `015` retires existing sessions **once** because the old Google fallback accepted an email without identity proof. Existing users must sign in again. It does not delete their saved content. Existing finite paid grants are retained; undated legacy upgrades do not count as paid access.

## Optional identity and billing configuration

Set `GOOGLE_CLIENT_ID` to a Google web OAuth client. Add the actual HTTPS site to its authorised JavaScript origins. The app loads the official Google Identity Services button and checks the signed token, audience, issuer, expiry and browser nonce. Third-party Google email addresses use email verification unless already linked.

Keep `SAATHI_BILLING_MODE=disabled` until checkout setup has been reviewed. Test mode requires matching `rzp_test_` credentials plus `RAZORPAY_WEBHOOK_SECRET`. Live mode additionally requires `MERCHANT_VERIFIED=true` and matching live credentials for the verified business; no test transaction grants real access. Subscribe the webhook URL `/api/payment/webhook` to `payment.captured` and `payment.refunded`, and use its separately generated signing secret. Do not paste real keys into source files.

The current products are fixed passes: ₹199 for 30 days or ₹1,499 for 365 days, without automatic renewal. Free accounts receive 1 mock test and 2 mindmaps daily; paid accounts receive 20 of each. Existing attachment size and daily limits still apply. Publish the merchant’s refund, tax and support terms before enabling live checkout.

`GEMINI_FAST_MODEL` defaults to `gemini-3.5-flash-lite` for everyday chat; `GEMINI_MODEL` defaults to `gemini-3.6-flash` for deeper study. Both can be set to a Gemini model available to your project. Connections are reused within each worker thread, and streamed UTF-8 text is decoded incrementally. Cold starts, database location, provider availability and free-tier quotas still affect response time.

CI runs isolated PostgreSQL integration tests in addition to unit and browser behaviour checks. Locally, set `TEST_DATABASE_URL` to a disposable localhost database whose name ends in `_test` to include these tests; use `PGPASSWORD` separately if needed. Never point tests at production.

## Architecture

```text
Browser
  -> same-origin Flask pages and JSON APIs
      -> PostgreSQL for account and workspace records
      -> Google Gemini for chat and study documents
      -> Brevo for verification, reset and opted-in reminder email
```

The service worker never caches API responses. Repository files such as `app.py`, `README.md` and `requirements.txt` are not public web assets.

## Project structure

| Path | Purpose |
| --- | --- |
| `app.py` | Flask routes, validation, security, PostgreSQL, Gemini and Brevo |
| `migrations/` | Ordered SQL migrations recorded in `schema_migrations` |
| `saathi.html` | Public landing page |
| `account.html` | Signup, OTP, login and password reset |
| `chat.html` | Full-page conversation workspace with AI modes, study actions and photo/PDF attachments |
| `dashboard.html` | Planner, reminders, habits, journal, check-ins, memory and account |
| `privacy.html`, `terms.html`, `limitations.html` | Public policy pages |
| `support.html` | Rate-limited feedback form |
| `manifest.webmanifest`, `service-worker.js`, `offline.html` | Installable offline shell |
| `tests/` | Backend, migration, security and frontend structure checks |
| `.github/workflows/ci.yml` | Automatic tests for every main-branch update and pull request |
| `render.yaml` | Reviewable Render service and environment blueprint |
| `scripts/` | JavaScript validation and read-only live smoke checks |

## Environment variables

Copy names from `.env.example`. Never commit real values.

| Variable | Required | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | yes | PostgreSQL connection URL, including required SSL options |
| `FLASK_SECRET_KEY` | yes | stable long random value for signed sessions and rate-limit hashing |
| `GEMINI_API_KEY` | for chat | server-side Google Gemini key |
| `BREVO_API_KEY` | for email | Brevo transactional email key |
| `BREVO_SENDER_EMAIL` | for email | verified Brevo sender address |
| `APP_BASE_URL` | production | canonical HTTPS site URL without a trailing slash |
| `COOKIE_SECURE` | production | `true` on HTTPS; `false` only for local HTTP |
| `CRON_SECRET` | scheduled reminders | long random value protecting the scheduler route |
| `FLASK_DEBUG` | optional | keep `false` outside local development |
| `PORT` | optional | hosting platform port |

Optional Web Push requires `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY` and `VAPID_SUBJECT` (a `mailto:` contact controlled by the site operator). Generate the pair locally with `python scripts/generate_push_keys.py`, and place the output only in your server environment. Keep the private key out of Git, chat messages and logs. Preserve the same key pair across deployments; changing it requires browsers to subscribe again.

Schedule an authenticated `POST /api/cron/reminders` with `X-Cron-Secret` every minute using your server-side scheduler. Email and Web Push use this same endpoint. Web Push works without Brevo, but still requires the scheduler. Use an awake production server for timely delivery; a sleeping free instance can delay reminders. Browser and operating-system delivery is best effort. Do not use it for emergencies.

Users enable alerts in Dashboard → Account → Background reminder alerts. Permission is requested only from their click. Supported browsers receive a generic alert even with the Saathi tab closed; the private reminder title and note stay in the app. On iPhone/iPad, open an installed Home Screen web app on a supported OS. Disabling alerts or signing out stops that device's subscription; all-device logout and password reset invalidate existing subscriptions through the account session version. Delivery records prevent repeat sends, retry temporary failures up to five times, and remove expired subscriptions.

Quick notes are private account records, available from the chat and dashboard sidebars. They support up to 100 notes of 10,000 characters, explicit Save, search, edit, deletion, retry-safe creation and conflict detection. They are included in account export and deleted with the account. Notes are not automatically sent to the AI or shared through Family Bridge. Google profile photos are accepted only from a verified Google credential; missing or unavailable photos fall back to initials. Appearance follows the device preference until a user chooses light/dark mode, and the choice carries across public, account and workspace pages.

## Local setup on Windows PowerShell

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
$env:DATABASE_URL = "your-postgresql-url"
$env:FLASK_SECRET_KEY = "replace-with-a-long-random-value"
$env:GEMINI_API_KEY = "your-gemini-key"
$env:BREVO_API_KEY = "your-brevo-key"
$env:BREVO_SENDER_EMAIL = "verified-sender@example.com"
$env:APP_BASE_URL = "http://127.0.0.1:5000"
$env:COOKIE_SECURE = "false"
$env:FLASK_DEBUG = "true"
python app.py
```

Open `http://127.0.0.1:5000`.

## Local setup on macOS or Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
export DATABASE_URL="your-postgresql-url"
export FLASK_SECRET_KEY="replace-with-a-long-random-value"
export GEMINI_API_KEY="your-gemini-key"
export BREVO_API_KEY="your-brevo-key"
export BREVO_SENDER_EMAIL="verified-sender@example.com"
export APP_BASE_URL="http://127.0.0.1:5000"
export COOKIE_SECURE="false"
export FLASK_DEBUG="true"
python app.py
```

## Database migrations

Migrations run automatically at application startup when `DATABASE_URL` exists. The runner:

- locks migration execution across Gunicorn workers
- runs numbered SQL files in order
- records each successful version once
- rolls back the failing migration
- preserves existing users and legacy messages
- moves legacy messages without a conversation into one **Previous conversation** per user

Create a PostgreSQL backup or restore point before each production migration. See `migrations/README.md` for rollback guidance.

## Testing

Tests mock Gemini and do not send real email or AI requests.

```bash
python -m py_compile app.py
pytest -q
```

JavaScript syntax checks:

```bash
for page in account.html chat.html dashboard.html saathi.html support.html; do
  sed -n '/<script>/,/<\/script>/p' "$page" | sed '1d;$d' | node --check -
done
node --check service-worker.js
```

The same checks run automatically through GitHub Actions. To verify an already
deployed public release without changing data:

```bash
python scripts/smoke_test.py https://saathi-md5w.onrender.com
```

The automated suite covers public source blocking, security headers, CSRF, session duration choice, all-device logout, signup and password-reset OTP expiry boundaries, branded destructive-action confirmations, printable conversation exports, disabled checkout, migrations, legacy history preservation, reminder recurrence, habit streaks, attachment signatures and limits, AI-mode validation, Gemini multimodal payloads, language context, HTML IDs, service-worker privacy and forbidden-provider scanning.

## Production deployment

Build command:

```bash
pip install -r requirements.txt
```

Start command:

```bash
gunicorn --timeout 120 app:app
```

`render.yaml` records the intended Render build, start, health and environment
configuration. Secret values remain `sync: false` or generated by Render and
must never be copied into the YAML file.

Deployment checklist:

1. Back up PostgreSQL.
2. Configure all required environment variables in the hosting dashboard.
3. Keep `COOKIE_SECURE=true` and `FLASK_DEBUG=false`.
4. Deploy the reviewed commit.
5. Confirm `GET /api/health` returns status `ok` and release `2026-09-09-workspace-navigation`.
6. Confirm `/app.py`, `/README.md` and `/requirements.txt` return 404.
7. Test signup, OTP expiry, temporary and 30-day login, chat, current-session logout and all-device logout with test accounts.
8. Test conversation ownership with two separate accounts.
9. Test tasks, reminders, habits, journal, language, export and deletion.
10. Attach a small test image and PDF, verify streaming, Stop, file-only answers and confirmed page chips, then confirm another account cannot open their attachment URLs.
11. Run `python scripts/smoke_test.py https://saathi-md5w.onrender.com`.
12. Review server logs without copying secrets into tickets or screenshots.

## Reminder email scheduler

Users must choose **Email and browser** on a reminder. Email does not run merely because a reminder exists.

Configure a secure scheduler to send this request every five minutes:

```text
POST https://your-domain.example/api/cron/reminders
X-Cron-Secret: the exact CRON_SECRET value
```

The scheduler records one delivery per reminder schedule, retries failed claims after a delay and never exposes provider responses. Keep `CRON_SECRET` only in the hosting scheduler and server environment. A disabled or misconfigured scheduler means email reminders will not be delivered.

## Security checklist

- use a stable production `FLASK_SECRET_KEY`
- rotate any key that was ever committed or shared
- keep database, Gemini, Brevo and cron values out of Git and browser code
- use HTTPS and secure cookies
- keep the committed dependency pins reproducible and merge automated update PRs only after CI passes
- review dependency version updates deliberately instead of bypassing CI
- review migrations before deployment and back up first
- check logs for errors, but never log OTPs, passwords, API keys or provider bodies
- do not enable payment buttons until verified billing is legally and technically ready

## Rollback

Application rollback:

1. Stop the new deployment if health checks fail.
2. Redeploy the last known-good Git commit.
3. Do not delete rows from `schema_migrations` to hide a failure.
4. If a migration changed data unexpectedly, restore the pre-deploy database backup into a safe database first and verify it before changing production.

Forward fixes are safer than hand-written destructive rollback SQL for additive migrations. Never run `DROP TABLE`, broad `DELETE` or schema rollback commands on production without a verified backup.

## Honest limitations

- checkout and subscriptions are not active
- photo and PDF analysis is available in a limited free beta; richer document workflows and larger Plus limits are planned
- background Web Push requires VAPID configuration, an authenticated scheduler and device permission; browser/OS delivery is best effort
- email reminders require a separately configured scheduler and can still fail
- Family Bridge currently records invitations and consent boundaries; it does not expose or deliver another user's private data
- translations cover the most important workspace navigation and AI reply preference, not every sentence on every page
- automated tests do not replace a staging test against the configured PostgreSQL, Gemini and Brevo services
- Saathi can make mistakes and cannot replace qualified professional or emergency help

## Troubleshooting

- `configuration_required` from `/api/health`: set `DATABASE_URL`.
- Login appears to work but immediately ends: use a stable `FLASK_SECRET_KEY` and correct HTTPS cookie setting.
- No verification email: confirm the Brevo key and verified sender, then check Brevo logs.
- Chat unavailable: confirm `GEMINI_API_KEY` and inspect server logs for the status only, not provider bodies.
- Reminder email absent: confirm the reminder has email enabled, `CRON_SECRET` matches and the scheduler is actually calling the route.
- Migration failure: read the first migration error, keep the transaction rolled back and restore the previous deploy while preparing a forward fix.

Streaming recovery release: the browser reads UTF-8 chunks directly with Fetch, including regenerated answers. Stop and connection errors preserve received text on the current screen with an unsaved notice. Retries reuse the request ID. Partial replies are not persisted. The Render start command uses four threads so a long response does not monopolize the sole worker. Existing manually managed services may need their Start Command updated in Render. Verify a logged-in streaming request in browser Network timing after deployment; local chunk tests cannot prove CDN delivery.

Workspace navigation release (`2026-09-09-workspace-navigation`): Dashboard section changes now create history entries, while successful sign-in replaces the login entry. Valid sessions revisiting `/account` return to the workspace. Each dashboard section loads independently and can recover through Retry; failed requests do not trigger logout unless the server returns 401. Private pages are marked no-store and streaming responses retain no-transform. Heading tracking uses normal spacing across the workspace and public pages. Care shortcuts remain optional; journal entries and check-ins are not sent to the AI.

Regression checks run the production navigation and request functions against a DOM/history model, including Today → Planner/Reminders/Memory → Back → Forward, preserved drafts, deep links, mobile focus, missing notifications, connection failures, Retry and sign-in history. After deployment, repeat these paths in a real signed-in browser at desktop and mobile widths, including refreshed deep links and Stop during a Gujarati reply. The automated model does not verify rendered layout or live proxy streaming.
