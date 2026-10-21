# Colloquial Classroom reads — 21 October 2026

Baseline: `fa888171b5e9c052b7e46db37a8097bf09f29898` (PR75).

## Reproduced before changing code

The reported production answer was a generic AI denial of access to the student's Classroom data. The exact triggering user question was not supplied. Ten representative questions in the reported style failed the existing classifier, including `mare ketli assigment baki che?`, `mara classroom ma su assignment aavya che?`, `mara assignments kaya che?`, `my classroom assignments`, and Gujarati/Hindi requests with common assignment spellings or `बताओ`.

The initial regression run produced **15 failures and 14 passes**: all ten intended reads missed the deterministic route; five corresponding source-refusal checks were also not recognized. Existing formal pending-work tests had not covered these forms. A missed route can reach Gemini, which cannot itself fetch the account's Classroom data; adding reassurance to its prompt would not repair that routing gap.

Follow-up cases separately reproduced three Gujarati/Hindi vowel/virama spelling variants and three native owned noun fragments before extending the same bounded matcher.

## Minimal fix

- Share the bounded school-work spelling list between the read classifier and source-refusal guard, including `assigment`, `અસાઇન્મેન્ટ` and `અસાઈન્મેન્ટ`.
- Recognize common Roman Gujarati/Hindi question/read words and native Hindi `बता…` forms.
- Treat a short owned noun phrase such as `my classroom assignments` or `mara college na assignment` as a list request. Ownership inside an explanation or writing-help request does not grant a read.
- Keep generic definitions, quoted/example requests, literal note fields, study-output requests and explicit source refusals outside this route. Extend matching refusals when extending read vocabulary.

The existing deterministic reader still resolves only the authenticated student's selected courses and actual submission states, refreshes when needed, and returns the existing truthful fetch-failure message if Google cannot be read. It does not send the question or teacher text to Gemini, enable automatic sharing, alter courses, create Planner tasks or change provider configuration.

## Regression evidence

The 39 new local unit cases cover colloquial reads, mode normalization, conservative noun fragments, definitions, quotes, mutations and source refusals. The final full local suite passed **652 tests** in 9.26s, with 283 isolated-database cases skipped.

Twelve new isolated-PostgreSQL cases exercise both streaming and JSON chat transports in EN/GU/HI, with a previously selected Care mode, automatic sharing off, a stale assistant denial and a previous-turn source refusal. They require an actual owned fixture read, exact original user text, no cross-account assignment, no Gemini call/AI usage event, unchanged sharing controls, and idempotent replay. Google renewal failures must produce `Google Classroom data could not be fetched right now.` rather than a model-generated denial. These database cases are skipped locally without a test PostgreSQL service; exact-candidate CI and live results are recorded in the PR.

This patch does not prove every possible spelling, physical-device behaviour or production availability. Earlier failed browser navigation is not used as evidence that Classroom is disconnected, and no existing saved conversation is rewritten.
