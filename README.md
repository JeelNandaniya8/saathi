# Saathi

Saathi is a responsive Flask and PostgreSQL workspace for AI conversations, study planning, reminders, habits, private writing and everyday reflection. Google Gemini is the only AI reply provider. Gemini and Brevo keys stay on the server.

Saathi is not a doctor, therapist, emergency service or monitoring system. AI replies and reminder delivery can be wrong or fail, so important information and schedules need an independent check.

## What works

- email verified signup, login, logout and hashed password reset codes
- separate conversations with search, rename, pin, archive, delete and pagination
- Gemini replies using limited recent context and only user-approved memory
- task creation, editing, completion and deletion
- once, daily and weekly reminders with edit, snooze, pause and completion
- optional reminder email delivery through a protected scheduler
- habits with local-day completion, pause, edit, deletion and streaks
- private journal creation, search, editing and deletion
- private mood and energy check-ins
- English, Gujarati and Hindi workspace preference and AI reply preference
- consent-based trusted-contact invitations with clear private-data boundaries
- account profile, password, JSON export and permanent deletion controls
- privacy, terms, AI limitations, support, SEO, PWA and custom error pages
- numbered, transactional and idempotent PostgreSQL migrations

Plus and Family pricing is visible only as **Coming Soon**. Checkout is disabled. No request can charge a user or change a plan. Real billing must wait for an adult-owned verified business, payment gateway, tax, legal and KYC setup.

## Architecture

```text
Browser
  -> same-origin Flask pages and JSON APIs
      -> PostgreSQL for account and workspace records
      -> Google Gemini for chat replies only
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
| `chat.html` | Full-page conversation workspace |
| `dashboard.html` | Planner, reminders, habits, journal, check-ins, memory and account |
| `privacy.html`, `terms.html`, `limitations.html` | Public policy pages |
| `support.html` | Rate-limited feedback form |
| `manifest.webmanifest`, `service-worker.js`, `offline.html` | Installable offline shell |
| `tests/` | Backend, migration, security and frontend structure checks |

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
| `CRON_SECRET` | reminder email | long random value protecting the scheduler route |
| `FLASK_DEBUG` | optional | keep `false` outside local development |
| `PORT` | optional | hosting platform port |

The VAPID names in `.env.example` are reserved for a future web-push implementation and are not currently used.

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

The automated suite covers public source blocking, security headers, CSRF, disabled checkout, migrations, legacy history preservation, reminder recurrence, habit streaks, Gemini context limits, language context, HTML IDs, service-worker privacy and forbidden-provider scanning.

## Production deployment

Build command:

```bash
pip install -r requirements.txt
```

Start command:

```bash
gunicorn app:app
```

Deployment checklist:

1. Back up PostgreSQL.
2. Configure all required environment variables in the hosting dashboard.
3. Keep `COOKIE_SECURE=true` and `FLASK_DEBUG=false`.
4. Deploy the reviewed commit.
5. Confirm `GET /api/health` returns `{"status":"ok"}`.
6. Confirm `/app.py`, `/README.md` and `/requirements.txt` return 404.
7. Test signup, OTP, login, chat and logout with test accounts.
8. Test conversation ownership with two separate accounts.
9. Test tasks, reminders, habits, journal, language, export and deletion.
10. Review server logs without copying secrets into tickets or screenshots.

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
- keep dependency ranges reviewed and update them deliberately
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
- Plus document/image study tools are planned, not implemented
- closed-browser web push is not implemented
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
