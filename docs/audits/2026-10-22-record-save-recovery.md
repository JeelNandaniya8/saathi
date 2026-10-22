# Task and reminder save recovery — 22 October 2026

## Reproduced before changing production code

Baseline `78a4554814612e629c6e0f4b359c207a77913dec` had two remaining save paths
outside the Normal-chat action receipt protocol. The Chat task/reminder dialogs
sent no client identity, allowed simultaneous handler submissions, and closed
with a success notice from the POST response without reading the saved record.
The Dashboard task form likewise omitted a retry identity; its reminder form
already retained one.

Executing the shipped Chat handlers against deterministic lost-response,
double-submit and independent-read fixtures failed **6/6 checks** in 18.5 ms.
The extended existing Dashboard save-race test also failed because the task
request had no identity. These are synthetic reproductions; no production
records, teacher files, provider requests or quotas were used.

Two further timezone fixtures failed before their correction: with a UTC
browser and an Asia/Kolkata account, both dialogs saved 18:30 as 18:30 UTC instead
of 13:00 UTC. They now use the existing account-clock input/parser, display the
account timezone, and reject ambiguous daylight-saving times without a POST.

## Correction

Both Chat dialogs retain a UUID for the unchanged draft, block overlapping
submissions, keep the draft and identity on either POST or read-back failure,
and verify the exact owned record before showing success and its ID-specific
Planner/reminder link. Text typed during the earlier save stays in the dialog.
The receipt link remains available longer than an ordinary toast and pauses
expiry while focused. New critical copy is provided in English, Gujarati and
Hindi; asset versions prevent cached translation catalogs hiding the update.

The task API accepts an optional UUID. Additive migration 039 gives new requests
a nullable identity and a per-owner unique index; existing tasks keep NULL and
legacy callers remain compatible. Identical retries, including concurrent
ones, return one object. Reusing an identity with different details returns 409
for both tasks and reminders, rather than implying that the changed request
was saved. The old reminder regression now checks rejection and independent
read-back of the unchanged original; its overwrite protection is retained.

An owned task GET supplies independent read-back. Exact task/reminder links
resolve by ID even when the initial list omits that record. No provider,
production allowance, sharing preference, notification permission or paid
infrastructure setting changes.

## Live observations and limits

The previously tested PR80 remains the live baseline until this change passes
CI and is deployed. Scheduled GitHub run 39727968625 completed its actual
Classroom refresh and general-alert jobs successfully on 22 October; this proves
job execution, not physical notification delivery or a punctual schedule.

Read-only browser run `f377f6ce-9ebe-4623-a82f-35d8e00d2fcd` reported a cold
note38 UI link and a mixed-history timing summary: 76 attempts, 62 completed,
11 errors, 3 cancelled; 56 first-text samples; median 5827.5 ms, p95 17926 ms.
It did not retrieve the original note command for a codepoint comparison.
Its escaped note text conflicts with earlier reports, and one reported timing
UUID is malformed. The note's exact Unicode is therefore **UNVERIFIED**, and
the timing transcription is not an independently certified release sample.
The run exceeded its requested 150-second bound (reported 240 seconds); no repeat
or new AI probe was made. Neither quota/reset details nor physical-device
behaviour were verified by this run.

The selected Classroom PDF permission flow reached Google login in run
`42f15678-7658-4dfb-b564-9b89655c483e`; human Google login/final consent is still
required. No file download or PDF-to-AI request was performed. Actual PDF
citations, live PNG/PDF error recovery, physical phone upload/keyboard/alerts,
independent eight-gate certification, production >=99% and p95 <5 seconds remain
open. Existing synthetic coverage must not be relabelled as these live passes.

CI and deployment evidence will be recorded in the review PR. The migration
only adds a nullable column/index and does not rewrite or delete existing
records; the previous application remains compatible with the added schema.

## Publication blocker

Automatic approval review rejected creating the GitHub tree twice, including
after repository ownership, existing PR80, public visibility and connected
admin/push rights were verified. Its stated reason is that broad permission to
continue/merge/deploy does not specifically authorize publishing source code
to this public repository. No branch, PR, remote commit or deployment was
created at that point. The owner subsequently explicitly approved publishing
this exact 14-file patch to the existing public repository and continuing
CI/merge/deployment. The review restriction was not failed authentication.

Local backend validation passed 751 tests with 346 database-dependent skips;
the full JavaScript checks passed, including the 16 save-dialog and timezone cases. The final targeted backend/static checks
passed 48/48 in 0.49 seconds.
New PostgreSQL tests cover concurrent retries, owner isolation, invalid UUIDs,
changed-payload rejection and legacy callers; these remain unrun until CI is
available. No claim of a production fix is made for this unpublished patch.
