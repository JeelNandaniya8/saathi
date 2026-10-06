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
- [ ] Confirm before saving health information; retain source and last-reviewed date. Never infer a diagnosis from conversation.
- [ ] Separate sensitive health fields from general memory. Send only necessary, permitted context to AI and explain external processing.
- [ ] Show exactly what is stored/used/shared; field-level edit/delete and revocation.
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
- [ ] User confirms exam date, syllabus and time budget; distinguish assignment deadlines from exams.
- [ ] Build realistic backwards plans including recall, practice, revision and rest; label estimated workloads.
- [ ] Ask progress, then re-plan missed days without shame or streak loss.
- [ ] Gentle/direct tone choice; direct remains respectful.
- [ ] Reuse planner, mock tests, notes and mindmaps rather than add another dashboard.
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

## Status of this commit
Only the checked foundation items are implemented. Today now uses static, low-CPU skeletons for its primary data, guards against false zeroes, and offers direct actions in empty states. Care profiles, proactive clinical-context workflows, meal support, Classroom integration and adaptive exam plans remain planned.
Syntax and focused behaviour checks accompany the initial changes; live/mobile verification remains outstanding.

## Primary reference basis (reviewed 6 October 2026)
- https://developers.google.com/workspace/classroom/guides/auth
- https://developers.google.com/workspace/classroom/guides/push-notifications
- https://www.cdc.gov/diabetes/treatment/your-diabetes-care-schedule.html
- https://www.cdc.gov/diabetes/healthy-eating/diabetes-meal-planning.html

