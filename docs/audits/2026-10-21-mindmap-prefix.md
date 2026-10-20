# Privacy-prefixed Normal mindmaps — 2026-10-21

## Reproduced problem

A fresh Normal request beginning with "Do not use my Classroom, notes, memories or workspace sources." and then explicitly requesting a saved mindmap did not satisfy the start-anchored English command classifier. It fell through to ordinary chat rather than the existing JSON study-generation, validation and receipt path. A plausible map description in a persisted conversation is not proof of a saved mindmap.

The pre-fix regression commit `8fee6140ce929d97cfef0347e229387eaa638308` failed the direct `automatic(REQUEST, 'mindmap')` assertion in CI run [39483115088](https://github.com/JeelNandaniya8/saathi/actions/runs/39483115088). That run reported 11 failures and 868 passes. Ten additional failures used fake model names rejected by the model-name validator; they are not clean provider-failure reproductions. The repaired fixtures use valid synthetic `gemini-` names and never call a real provider.

## Minimal repair

Only mindmap creation classification retries the existing classifier after removing negative clauses with the existing source-query parser. Preview, no-save, quoted/example and literal-field guards still run. A full-turn veto is checked before the new retry, including a no-save instruction after a titled field. Original persisted requests and source privacy policy are unchanged.

Both chat transports reject a known exhausted map allowance before provider generation; the final save still rechecks the quota. The existing direct quota reply carries an internal AI_QUOTA marker so both endpoints return the same error/allowance contract rather than persisting a normal assistant reply for an exhausted request. There are no model, deployment configuration, schema or frontend changes.

## Regression evidence

The added tests cover the exact privacy-prefixed request; twelve no-save/preview/quotation safety cases; streaming and ordinary JSON generation with and without file-only selection; real isolated-PostgreSQL receipts and integer map IDs; owned read-back, cold API reads, exact-request busy retry, idempotent replay and cross-account exclusion; and exhausted synthetic quotas with no provider access. All provider responses, failures, files and quota consumption in these tests are fixtures.

The first repaired candidate CI run [39484372589](https://github.com/JeelNandaniya8/saathi/actions/runs/39484372589) passed 877 tests and failed the two exhausted-quota transport assertions, exposing the existing direct-reply short-circuit (HTTP 200 instead of the error contract). The follow-up carries that quota condition through to endpoint rejection and additionally requires zero persisted messages and unchanged allowance.

Exact candidate CI and release/live results are recorded in [PR #73](https://github.com/JeelNandaniya8/saathi/pull/73). CI success is staging evidence, not a production success-rate estimate.

## Live evidence and limits before this repair

The provisional live map report reopened conversation 108 and supplied a title as resource ID. Its object lookup returned 404, and no valid integer map receipt was established. Treat that saved-object claim as UNVERIFIED. A conversation URL is not a map receipt.

Stop visibly halted a partial reply and retained the draft, but two cancellation timing rows and multiple clicks prevent a controlled single-attempt/zero-duplicate conclusion. The short text probe was not run. Exact Hindi note read-back remains unverified because returned reports were not raw ASCII-escaped Unicode.

The latest mixed-history baseline was 55 attempts, 44 completed, 9 errors, 2 cancelled; 40 first-text samples; median first text 6250.5 ms and p95 17802.8 ms. Recent rows have no request ID and cannot be reliably attributed to a release or probe.

Live PNG/PDF upload and citation recovery remain blocked by the automation driver's unsupported OS file picker (zero file sends), not a reproduced application failure. Real-device mobile uploads, reminder delivery, independent eight-gate retesting, production >=99% core success and p95 first words <5 seconds remain unproven. Do not bypass production quotas or infer an artifact save from prose, a toast, or allowance consumption.
