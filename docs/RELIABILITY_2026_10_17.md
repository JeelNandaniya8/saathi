# October 17 reliability review

Status: proposed changes; deployment and independent live retest are pending. This is not a 10/10 certification. The Flask/PostgreSQL/vanilla JS/Render/Gemini stack and production quotas are preserved.

## Reproduction before edits

Base: `5413eab797e2718568adff35258849e4bbdc5002` (release `2026-10-15-evening-audit`). Read-only live preflight reported healthy, map allowance 2/2 and uploads 5/5, with the next UTC reset displayed as 05:30 in Asia/Calcutta. This establishes availability of those endpoints, not generation reliability. A separate read-only `/api/ai-diagnostics` request reported configured=true, models_status=200, and Normal/care model `gemini-3.1-flash-lite`. The deployed endpoint did not expose the study model, so the production model difference and actual timeout cause remain unconfirmed. The proposed endpoint adds the study model; stream timing logs add only profile/model/attachment count, never prompt, reply or account identifiers. Render logs could not be retrieved because no workspace was selected; no workspace was guessed.

| Finding | Before evidence | Proposed correction |
| --- | --- | --- |
| Normal upload/provider path differs from direct generators | A fixture with a busy fast-model override and a healthy study model fails file analysis with AI_BUSY; direct study profile succeeds. | Normal attachments and mindmap intents use the existing study provider profile, including its startup budget. No new provider or automatic quota retry. |
| Retry loses file-only choice | Executing the real draft functions in Node fails because `file_only` is absent. | Persist exact request key/mode/file-only choice and attachment metadata; after reload require original files to be reattached or explicitly discarded. File bytes are not stored in browser drafts. |
| Same key can refer to changed attachment bytes | Code inspection: replay checked text only. | SHA-256 fingerprint binds text, requested mode, file-only and ordered file names/MIME/bytes. Legacy retries read owned original bytes. Changed requests return 409. |
| Unresolved/stale allowance can enable generation | Deferred-response fixture fails the immediate disabled-state assertion. | Pending/error means disabled; ignore stale responses; refresh after success/failure; saved-job recovery precedes new quota checks. |
| Completed tool can disable the next tool during a click | Chromium at 360px captured a map dialog with no generation request; a completed mock job's delayed quota refresh disabled the button. The focused regression then recorded two unwanted allowance state changes. | Clear the delayed refresh when creation finishes and dispose closed dialog listeners. Checking/waiting labels use the selected language. |
| Recovery job and result can disagree after a lost response | Code inspection: separate commits could leave a saved object behind a failed job. | Commit ready receipt and verified owned document together; never downgrade a committed ready job. Lookup by exact owned job ID. |
| Stop can race final save | Code inspection: browser abort alone cannot prevent a server finishing. | Durable cancellation shares the final-write lock; if save wins, return its verified receipt. Regeneration has a separate idempotency key and the same cancellation checks. |
| Wrong transcription polarity accepted | Fixture stating the transcription template has 5′→3′ polarity passes the old guard. | Narrow direction guard and grounding distinguish template reading 3′→5′ from RNA synthesis/coding strand 5′→3′. Existing correction endpoint still updates source, revision copy and progress. |
| Zero-vector angle accepted as 90° | Incorrect answer key passes the old quality check. | Check defined vector domains before using an angle/unit-vector/projection answer. Zero projection onto a nonzero target remains zero. Unsupported questions are not marked verified. |
| Map fitted text becomes tiny | Code inspection: Fit used the full large hierarchy, with scale allowed down to 0.01. | Readable view preserves at least 12px from 14px descriptions and uses existing scrolling/panning. It does not promise the whole map fits at once. |
| Some saved objects open a section only | Code inspection: habit, journal and check-in receipt links omit their IDs. | Include exact IDs; owned ID reads bypass list truncation and focus the selected object. |

The production generation probe was stopped after automatic approval review rejected it because it would create persistent demo records and consume production map/upload allowances while failure tests were requested in staging. No generation results or production before/after timings are claimed from that probe. Do not rerun it without explicit authorization.

## Verification

- Local Python and JavaScript checks exercise real production functions. PostgreSQL tests require the isolated CI service; local skipped tests are not passes.
- Added staging cases cover changed-file/mode/privacy retries, legacy replay, cancel-before-save and save-before-cancel, regeneration recovery, job response loss, exhausted quota, ownership, incorrect transcription rollback, exact ID reads, vector domains, and one ten-minute exam-stress step in EN/GU/HI.
- The 100-journey note sample performs save, exact-key replay, database read-back and chat reload. Titles rotate EN/GU/HI. Production note limits stay intact. A printed `STAGING_NOTE_RECEIPTS` row records N, duplicates, false saves and receipt latency. This is a deterministic local-command fixture, not a provider success-rate estimate or complete multilingual journey certification.
- Existing regression coverage includes PDF page-number grounding/citation links, correction persistence, privacy exclusions/paused memories, account timezones/DST, due-only reminder scheduling, scheduler failure handling and notification permission states.
- Browser CI uses the actual pages at 1280/768/390/360/320px, with touch/mobile emulation at phone widths. Map text readability, panning, keyboard controls, Unicode, Stop/draft retention and exact record navigation are checked. This does not establish physical-device uploads, a real soft keyboard, or notification receipt.
- New provider failures map stable codes to EN/GU/HI UI errors. Quota checking/reset and critical recovery labels are translated; user text stays untouched. Complete independent EN/GU/HI live journeys remain a release gate.

## The attached audit's eight critical trust checks

These names match the October 15 audit trust table. Staging regression evidence is distinct from an independent live pass; all eight still require that live retest.

| Audit check | Regression evidence and live limit |
| --- | --- |
| What remains today? | Date-scoped Planner reads exclude overdue, undated, completed and other-account records; preserve exact local deadlines. Existing streamed and JSON fixtures pass. October 17 live retest pending. |
| Mindmap honesty | No success without owned read-back; no generation at exhausted quota; atomic document/job completion and exact recovery. Normal chat/provider comparison still needs a live retest. |
| Future snooze | Future reminders cannot be snoozed early; rescheduling remains separate; due-only snooze and recurrence/timezone fixtures are covered. Actual phone delivery remains unverified. |
| Note deep link | Exact note ID, title and text reopen, including with a previously filtered list. Other saved types now also include IDs. Independent live destinations still need spot checks. |
| LaTeX/Markdown | Conditional-probability/absolute-value bars, code bars, tables and inline fractions have renderer regressions; browser tests cover MathML and responsive layout. Independent live rendering review pending. |
| Quota pre-check | Unresolved/error allowance means disabled; exhausted and stale-response fixtures, account reset displays, and recovery before new quota checks. Production limits are unchanged. |
| Waiting honesty | Separate waiting, generating, checking and saving stages; local replies do not claim AI generation. Durable Stop/save races and exact retries are covered. An upstream call can continue computing after Stop; cancellation prevents a subsequent save when it wins the lock. |
| Privacy state | Paused memories, current sharing controls, explicitly excluded sources, owned records and file-only provider payloads have regression coverage. Independent live cross-account/provider-payload review pending. |

Additional release requirements include the audited DNA/vector corrections, readable maps, the ten-minute exam-stress step, complete live EN/GU/HI paths, physical 360px uploads/keyboard, PDF citations and actual reminder receipt. The fixture scope and remaining gaps above apply to those requirements as well. The narrow content guards are not a general factual verifier.

## Timing and acceptance limits

CI run [233](https://github.com/JeelNandaniya8/saathi/actions/runs/39007863736), commit `93ca36a`, recorded 649 passing backend tests in 126.41s. Its deterministic note sample completed 100/100 save/replay/reload journeys with zero duplicates and zero false saves; p50 receipt 31.8ms and p95 receipt 32.9ms. Those are local Flask/PostgreSQL receipt timings, with no provider or external network in the sample. Browser checks are a separate gate.

There is no valid October 17 live generation baseline, no live core-flow sample, and no measured live p95 first words for this PR. Consequently neither ≥99% live success nor p95 <5 seconds is established. The CI note receipt metric must not be substituted for either target. For reference only, earlier October 15 measurements were small samples (Normal first words about 5.72s; file paths about 5.56/7.41s), from another release and workload; they are not an October 17 comparison.

Before deployment acceptance, an independent authorized tester should run the eight gates on staging and then the approved live release, record each request category, language, timestamps, first visible words, completion, saved IDs and reload results, and disclose N and failures. Confirm physical device, timezone, notification permissions and actual delivery time. Keep exhausted-quota, provider-failure, privacy and cancellation fixtures in staging. A 100/100 deterministic note sample is insufficient to certify live availability.

Migration 036 only adds request identity/cancellation fields, a control table and an index. Apply through the existing migration/deployment process. This PR remains open for review; no merge or production deploy is part of this delivery.
