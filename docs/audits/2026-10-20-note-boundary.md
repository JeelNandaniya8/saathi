# Exact note boundaries — 20 October 2026

## Reproduction before code changes

Test-only commit `8888cb2ca577ff577355f18a2256f78f24ffe26f` ran against the
unchanged production parser in [CI run 39459388552](https://github.com/JeelNandaniya8/saathi/actions/runs/39459388552).
Result: **11 failed, 843 passed in 201.16 seconds**. The failures are five
literal-boundary cases and six database cases (EN/GU/HI, both transports).

A synthetic request naming a title ending in `21:36. Content: …` split at the
time's colon, keeping only `21` in the title and moving the suffix into content.
An actual saved row, not a success toast, failed exact title/content assertions.
The live audit's ambiguous note report prompted this reproduction; its Hindi
transcription inconsistency is not evidence of a separate storage bug.

## Minimal correction

- Prefer an explicitly labeled content boundary over punctuation in the title.
- Keep digit-to-digit colons in time/ratio titles.
- Preserve the existing short colon form, quoted titles and labeled fields.
- Keep the original Unicode and internal line breaks. No text normalization,
  AI fallback, schema migration, model change or production-data rewrite.

The new database checks independently read the receipt's owned note twice,
reload conversation/receipt data, replay the exact request without a second
note, reject another account's read and require zero AI usage. Separate
Classroom fixtures exercise the three exact pending-work queries through both
transports with two overdue, one future and three undated assignments, the
account timezone, ownership filtering and zero provider calls. These are
synthetic staging checks, not a live Classroom certification.

## Live evidence and limits

The preceding bounded browser session reported an authenticated Dashboard, one
successful Classroom Sync and a retained synthetic note. Today/open-task
comparison and exact note contents need verification; the language comparison
was unrun. No production records are edited by this repair.

A follow-up signed-in browser run was rejected by automatic approval review
because private note/Classroom data would be visible to an external automation
service without explicit approval of that disclosure. It was not retried or
routed around the rejection.

Old reply-performance history contains 44 attempts (35 completed, 9 errors,
0 cancelled), with a displayed p95 first text of 17,046 ms and eight recent
rows dated 18 October. This is mixed history, not a release-specific sample.
No new live provider/attachment cohort has been collected for this change.

Open live gates: exact owned receipt and today parity; connected Classroom
EN/GU/HI; observed quota/reset; natural AI_BUSY recovery and exact PNG/PDF
retry/citations; real Stop; physical-mobile upload/keyboard and reminder delivery;
new-release success/first-word measurements and an independent eight-gate retest.
No production >=99%, p95 <5 s, physical-device or 10/10 claim is made.

Full CI must pass on the final change before the authorized merge, and the
matching Render deployment must reach Live and pass public smoke checks.
