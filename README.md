# Saathi

Saathi is a Flask web application for AI conversation, saved history, accounts, email verification, and user-created reminders.

## What is included

- Premium responsive landing page
- Product walkthrough with dashboard and medicine-reminder previews
- Email-verified accounts
- Secure password hashing and cookie sessions
- Saved conversation history
- PostgreSQL-backed reminders
- Complete, snooze, pause, resume, and delete reminder actions
- Optional browser alerts while the dashboard is open
- Google Gemini integration handled only by the Flask server
- Brevo email delivery for verification codes

## Project files

```text
saathi/
├── app.py
├── saathi.html
├── account.html
├── dashboard.html
├── requirements.txt
└── README.md
```

## Required environment variables

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | PostgreSQL connection string, such as a Neon database URL |
| `FLASK_SECRET_KEY` | Long random value used to sign login sessions |
| `GEMINI_API_KEY` | Server-side Google Gemini API key for Saathi chat |
| `BREVO_API_KEY` | Brevo key used to send account verification codes |
| `BREVO_SENDER_EMAIL` | Verified Brevo sender address |
| `COOKIE_SECURE` | Use `true` on HTTPS hosting and `false` for local HTTP testing |
| `FLASK_DEBUG` | Optional. Use `true` only during local development |

Never place real secret values inside `app.py`, HTML, commits, screenshots, or the README.

## Run locally

Create a Python virtual environment and install the dependencies:

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:DATABASE_URL = "your-postgresql-url"
$env:FLASK_SECRET_KEY = "a-long-random-secret"
$env:GEMINI_API_KEY = "your-gemini-key"
$env:BREVO_API_KEY = "your-brevo-key"
$env:BREVO_SENDER_EMAIL = "your-verified-sender@example.com"
$env:COOKIE_SECURE = "false"
$env:FLASK_DEBUG = "true"
python app.py
```

Open `http://localhost:5000`.

## Production deployment

Use this start command on a Python hosting service:

```bash
gunicorn app:app
```

If your host does not automatically install Gunicorn, add it to `requirements.txt` before deployment. Set all required environment variables in the hosting dashboard, keep `COOKIE_SECURE=true`, and never enable debug mode in production.

The database tables are created automatically when the application starts and `DATABASE_URL` is available.

## Reminder behavior

Reminders are stored in PostgreSQL and attached to the signed-in user. The current dashboard checks for due reminders while it is open. Browser alerts also require user permission.

Sending reliable alerts when every Saathi tab is closed requires a background worker or push-notification service. The current UI explains this limitation instead of pretending a closed-browser alert has been delivered.

Medicine reminders only repeat the schedule entered by the user. They do not select medicines, recommend doses, or replace instructions from a qualified healthcare professional.

## Before pushing to GitHub

Run these checks:

```bash
python -m py_compile app.py
```

Confirm that no `.env` file, database URL, session secret, email key, or Gemini key is staged. Then commit:

```bash
git add app.py saathi.html account.html dashboard.html requirements.txt README.md
git commit -m "Upgrade Saathi UI and add account reminders"
git push origin main
```
