# Connected Classroom recovery and live retest — 18 October 2026

Scope: provider/upload recovery and citations, connected Classroom in EN/GU/HI,
small UI/error copy, and measured acceptance gates. Existing stack, models,
production quotas, Google scopes and infrastructure are unchanged.

## Reproduced before editing

On live commit `72d7c675b59c5fe6c80a0fe5a8ef47a0355de06d`
(`2026-10-18-provider-boundaries`), the signed-in Normal chat history displayed:

`Failed: Failed: Nothing was saved: no valid action was returned.`

`load_receipts` put the persisted display prefix into `action_error`; the client
added the prefix again. Four backend regression cases and the historical-prefix
renderer regression failed against the unchanged baseline. No provider call was
needed to reproduce this history-rendering defect.

The live exact receipt URL `/dashboard?mindmap=12#mindmaps` now opens the existing
`Audit18C Probability` map directly after a fresh sign-in. Root, all three
branches, and the fair-die `3/6 = 1/2` detail were observed. This closes the
previous self-retest gap for PR58's cold-link fix; it is not a new generation or
an independent review.

## Minimal repair and checks

- Return the error detail separately from the persisted display prefix. Keep
  the stored message, exact user request and receipt schema unchanged.
- Accept legacy prefixed errors in the client, render one native failure label
  in EN/GU/HI, and translate the known action-validation/read-back errors. Keep
  the Retry control and withhold saved-item links for unsaved actions.
- Bust the chat-actions/Classroom asset caches. Advance the health/smoke release
  together to `2026-10-18-classroom-recovery`.
- Extend actual Chromium connected-Classroom fixtures across EN/GU/HI: selected
  course and assignment labels, save selection, sync, consent before AI,
  localized busy failure followed by retry, unchanged teacher instructions,
  retained selected-assignment consent, literal unsafe text, and one existing
  Planner task after reopening/syncing. These are isolated provider fixtures,
  not authenticated live Google results.

## Connected account: reproduced recovery defect

The owner then securely signed into an account with an existing Classroom
connection and one selected course. Its old imports were visible, the last sync
was flagged failed, and submission state was unavailable. One manual live sync
failed with the generic retained-imports message. A Normal chat read returned
the specific `Reconnect in Study → Google Classroom` recovery reason instead
of inventing a current pending list. No assignment was sent to an AI provider.
This debugging cohort has **0/2 successful fresh Classroom retrievals** (one
manual sync and one Normal chat request); both require authorization renewal.
It is not a representative availability estimate and must not be omitted from
the live results.

Two source defects prevented that recovery: the dashboard dropped the API's
`error_code`, and a connected dialog had no reconnect entry. More seriously,
the OAuth callback used `ON CONFLICT DO NOTHING`, discarding renewed credentials
for an existing connection. Repair the existing callback to replace only the
encrypted authorization, invalidate the old submission snapshot, and increment
the optimistic version while preserving course selection and imported records.
Show native sanitized reasons and an explicit-consent reconnect control in all
three languages, including immediately after an authorization failure. Required
Google scopes are unchanged. New PostgreSQL coverage checks credential renewal,
preserved imports/selection, version change and account isolation; Chromium
fixtures cover `error_code` recovery and no reconnect without consent.

The first exact-head CI (run 268) stopped with **823 passed / 6 failed** before
browser checks. The six dated-provider fixtures replaced the shared stdlib
`time.time`, making their own Flask session signature appear issued in the
future once the real CI clock passed the fixed test time. Isolate that provider
clock rather than weakening authentication or retry assertions. The fixture now
also asserts authenticated conversation creation succeeded. A new green
exact-head run is required; run 268 is not counted as passing validation.

Local focused backend checks: **109 passed**. The repository JavaScript checks
pass, including exact receipts and historical failures in EN/GU/HI. Full
PostgreSQL/Chromium CI is required before merge. Chromium is not installed in
the local runtime; the attempted local browser run stopped before any journey.

## Current live limits

- PNG/PDF: both synthetic files have verified ground truth. The actual browser
  chooser was blocked by native credential-data protection before attachment.
  The documented existing-tab navigation succeeded; the chooser still refused.
  No alternate upload channel, credential access, or production-limit bypass
  was used. **Zero new live upload/provider/citation attempts completed**.
- Classroom: the demo was disconnected, but the owner's second account was
  securely authenticated and its existing connection tested as described above.
  Renewed Google authorization and a successful fresh sync remain pending.
  Google sign-in selection alone did not establish an authenticated session.
  No new OAuth scopes or fabricated assignments were introduced.
- Retrieved content-free provider timing/error logs from `11:41:39Z` through
  `14:43:15Z`: **0 events**, `hasMore=false`. This supplies no live success
  denominator or first-word percentile. No new paid provider calls were made.
- The earlier 200/200 database fixture journeys and 100/100 note receipts remain
  staging evidence only. They do not prove production availability or latency.

## Eight critical trust checks

| Check | Current evidence | Outstanding live requirement |
|---|---|---|
| T1 Today's Planner | Earlier exact-title/time live comparison; current timezone fixtures | Independent fresh comparison |
| T2 Durable map | Earlier saved map 12; exact cold link now self-retested live | Independent creation/retry/reload |
| T3 Future Snooze | Preview/confirm/timezone fixtures | Fresh independent reminder check |
| T4 Exact note destination | Earlier exact Unicode note 35 and deep-link reopen | Independent fresh save/read-back |
| T5 Readable math | Browser/math regressions; existing live map content observed | Independent full reading/export check |
| T6 Quota gating | Earlier live 2→1 and unchanged quota on failure; exhausted/pending fixtures | Independent success/failure refresh check |
| T7 Stages and Stop | Earlier local Saving/draft observation; cancellation/replay fixtures | Live Stop and network-race retest |
| T8 Effective privacy | Selected-source, refusal, paused-memory and two-account fixtures | Connected-account live comparison |

**Acceptance remains open:** representative production core-flow success
**≥99%**, end-user **p95 first words <5s**, complete connected EN/GU/HI live
journeys and all eight independently retested trust checks. No numeric product
rating, independent pass, physical-phone pass or production SLO is inferred
from these fixtures, an empty log query, or an existing saved record.
