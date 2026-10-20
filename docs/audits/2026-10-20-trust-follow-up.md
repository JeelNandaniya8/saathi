# Reliability follow-up — 20 October 2026

Scope: preserve the current Flask/vanilla-JavaScript/Gemini/Render stack and the
existing limits. No new product features, models, database schema or paid
infrastructure are introduced.

## Reproduced before repair

1. Two identical study-generation calls made while allowance was unresolved
   issued **two POSTs instead of one**, with different job IDs. The new
   `study_job_races.cjs` assertion failed `2 !== 1` before the repair.
2. A resumed mindmap job reported `waiting`, but Dashboard displayed
   **Generating mindmap…**. The new `study_status.cjs` assertion failed on that
   exact mismatch before repair. The mock-test handler had the same callback.
3. Gujarati and Hindi catalogs lacked the transient generation/waiting labels.

## Minimal changes

- Coalesce an identical in-flight study operation before its first allowance
  await. Both callers receive one result and one job ID. The payload is
  snapshotted; separate topics remain separate operations.
- Release the in-flight guard after success or failure. An uncertain retry
  retains its existing request ID; a later deliberate generation gets a new ID.
- Distinguish waiting from generating in Dashboard, with native GU/HI labels.
- Version the changed scripts/catalogs so existing clients receive the repair.

## Acceptance evidence map

All provider failures and exhausted limits below use isolated fixtures, not
production fault injection. Passing CI is engineering evidence, not an
independent live review.

| Gate | Executable coverage | Remaining live requirement |
|---|---|---|
| Planner truth | Critical-journey schemas compare today's tasks, dates and ownership | Fresh signed-in Chat/Planner comparison |
| Durable mindmap | Normal-map save, exact cold link and retry/replay checks | Independent create/reload |
| Reminder semantics | Future snooze, explicit reschedule and timezone/DST checks | Physical notification delivery |
| Exact saved note | Unicode read-back, conflict, exact receipt and replay checks | Independent cold-session save/read |
| Content and readability | DNA direction/correction persistence, vector denominator, math and fitted-map checks | Human content/export review |
| Quota truth | Pending, exhausted, stale, failure and reset/retry checks | Signed-in balance/reset observation |
| Stage/Stop/retry | Exact files/file-only/request ID, cancellation races, job coalescing and native stages | Live Stop/network-failure observation |
| Effective privacy | Paused memory, file-only, refusal, two-account isolation and connected Classroom fixtures | Renewed connected-account payload review |

CI also exercises real Chromium at 1280/768/390/360/320px, light/dark and
EN/GU/HI; synthetic PNG/PDF citations and concrete ten-minute exam-stress
responses are covered by existing regressions.

## Measurement boundaries

- The existing 200-journey PostgreSQL cohort and 100-note receipt cohort are
  staging measurements. Report their actual current-run results and timings;
  never call them production availability or first-word latency.
- New directed authenticated live AI cohort: **not collected**. Secure sign-in
  timed out; no successful authentication is inferred and no credentials were
  read or entered through another channel.
- Production success >=99%, p95 first words <5s, physical-phone keyboard/uploads
  and reminder delivery, and all eight independent live gates remain open.
- Public health, static-asset checks and smoke routes do not replace those gates.
- No production quota exhaustion, artificial keepalive, paid upgrade or model
  switch is used to improve the reported numbers.

The final PR records the exact tested commit and CI run; deployment must match
that tree and pass the public smoke/static-asset checks before being called live.
