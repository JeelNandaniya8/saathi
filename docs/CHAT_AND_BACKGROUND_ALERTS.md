# Conversational saves and controlled context

Signed-in chat asks for missing details and can propose one task, general reminder, note, habit, journal entry, check-in or general memory per reply. Explicit “Add task: …”, “Save note: …” and daily/weekly habit commands can create labelled previews without any AI request, including Gujarati/Hindi task/note prefixes. Ambiguous dates and ordinary conversation use AI. Model-generated previews use the same reply without a second AI call. The user reviews editable fields and presses Save. Memory additionally needs explicit future-use consent. A message-owned receipt makes confirmation retries once-only. Clinical routines and health profiles retain their separate review/consent flow.

Chat context defaults off for Planner tasks, general reminders and selected Classroom assignments. The chat context control independently enables each source. Only up to 20 account-owned records per source are sent, with text limits; source labels accompany the reply. Revocation affects future replies, not earlier saved answers. File-only replies exclude this workspace context. Notes are never read automatically. Consents and save receipts are included in account export and removed through account deletion.

# Free general background alerts

The existing public-repository Actions workflow has a final general-alert step using the already configured Classroom scheduler credential. Server-side `BACKGROUND_ALERTS_ENABLED=true` gates its separate endpoint. Both the initial query and atomic claim exclude medication schedules, including digests and legacy general reminders explicitly mentioning medicine/insulin/injections, regardless of the clinical beta flag. This endpoint never calls medication scheduling, sends emails, or uses AI.

Configure matching VAPID public/private keys and an HTTPS or mailto contact subject on Render. Do not rotate a working pair casually: existing devices must resubscribe after key rotation. Users enable notifications individually in Account and can send a private test alert. Provider acceptance is not physical receipt. No reminder details are sent to the lock screen.

Account shows unverified/stale scheduler status after 45 minutes and the latest failed device delivery. The schedule runs roughly every 15 minutes, with a maximum of 10 deliveries per dispatch; GitHub/Render free infrastructure can delay or drop runs. It is best-effort, unsuitable for time-critical medication or emergency alerts. Existing protected `CRON_SECRET` delivery is unchanged.

On a permitted Android device, enable alerts, send a test, lock the device and observe the alert. On iPhone, install the web app to Home Screen and enable alerts from there. Then schedule a general reminder, close the app, and verify the actual locked-device notification. Repeat after disabling permission and reconnecting. These physical checks cannot be replaced by automated server tests.
