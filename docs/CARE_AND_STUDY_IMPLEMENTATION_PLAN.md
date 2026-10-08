# Saathi: care companion + student partner

Working implementation plan, 7 October 2026. Scores are feedback, not guarantees.

## Guardrails and evidence
Keep Flask/PostgreSQL, cream/beige styling, right-hand chat history, EN/GU/HI and lightweight JavaScript. Domain/hosting changes and public launch are out of scope. No new AI vendor.
Verified live: login, note save, Gujarati response, mock exam timer/navigation/flag/submission/explanations. Outstanding: mobile device testing, PDF/OCR processing, full mindmap export, account export/deletion, reminder delivery, full translations.
Already shipped: simpler hero CTAs, waitlist, OG image/tags, illustrative demos, lazy tools, parallel dashboard requests and bounded streaming rendering. Do not rebuild these.

## 1. Foundation and calm navigation
- [x] Collapse secondary tools into accessible More; retain direct URLs and automatic expansion for active sections.
- [x] Keep Today, Study, Care, Notes and Chat immediately reachable.
- [x] Remove dashboard streak card/badge and habit streak pressure; preserve real habit completion history.
- [x] Replace competitive/viral exam copy with private revision language; retain voluntary sharing.
- [x] Fix Hindi label, account grammar, password visibility controls and duplicate initial session check.
- [x] Prioritize next task, next reminder and recent chat; collapse counters into an optional overview and suppress zero values only after overview loads.
- [ ] Skeletons matching final dimensions; no greeting flash or layout jump; retry without losing drafts.
- [ ] Condense repetitive landing stories; retain clear care/limits/privacy copy, visible mobile login/signup and one primary CTA.
- [ ] Reconcile actual Plus entitlements and referral promises without removing earned benefits.
Acceptance: all tools remain reachable by touch/keyboard; deep links, Back and notes keep working; no palette/sidebar relocation.

## 2. Existing feature reliability
- [ ] Chat: first chunk, long replies, Stop/Retry/edit, rapid A→B→A navigation, pagination and next-message drafts.
- [ ] Notes: create/edit/search/reopen/export; explicitly select context before AI use.
- [ ] Reminders: create/edit/pause/resume/snooze/complete; timezone and permission states clearly shown.
- [ ] Memory: review/edit/pause/delete/clear, and prove inactive memory is excluded from AI.
- [ ] PDF/image: size/type validation, cancellable progress, uncertain OCR disclosure, retry preserving input, source-grounded summary/formulas/flashcards/questions and save-to-notes.
- [ ] Mock exam: server deadline, background tab, refresh recovery, unanswered palette, submit-once, results and private downloadable scorecard.
- [ ] Mindmap: touch/keyboard pan/zoom/collapse, large-map readability, accurate PNG bounds and generation retry.
Acceptance: one success and failure/recovery path for every flow; no fake success before persistence.

## 3. Personal context with permission
- [ ] Optional care profile: name, language, timezone, accessibility preferences, user-reported conditions/allergies and clinician instructions.
- [ ] Optional study profile: subjects, level, goals, confirmed exam dates and available study time.
- [x] Confirm before saving health information; retain user-reported source and last-reviewed date. No inferred profile writes.
- [x] Separate care fields from general memory. Explicit per-field AI permission defaults off; care only in Wellbeing, study only in supported study modes. Exclude fields after 90 days until reviewed; disclose external processing.
- [x] Show saved fields, permission and review date; versioned edit/delete and revoke-all AI permission. Profiles are not shared with caregivers. Account export/deletion includes profile records.
- [ ] Trusted caregiver access is explicit, limited and revocable; never automatic family access.
Implementation: extend existing memory/preferences ownership patterns; add migrations and account export/delete coverage for new records.
Acceptance: two-account isolation, consent withdrawal, stale/contradictory profile handling and export completeness.

## 4. Proactive care and medication reminders
- [ ] Extend the existing reminder scheduler, not a parallel scheduling system.
- [ ] Save the exact user-confirmed prescribed instruction, schedule, timezone and recurrence. Prescription OCR creates a draft requiring confirmation.
- [ ] Do not choose medicines, insulin doses, injection timing or catch-up doses. Meal timing is separately confirmed, not inferred from age/diabetes.
- [ ] Separate recurring instructions, individual occurrences and notification delivery attempts.
- [ ] Occurrence states: pending, user-reported taken, skipped, not confirmed. No response is not proof that medicine was missed.
- [ ] Taken / Remind me later / Skip / Need help, with clear confirmation and correction. Notification snooze never rewrites prescribed timing.
- [ ] Deterministic scheduling and translated templates; no model call needed to decide whether a reminder is due.
- [ ] Unique occurrence IDs, bounded retries, duplicate prevention, stale-message expiry, timezone/DST tests and privacy-safe audit logs.
- [ ] Opt-in follow-ups, quiet hours, frequency limits and sensitive lock-screen content hidden by default.
- [ ] Honest states: in-app only, permission missing, server delivery unavailable, queued/sent/failed. No guaranteed delivery or emergency-monitoring claim.
- [ ] Caregiver follow-up only with both parties' consent and a chosen trigger; no silent escalation.
Acceptance: restart/offline/retry/snooze/timezone/pause/revocation tests; clinical review before health-sensitive beta use.
Example after schedule confirmation: “John bhai, tamara save karela schedule pramane dava nu reminder chhe. Lidhee chhe?”

## 5. Wellbeing and food support
- [ ] Opt-in wellbeing check-ins with skip and adjustable frequency; show user-reported trends without diagnosis.
- [ ] Optional clinician-shareable summary under user control.
- [ ] Food ideas account for preferences, budget, local foods, allergies and clinician restrictions.
- [ ] General food support stays distinct from therapeutic diets; complex conditions/insulin plans require qualified clinical review.
- [ ] No fixed calorie/fluid/carb prescription from age or condition alone, and no medication change based on an AI meal plan.
- [ ] Urgent symptoms direct users to appropriate human help; never wait for a scheduled reminder or pretend help was dispatched.
Acceptance: unsafe-dose requests, allergies, uncertain prescriptions, missed-dose questions and urgent symptoms tested in all three languages.

## 6. Google Classroom: read-only first
- [ ] Separate Connect Classroom permission from Google login; selected courses only.
- [ ] Minimum needed own-coursework/course read scopes; avoid classmates, unnecessary grades and write permissions.
- [ ] Server OAuth authorization-code flow, state/redirect validation and PKCE as appropriate; encrypted refresh-token storage, never frontend storage/logs.
- [ ] Proposed classroom_integration.py plus connect/callback/status/sync/disconnect endpoints, per-user connections and external-assignment-ID migrations.
- [ ] Import title, instructions, original link, due date and status. Preserve no-deadline items; do not invent exam dates.
- [ ] Idempotent manual/bounded scheduled sync; display last successful sync, stale state, quota/admin/revocation errors. Add Pub/Sub only if justified.
- [ ] New assignment → explain requirements → break into steps → add to planner with user control.
- [ ] AI uses selected assignment content with permission. Treat uploaded/classroom instructions as untrusted content, never system authority.
- [ ] Local task completion is distinct from official submission. No automatic turn-in, teacher messages or classroom posts.
- [ ] Disconnect stops sync, revokes tokens where supported and offers imported-data removal; export/delete includes integration records.
Dependencies: Google Cloud API/OAuth configuration, authorized test student and possible school-admin approval. Build/test before requesting owner configuration; do not claim connection is live until verified.
Acceptance: selected-course isolation, duplicates, edited/deleted assignments, missing deadlines, revoked tokens and admin-blocked authorization.

## 7. Exam preparation companion
- [x] User confirms exam date, topics, timezone and time budget; distinguish assignment deadlines from exams.
- [x] Preview estimated recall/practice/revision blocks with breaks and a final light/rest day. Reject impossible minimum coverage and disclose partial coverage. Preview fingerprint prevents unnoticed changes before saving.
- [ ] Ask progress, then re-plan missed days without shame or streak loss.
- [ ] Gentle/direct tone choice; direct remains respectful.
- [x] Save reviewed study blocks into the existing Planner with duplicate-safe retry. Tasks can be manually adjusted there; removing a plan retains tasks explicitly.
Example: “Exam ne 26 divas baki chhe. Aaje 20 minute chapter 1 thi sharu kariye?”
Acceptance: changed dates, timezones, unrealistic workloads, overdue tasks and manual overrides.

## 8. Design, accessibility and quality gate
- [ ] Consistent typography/spacing/radii/buttons; test cream/light/dark states without changing the established identity.
- [ ] Optional larger text, 44+ CSS-pixel targets, clear labels and optional read-aloud; do not infer ability solely from age.
- [ ] Complete EN/GU/HI controls/errors/loading/dialogs, date/time formatting and matching AI response language.
- [ ] 320/360/390/768/1280 viewport checks, keyboard, screen reader, reduced motion, contrast and real Android/iPhone keyboard/touch testing when available.
- [ ] Data lifecycle audit: collection → storage → AI use → sharing → export → deletion; privacy copy must match behaviour.
- [ ] No health text, OAuth tokens or secrets in analytics. Verify cross-account authorization for every added endpoint.
- [ ] Target feedback ≤100 ms, warm LCP ≤2.5 s, INP ≤200 ms and CLS ≤0.1 on documented devices/networks. Targets are not measured results.
- [ ] Measure AI first-text and full-response separately from app startup; preserve input on slow/offline failures.
Gate: no known critical privacy/medical/data-loss defects; primary success and recovery flows pass; list untested device/production checks. Scores cannot be guaranteed.

## Implementation checkpoint — 7 October 2026
Implemented in this batch:
- Account / Care / Study entry points for optional profiles with EN/GU/HI controls, confirmation, field-specific AI consent, review age, edit/delete and revoke-all. Existing account name/language/timezone controls remain authoritative.
- Separate profile storage, account-scoped queries, non-reused field versions, export and cascading account deletion. User-entered clinician instructions are labelled unverified; no diagnosis inference or medical scheduling is added.
- Exam date/topic/time-budget confirmation; deterministic preview, limited-coverage warnings, breaks/rest, preview fingerprint and duplicate-safe Planner creation. No model credits are spent generating these plans. New plan creation is not automatic replanning.
- Mindmaps: subtree-sized layout to prevent overlap; collapse/expand, keyboard zoom, mouse drag/native touch scrolling, bounded full-hierarchy PNG with wrapped descriptions (including all descendants).
- Mock tests: account-scoped browser answer/flag recovery within existing expiry, submit-once guard and failed-submit timer recovery. Existing server deadline/grading remain unchanged.
- General memory: confirmed clear-all, owned by the signed-in account; profiles and conversations remain separate.
- Earlier chat/history/notes/Planner race tests are now included in the JavaScript quality gate; stale fixture assumptions updated for parallel startup and stream painting.

Verification: local Python and JavaScript suites pass. GitHub CI run 37635133935 passed the full PostgreSQL suite, including ownership, stale writes, consent/revocation, export, duplicate plan creation and account deletion, plus existing Chromium flows at desktop/mobile viewport sizes. GitHub CI run 37671608406 additionally passed the real consent/revoke forms, exam preview-to-Planner flow, complete 25-node mindmap collapse/expand and PNG download checks at 1280px and 390px. All 274 Python tests passed against the isolated database. Physical-device and live production checks remain unverified.

Still open (not represented as complete): full EN/GU/HI coverage of legacy screens and backend errors; pixel/contrast/device checks; landing length/entitlement reconciliation; PDF/OCR end-to-end verification; mock late/offline completion beyond existing deadline; timezone-aware medication occurrences and delivery tracking; opt-in clinical-context check-ins/food workflows; caregiver access; Google Classroom OAuth/import/sync; changed-exam-date/adaptive replanning. The profile's food-preference field stores user input only and does not implement diet planning.

External gates: Classroom needs configured Google Cloud OAuth/API and a permitted test student; medication/clinical-context beta needs clinical review and verified scheduler delivery. Neither integration is claimed live. No deployment/domain changes or new AI vendor.

## Medication-log checkpoint — 8 October 2026
Implemented behind `CARE_ROUTINES_ENABLED=false` (default):
- User-confirmed existing clinician instructions, explicit storage consent, timezone and once/daily/weekly schedules, stored in the existing reminders table. No inferred prescription or AI dose/timing decisions.
- Separate, uniquely identified occurrences, reported taken/skipped/not-confirmed states, versioned corrections and confirmation before changes.
- Recurrence advances without interpreting silence as a missed dose. Bounded 30-day reconstruction after downtime, DST gap/overlap policy shown to the user, pause/resume and notification-only 30-minute snooze.
- Existing cron/push scheduler reused. Generic lock-screen payloads, existing quiet-hour/permission gates, bounded push retries and linked delivery attempts. No medication email delivery or caregiver escalation.
- Account-owned history/export/delete, duplicate-safe creation, general reminder endpoints cannot mutate medication records, EN/GU/HI controls and human-help guidance.

Not enabled or claimed clinically validated. Clinical review, real-device notification testing and scheduler verification remain mandatory before enabling the environment flag. Prescription OCR, instruction editing without replacing the schedule, caregiver consent/escalation and flexible multi-time daily schedules remain open. Food support and Classroom are not implemented by this checkpoint.

Follow-up hardening: future occurrences cannot be snoozed into early notifications; malformed actions return validation errors; recurrence advancement is independent of notification snooze, and keyset batches prevent schedules beyond the first 100 from being starved. Added DST, consent, isolation, duplicate-create, correction/version, export/delete, restart and pause/resume tests. Database and browser CI results must be checked before merging this checkpoint.

## Primary reference basis (reviewed 6 October 2026)
- https://developers.google.com/workspace/classroom/guides/auth
- https://developers.google.com/workspace/classroom/guides/push-notifications
- https://www.cdc.gov/diabetes/treatment/your-diabetes-care-schedule.html
- https://www.cdc.gov/diabetes/healthy-eating/diabetes-meal-planning.html


## Missed-study replanning checkpoint — 8 October 2026
- Existing saved plans offer a progress-confirmed preview of new dates for untouched overdue blocks. No AI calls and no duplicate tasks.
- Completed/manual edits stay unchanged; future blocks consume this plan's daily capacity. Preserves breaks and the pre-exam rest day; explicitly reports blocks without space. Other plans/commitments must still be checked in Planner.
- Snapshot validation rejects intervening progress/edits; row locks make application atomic and retries reuse the saved result. Previously replanned blocks can move again unless manually edited.
- EN/GU/HI controls, ownership, stale preview, budget, overdue, retry and desktop/mobile form checks added. Changed exam dates and cross-plan workload balancing remain open. CI verification pending.

## Classroom import checkpoint — 8 October 2026
- Implemented separate consent/code flow with single-use expiring server state, session binding, PKCE, fixed HTTPS redirect and encrypted server refresh-token storage. Default off; no credentials requested or configured by this change.
- Own-student course list, explicit selection (up to three), bounded manual sync and idempotent assignment upsert. Titles, original instructions/links and UTC deadlines only; grades/rosters are not requested. Missing/invalid deadlines stay unset.
- Stale/failure states preserve earlier imports; complete snapshots mark unavailable work without deleting local tasks. Adding to Planner needs confirmation and is retry-safe; imports never overwrite edited tasks or imply official submission.
- Disconnect stops import, attempts remote revocation and optionally removes imported records. Existing Planner tasks remain; export excludes credentials, account deletion cascades through stored integration records.
- EN/GU/HI controls and ownership/consent/sync/duplicate/deadline/state/export/revocation regression tests added. CI pending. Live Google authorization, scheduled sync, selected-assignment AI explanations and official submission-status retrieval remain open. Owner setup is documented in CLASSROOM_SETUP.md.

Copy/landing follow-up: removed the duplicate Today story below the hero to reduce repetition; retained reminder proof, study cards, pricing and care/privacy limits. Account upgrade actions now disclose Coming soon when checkout is disabled. Referral bonuses explicitly describe current higher study limits, without changing earned access. Replaced provider/database jargon in public privacy explanations. Full legacy-screen translations and physical-device visual review remain open.
