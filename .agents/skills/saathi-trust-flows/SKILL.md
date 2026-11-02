---
name: saathi-trust-flows
description: Implement or audit Saathi saves, notes, tasks, reminders, memory, chat streaming, attachments, Classroom and other async student flows where accurate status, persistence, privacy, retry or cancellation matter.
---

# Saathi trust flows

1. Trace the full route from user gesture through client state, request, authorization, database transaction and read-back. Record exact expected behaviour before changing code.
2. Separate local saving, AI generation, waiting and delivery states. “Saved” requires server confirmation plus an independently readable record with owner, title, destination and state. AI text generation is not proof of a record.
3. Preserve the exact draft, attachments, mode and request identity across retry and Stop. Handle duplicate clicks, out-of-order responses, expired sessions, quota exhaustion and network failure without invented progress or duplicate records.
4. Respect stored source consent and account ownership on every new request. Do not silently fall back from a connected source to fabricated data. Show a recoverable, localized EN/GU/HI error when a source is unavailable.
5. Reminders: snooze only due reminders; future schedule changes require explicit rescheduling. Verify the exact updated record. Do not claim guaranteed delivery from a saved schedule.
6. Add or update focused backend/controller/browser tests for the failure mode, then run relevant checks from AGENTS.md. Use disposable data only. Report observed read-back and what still needs live testing.
