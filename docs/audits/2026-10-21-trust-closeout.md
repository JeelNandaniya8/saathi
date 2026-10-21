# Trust follow-up — 21 October 2026

Baseline: `874c764643b7333d2d19243030c8635ca38fc7f5` (PR74). Scope remains the existing Flask/PostgreSQL/Gemini/Render stack. No provider, paid plan, quota, permission, schema or student feature changes.

## Timing attribution repair

The existing database stores a browser attempt UUID and owned conversation ID, but the recent-timings SELECT returned neither. The earlier live raw-JSON evidence therefore could not identify a particular conversation; source inspection confirms the same five-field projection at this baseline. Returning those two existing fields repairs that read-back gap. The latest eight rows, 100-attempt/30-day retention, ownership checks and percentile denominator remain unchanged.

`request_id` here is a **browser measurement attempt UUID**, not the chat operation/idempotency UUID. Multiple retries in one conversation remain separate measurements. A conversation ID permits association when a controlled conversation has exactly one measured request. These identifiers do not establish release provenance or associate every historical row to a message. No request/reply text is added to the timing response.

The added PostgreSQL regression posts ten distinct measurements across two owned conversations, checks the exact latest-eight values/identifiers, and verifies that a second account receives none. Final CI/deployment results belong in the PR.

## Evidence ledger

| Gate | Available evidence | Remaining live limit |
| --- | --- | --- |
| Planner/today parity | 20 fixture variants across four timezones, duplicate titles and midnight boundaries | No new controlled production parity comparison completed |
| Saved map honesty | Real PostgreSQL receipts, integer IDs, cold object read-back, failed validation rollback and owner isolation | Historical conversation108/title-as-ID is not a verified map object; no new live map was generated |
| Reminder semantics | Future snooze rejected without rescheduling; preview/confirmation and idempotent receipts tested | Physical reminder receipt and current live disclosure interactions unverified |
| Exact note link | Owned note read-back, edits/conflicts/replay and exact UI-link regressions | Exact mixed-script audit-note Unicode read-back still unverified |
| Formatting/corrections | Markdown/LaTeX suites, DNA polarity and vector-domain guards, persisted correction/revision conflict tests | No new live science-generation sample |
| Retry/file-only/duplicates | PNG/PDF multipart and map fixtures cover AI_BUSY/AI_TIMEOUT, both transports, unchanged payload/file-only/filename, single save/charge after exact retry | Cloud driver cannot select OS upload files; no new live PNG/PDF request |
| PDF citations | Extracted-page grounding, filename/page matching, wrong-file/out-of-range and history-exclusion regressions | No new production citation answer verified against an uploaded synthetic PDF |
| EN/GU/HI/mobile | Connected synthetic Classroom parity in all three languages, five browser widths, 13 views and both themes | Real connected Classroom parity, physical-phone upload/keyboard and notification receipt remain unverified |

PR74 CI ran **200/200 varied critical fixture journeys**, ten categories, EN/GU/HI, 20 isolated two-account schemas, zero failed journeys. Fixture p95 journey duration was 183.8ms; this is **not** AI first-text latency or production availability. Its full run passed 883 backend/security tests. A separate local targeted run on this baseline passed 231 provider/privacy/grounding/science/stress/command tests in 2.37s; database suites are skipped locally without an isolated PostgreSQL service.

## Bounded live follow-up

TinyFish run `f327a0e4-e946-4575-8c2a-4a004ba87549` confirmed an actual signed-in Dashboard and opening the Notes secondary disclosure. It did not reach the actual Account language selector, Study/Classroom module or parse the timing JSON; three deterministic Classroom sends were unrun. Its reported zero assignment counts are **unknown**, not observed zeros. Original English remained English. No new generation, upload, sync or record mutation was requested or reported. Missing-controls claims conflict with deployed source and existing five-width browser checks; they are not established application defects.

The prior PR74 bounded live run observed Planner form opening/focus, Notes controls, Chat study/sound controls, composer and right history. It did not verify full secondary-menu contents, reset values or the history toggle. Do not turn partial observations into passing whole journeys.

## Provider timing evidence and acceptance limits

A bounded read of content-free production logs for 20–21 October returned seven historical stream timing rows. Header-to-first-text deltas were 0–1ms; provider-header waits ranged from 3981ms to 17295ms. Two rows completed; five were interrupted. These rows exclude application preparation, queueing and browser/network time, have no probe IDs, and are not a representative success-rate sample. They locate substantial waiting before provider output; they do not justify a model or timeout change.

The last independently readable browser mixed-history baseline remains 55 attempts: 44 complete, 9 errors, 2 cancelled; 40 first-text samples; median 6250.5ms and p95 17802.8ms. It is historical and not release-specific. The follow-up JSON read was unavailable, so no fresher baseline is asserted.

Production >=99% success, p95 first useful words <5s, physical-device delivery/uploads/keyboard and an independent eight-gate live pass are **not established**. Repeated production probes, exhausted quotas and invented timings cannot close those gates. Keep failures and cancellations in the disclosed denominator. No 10/10 certification is claimed.
