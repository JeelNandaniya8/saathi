# Saathi

Saathi is a Flask and PostgreSQL workspace for AI conversations, study planning, user-created reminders, private check-ins and explicit user-controlled memory. Google Gemini is the only AI reply service. Its key stays on the Flask server and is never placed in browser code.

## Included features

### Conversation workspace

- separate conversations for each signed-in user
- safe migration of earlier messages into **Previous conversation**
- new chat, search, automatic titles, rename and delete
- pin, unpin, archive and restore
- text export and 100-message cursor pagination
- date groups, mobile drawer, copy, retry and another reply
- safe plain-text rendering and responsive composer

### Dashboard

- live Today overview
- task planner with priorities and due dates
- once, daily and weekly user-created reminders
- complete, pause, resume, snooze and delete reminder controls
- private mood and energy check-ins with recent averages
- explicit memory items that can be activated, paused or deleted
- profile editing and current-password verified password changes
- complete JSON data export and permanent account deletion
- light and dark appearance, installable app and offline shell

### Security and privacy

- hashed passwords and secure Flask sessions
- Brevo email OTP verification and password reset
- database-backed request limiting across Gunicorn workers
- OTP attempt limits and resend cooldown
- same-origin mutation protection and one-megabyte request limit
- Content Security Policy and browser security headers
- ownership checks and `no-store` API responses
- no automatic memory extraction

## Project files

| File | Purpose |
| --- | --- |
| `app.py` | Flask, PostgreSQL migrations, authentication, Gemini, Brevo and APIs |
| `saathi.html` | Public landing page and walkthrough |
| `account.html` | Sign-up, OTP, login and password reset |
| `dashboard.html` | Complete signed-in workspace |
| `chat.html` | Full-page conversation experience |
| `manifest.webmanifest` | Installable web-app metadata |
| `service-worker.js` | Offline shell and static caching |
| `offline.html` | Honest offline fallback |
| `saathi-icon.svg` | Original Saathi icon |
| `requirements.txt` | Python dependencies |

## Required environment variables

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | PostgreSQL connection string with the SSL options required by the host |
| `FLASK_SECRET_KEY` | A long stable secret for sessions and limiter hashing |
| `GEMINI_API_KEY` | Google Gemini key used only by `app.py` |
| `BREVO_API_KEY` | Brevo transactional email key |
| `BREVO_SENDER_EMAIL` | Verified sender address in Brevo |
| `COOKIE_SECURE` | Keep `true` on HTTPS; use `false` only for local HTTP testing |

Optional variables are `PORT` and `FLASK_DEBUG`. Never commit real secrets.

## Local run

```bash
python -m venv .venv
```

Activate it, then run:

```bash
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`. Set `COOKIE_SECURE=false` only during local HTTP testing.

## GitHub and deployment

1. Extract the complete updated ZIP.
2. Replace the repository files with every extracted file.
3. Commit and push to the branch used by the hosting service.
4. Keep all environment variables configured.
5. Build with `pip install -r requirements.txt`.
6. Start with `gunicorn app:app`.
7. Confirm `/api/health` returns `{"status":"ok"}`.
8. Test sign-up, OTP, login, chat, old history, planner, reminders, check-ins, memory, export and logout.

## Automatic database migration

No manual SQL is required. `app.py` runs idempotent PostgreSQL migrations during startup under a transaction-level advisory lock. It creates the conversation, task, check-in, memory and security tables, adds pin, archive and OTP protection fields and preserves earlier messages. Restarting the app does not duplicate the migration.

## Honest product limits

- Payment settlement is not connected. Choosing Plus or Care records `pending_payment` and does not charge the user.
- Browser reminder notifications work while Saathi is open. Closed-browser delivery needs a separate push service and is not claimed here.
- Saathi never chooses a medicine, dose or treatment. It stores only the reminder entered by the user.
- Check-ins are personal records, not medical or psychological diagnosis.
- AI output can be wrong. Important health, legal and financial information should be checked with a qualified person.
