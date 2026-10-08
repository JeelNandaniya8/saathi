# Care and Classroom follow-up: code versus live verification

## 1. Response and startup performance

Connection pressure waits up to three seconds for a returned lease instead of immediately failing a request. Exhaustion returns sanitized 503 / Retry-After and does not replay writes. Medication due scans have a partial index; optional care and Classroom surfaces stay under More. See RENDER_ALWAYS_ON.md for a same-service paid-compute proposal and public latency probe. Actual Render plan is unchanged. No measured production timings are claimed.

## 2. Confirmed medicine schedules and transcription

One explicitly confirmed clinician instruction can have 1–6 distinct entered times, saved atomically and deduplicated using the same retry UUID. Every time becomes a separate existing medication schedule, with existing timezone/DST handling, pause/resume, occurrence corrections and generic push semantics. No dose or meal/injection timing is inferred.

Separate file/AI consent allows image/PDF transcription only. Existing validated attachment pipeline bounds file type/size/PDF pages, six requests per day, no profile/memory, no persisted files or draft, usage counts only. Unclear text stays unclear; OCR cannot be assumed reliable. User compares the original with a clinician and manually enters confirmed instructions. No automatic OCR-to-schedule action.

Keep CARE_ROUTINES_ENABLED=false until a qualified clinical reviewer checks names, decimal/unit mistakes, illegible/multilingual prescriptions, duplicate entries, missed-dose wording, recurrence and the exact user flow. Record reviewer/date/decision outside private repository data. No such review has occurred here.

### Physical notification acceptance protocol (not completed)

Use non-medical fixture schedules and two test accounts. Configure existing CRON_SECRET / VAPID and a protected one-minute reminders scheduler. Test Chrome Android, installed Safari iOS, supported desktop browsers: foreground, closed app, locked screen, permission denied/revoked, quiet hours/digest, offline/restart, timezone/DST, paused schedule, snooze, taken versus not-confirmed, expired push subscription, and duplicate scheduler calls. Confirm no dose instructions on lock screens and no cross-account notification after logout/account switching. Record scheduled time, server attempt, push-service acceptance, observed device receipt, and latency separately. Do not claim receipt from service acceptance. Test rollback and independent important-medicine reminders. Real devices, scheduler credentials and clinical acceptance remain external release gates.

## 3. Food choices and caregiver consent

Food organiser rotates 1–20 user-entered options across 1–7 days. It keeps preferences as explicit context; the user selects matching foods themselves. Estimates respect a daily user budget; unknown costs are not assumed affordable. Missing slots remain visibly incomplete. Allergens/restrictions/health conditions stop preview allocation until the user reports clinician review of the exact choices. This report is unverified. Conservative ingredient text matching is an extra exclusion only; hidden allergens, labels, translations and cross-contact still require human checking. No therapeutic quantities, carbs, calories, fluids or treatment changes.

Preview is not stored. Separate health-storage confirmation saves exactly the reviewed fingerprint; edits invalidate it, retries reuse an owned UUID. Ownership, deletion, export and account cascades apply.

Care sharing requires an accepted trusted-contact relationship plus separate bilateral acceptance. Only 1–10 selected owned medication schedules; default status/time, optional name/instructions; 1–30-day expiry. Changing fields resets acceptance, version checks prevent stale approval, contact removal denies further reads, either party can revoke even with beta disabled. No emails, auto escalation, emergency monitoring, caregiver edits or implicit sharing of profiles/food/check-ins/chats. Earlier recipient copies cannot be recalled. Keep the clinical gate off pending review.

## 4. Classroom scheduler and assignment help

Read-only scopes remain courses.readonly and coursework.me.readonly. Google Cloud must enable Classroom API and configure the exact HTTPS callback, consent-screen/testing or verification, permitted student account and encrypted token key; see existing setup guide. No live OAuth account or Google configuration was changed.

After selecting courses, a separate sync preference opts into six-hour refresh. Changing selections disables it. Configure an external protected POST /api/cron/classroom with X-Cron-Secret, typically every minute. The handler processes at most one due account, uses FOR UPDATE SKIP LOCKED, fetches a complete selected-course snapshot before applying it, preserves imports on provider failure, backs off 1/2/4/8/16/24 hours, and disables auto sync for reconnect/admin permission errors. Disconnect removes the connection and stops future jobs. No automatic AI or remote writes. The browser gives manual sync/course refresh 65 seconds and explicitly requested transcription/explanation 105 seconds rather than aborting them at the ordinary 25-second deadline; visible progress retains the input. The 40-second budget checks between requests; per-request timeouts apply, but slow-drip HTTP is not a guaranteed hard wall-clock bound. Use scheduler overlap prevention and HTTP timeout >60 seconds; monitor sanitized errors. Do not treat stored opt-in as proof the external scheduler runs.

A separately consented single available selected assignment can be sent to existing AI for requirements/steps. No profile/memory/other assignments; quoted untrusted data, no invented deadlines, no automatic submission or Planner write. Ownership, selection and connection version are checked again before returning output; changed permission returns 409. Draft is plain text, unverified and not persisted; usage counts only, six explanations/day. Check real permitted student, selected/unselected courses, expired/revoked refresh token, quota/admin block, cron retries/concurrency and reconnect before enabling CLASSROOM_ENABLED.

## Validation

Local Python unit/security and JavaScript checks plus CI PostgreSQL and desktop/mobile Chromium are required for this batch. Mocked providers do not prove clinical correctness, device delivery, Google live access or production performance.

## Instruction review and localisation follow-up

Confirmed instruction review now keeps recurrence/timing unchanged, checks the saved version, preserves elapsed/reported instruction snapshots and updates only future pending snapshots. Accepted sharing returns to pending recipient review. Legacy snapshots capture the available text at migration time; unknown older edits cannot be reconstructed. No medicine or dose is inferred. Study tone has explicit Gentle / Direct and respectful options; existing custom text remains selectable. Tone never overrides the safety or consent boundaries.

Hindi now uses an independently loaded interface catalog rather than silently falling back to the Gujarati/English-only loader. Gujarati and Hindi catalogs can load concurrently without changing the selected language; names, notes, assignments and AI answers remain excluded. All 699 registered legacy catalog keys now have both Gujarati and Hindi copy; parity checks prevent missing or empty translations. User writing and AI answers remain excluded. Text outside this catalog can still retain English; independent native-language/assistive-technology review is not claimed. Browser CI covers 320/360/390/768/1280-pixel application flows and language round trips, in addition to landing sizes. Physical devices, assistive-technology readings and measured production Web Vitals remain unverified.
