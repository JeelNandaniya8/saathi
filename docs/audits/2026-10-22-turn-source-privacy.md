# Turn-scoped source refusals — 22 October 2026

## Reproduced before changing code

Baseline `aa9c8da3e5344c0a9d579eadc98210bb7730e0db` kept automatically shared
workspace records, active memories and earlier conversation text when the
student explicitly refused those sources in the current turn. Normal mindmap
generation could additionally append the refused memory bundle after building
its provider payload.

Test-only commit `c288b9ac9f8980d773d7de0027d78948d95a9cf9` reproduced ten failures in 1.08 seconds. All markers,
records and provider responses were synthetic. A further deterministic Planner
reader test failed because a refused task source still reached a database read.
No production private data was used to demonstrate either defect.

## Minimal correction

- Read current-turn EN/GU/HI source exclusions before the scoped SQL snapshot.
  Exclude those sources even when stored sharing is enabled. Broad workspace
  exclusions also suppress memory and profile fields.
- Apply the same exclusions when rendering a previously loaded snapshot and
  before deterministic Planner reads. Do not change the stored permissions.
- Omit mixed prior history when it could contain a refused source. Suppress
  opaque memory bundles at the provider boundary and in Normal mindmap JSON
  generation. Keep the exact current request and its attachments.
- Keep ordinary unfinished-task questions, mathematical negations, unrelated
  permitted sources and subsequent permitted requests working.

The PostgreSQL regressions exercise streaming and JSON chat with owned active
and paused memories, a second account, consented profiles, tasks and prior
history. They inspect the actual fixture provider payload and persisted reply,
then verify that the following permitted request still receives allowed context.

## Live checks before this correction

Bounded read-only run `f9c08f0e-b5c2-4240-8257-c1ebf8813269` compared existing
persisted English, Gujarati and Hindi Classroom replies against the current
selected-course rows. Each matched six pending, two overdue and three undated
assignments, including exact titles and deadlines. The owned target assignment
had one Drive PDF and its per-file selection button/checkbox. Names and private
assignment text are intentionally omitted from this report.

Run `7b947a0f-050d-4435-a86b-b9ff344c1bd1` made one synthetic Normal map request
after reading a resolved allowance of two. The resulting integer map ID was
15, with receipt `/dashboard?mindmap=15#mindmaps`; cold-open and reload verified
its synthetic title/root/sample space and one matching object. Allowance was
one afterwards. The report's assistant identifier was a DOM label, not a
persisted message ID; do not treat it as a verified database ID. This check
does not establish that the earlier source refusal excluded every private
context field; the synthetic regressions above exposed that remaining gap.

## Remaining limits

Automatic approval review rejected initiating the new Google per-file OAuth
flow: it requires explicit at-action human confirmation, which broad approval
to finish the PDF test does not supply. No workaround, Google grant, file
download or file-to-AI send occurred. Real PDF citations and live PNG/PDF
failure recovery remain unverified. Physical-phone uploads, keyboard and
background alerts, independent eight-check certification, production success
rate and first-word latency also remain open.

First candidate CI run `39674327346` reported 12 failed and 1072 passed in
270.80 seconds. Two existing date-filter checks caught an overly broad source
refusal classification; the date-selector exception now preserves those reads.
Ten new positive-control assertions assumed the selected Deep study mode would
survive an explicit workspace read, which intentionally switches to Normal.
The control now uses an ordinary Deep study query with saved auto-sharing and
asserts the actual mode as well as the allowed profile/memory/task markers.
No failing assertion or existing test was removed.

Final CI, deployment and post-deployment observations are recorded in the PR.
