# Classroom consent follow-up — 18 October 2026

This is a focused implementation ledger, not an independent product certification.
Inspected baseline: `a00555c6b66cc5a7f32e613080d7ad2ae57fe201`,
release `2026-10-18-classroom-chat`, live Render deployment
`dep-db9upme7bikc73e565cg`. PR54's 767-test result is historical.
Final candidate CI and deployment proof belong in this PR's release record.

## Reproduction and fixes

| ID | Input / failure | Before | Change and regression evidence |
|---|---|---|---|
| CC1 | `Classroom ન વાંચો. Show pending homework.`; curly `don’t`; Hindi `न पढ़ो` | A refusal granted a school read | One refusal predicate controls intent, SQL context, source labels and provider history |
| CC2 | `Explain the sentence 'Show my classroom assignments'.` | Actual deployed browser returned the Classroom-fetch failure, rather than explaining the sentence | Quoted commands cannot grant one-reply consent; straight and typographic single quotes covered |
| CC3 | `Explain vectors without Classroom.` with automatic sharing enabled | Imported assignments and connection metadata entered context; earlier school answers entered provider history | Denied source is excluded from the SQL snapshot and stale supplied snapshots; prior chat is omitted for this turn; other permitted context remains |
| CC4 | Another reply after CC3 | Regeneration loaded context without the original turn restriction | Original user text is passed through the same consent check; both transports and regeneration have database regressions |
| CC5 | `School ni to-do list batav.` | No deterministic Classroom route | Roman Gujarati school scope uses the existing owned read, without an AI call |
| CC6 | Disconnected Classroom in Gujarati/Hindi | English-only recovery | Required English failure lead-in retained; connection, selection, busy and provider recovery localized; snapshots named explicitly |

Initial new unit set: **8 failed, 2 passed** before production edits.
Language recovery: **2 failed** before its edit. Quoted source names also exposed
two refusal failures during development and were corrected. All evidence uses
synthetic data; the live demo had no connected Classroom account.

## Source-state contract

| State | Effective behavior |
|---|---|
| Automatic sharing Off, no explicit request | No automatic Classroom data or connection state |
| Automatic sharing Off, explicit current-turn read | Only authenticated user's selected courses and own submission states; no model call |
| Automatic sharing On | Bounded imported excerpts, labeled as an incomplete snapshot; a pending-work read uses the existing bounded refresh/cache path |
| Explicit source refusal | Overrides automatic sharing and one-turn access; connection metadata excluded; earlier conversation omitted to prevent hidden school excerpts; no preference change |
| File-only | Existing latest-file-only boundary remains authoritative |
| Course selection/disconnect | Existing cache invalidation and owner checks retained |
| Provider failure | Previous imports retained, never reported as a current empty or complete list |

A one-turn exclusion is conservative: follow-ups depending on earlier chat may
need the student to provide the intended material again. It does not erase chat
history or change saved source permissions. Other source exclusions are outside
this focused fix; this change is not a general natural-language privacy proof.

## Validation and remaining limits

Focused unit checks passed locally. The local environment cannot run PostgreSQL
integration tests; skips are not passes. Required CI must execute the real-engine
tests, all existing trust journeys and the five Chromium viewport checks before
merge. There are no schema, OAuth scope, model, quota or infrastructure changes.
Rollback is the inspected baseline SHA above.

The existing eight trust contracts remain qualified by their evidence layer:
Planner, exact note links, future Snooze and Stop have historical live evidence;
math has prior narrow-width browser evidence; privacy gains these regressions.
New live mindmap generation, production first-word p95, a representative live
success rate, complete live EN/GU/HI journeys, real phone keyboard/uploads,
locked-device reminder receipt, a connected Classroom student and the seven-day
pilot remain unverified. Fixture success cannot close those gates. No 10/10 or
public-launch claim follows from this patch.

For a consenting connected student: select up to three own courses; compare one
pending-homework reply with Classroom at the same time; check exact count, titles,
due instants, own submission states and snapshot timestamp. Repeat once after a
selection change, then a source refusal. Do not change assignments or classmates.
For phone checks: exercise the synthetic PDF/PNG upload with keyboard open at
360px, follow its exact page citation, then test one synthetic reminder on a
designated consenting supported device and record actual receipt separately from
scheduling. No messages, invitations or notification tests were sent by this run.
