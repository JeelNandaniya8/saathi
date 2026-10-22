# Live upload startup recovery — 22 October 2026

Baseline: main `65953cc35aca6da397b12114e3698909dfa45f58` (PR81), actually signed in through the secure browser-auth form. No credentials, cookies, tokens or private teacher material were inspected. Two synthetic fixtures were prepared; the PDF had not been sent at reproduction time.

## Before changing code

One synthetic PNG was selected with the real browser file chooser in Normal mode, with file-only enabled. One immediate Send/Stop cycle retained the exact prompt, original file and file-only selection. Independent `GET /api/conversations/113/messages?limit=6` returned zero persisted messages. The browser timing was cancelled, 660ms, first text null. Allowance stayed 5.

One explicit retry failed with `AI_TIMEOUT`: browser measurement `84a405ac-5044-47f7-9720-085c8e3c9b36`, conversation113, created `2026-10-22T09:26:19.201975+00:00`, total **47,754ms**, first text null. It retained prompt/file/file-only, left allowance5, and a second independent message read still returned zero. The recovered PNG incorrectly displayed a PDF badge.

The corresponding Render window contained a study-route startup timeout at `09:26:18.180788Z`: configured `gemini-3.5-flash-lite`, `fast=False`, `stream=True`, recovery exhausted. The paired stream log had headers/first-text null, elapsed45,350ms, attachments1. The code sends Normal attachments to `deep_study`, but its pre-header timeout fallback applied only to fast modes. This reproduces a missing study recovery path; it does not establish why Google's primary request stalled. No HTTP503/AI_BUSY was forced in production.

Before the fix, **8/13 new transport cases failed** (0.33s). A separate recovered-PNG preview regression failed. All are deterministic fixtures with no provider calls or wall-clock sleeps.

## Minimal changes

- Extend the existing one-alternate recovery to the already-supported Flash-Lite models in the study route. First startup read timeout15s, unchanged40s/65s fast/study attempt budgets, maximum two attempts. A received short5xx cooldown still applies; access/quota failures and long/unknown cooldowns are not replayed. Stream consumption stays outside recovery: output is never replayed automatically. Custom study models are not silently downgraded after a timeout.
- Keep full study payload, attachments, file-only system rules, token limit and reasoning configuration through fallback and its three-minute cache. Do not use the compact fast-chat fallback for study work.
- Omit deprecated sampling fields for the documented newer GenerateContent models, retaining older-model configuration and caller payloads. Google says these fields are currently ignored on3.5 Lite and can error on future generations; this separate compatibility cleanup is **not** evidence that sampling caused the observed timeout. [Official API changes](https://ai.google.dev/gemini-api/docs/generate-content/whats-new-gemini-3.6#api_changes_and_parameter_updates); [3.1 Lite multimodal support](https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite).
- Recreate image previews on file retries instead of labelling a PNG as PDF. No stack, schema, plan, quota, provider account or infrastructure change.

## Verification and remaining limits

Targeted local transport/core cases: **139 passed**. Full local backend run before adding the twelve PostgreSQL recovery cases: **764 passed,346 database-dependent skipped** in9.14s. All existing JavaScript checks passed, including the new PNG preview case. PostgreSQL checks cover real multipart PNG/PDF and Normal maps, JSON/stream, timeout/503 fallback, full context equality, completed-request replay, one stored exchange/object/charge and exact reopen. Skips are not passes; the PR must record the exact-candidate CI result.

Independent read-only note38 verification also closed an older evidence gap: original user message669, receipt assistant670 (`kind=note,resource_id=38`), exact UI hyperlink `/chat?note=38`, cold open and reload. Stored title and all four content lines matched the actual original input codepoint-for-codepoint. Two older audit notes share a marker but contain different input codepoints; no note was created, edited or deleted in this check and their origin was not inferred.

The mixed-history browser baseline after reproduction was78attempts,62complete,12errors,4cancelled,56first-text samples; medianfirst-text5827.5ms,p9517926ms. It is not release-specific. The two newly associated rows above have no first text and cannot be discarded from completion reporting.

Post-deployment PNG/PDF citation checks, selected Classroom file permission, actual-phone behavior, notification arrival and independent acceptance remain unverified until observed. Neither the fixture suite nor a small live sample proves production99% success, p95under5s or all-eight-trust-check acceptance. Requests' socket limits are not a hard total wall-clock deadline, and Stop does not certify cancellation of provider work or billing.
