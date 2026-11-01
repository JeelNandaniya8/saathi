# November trust follow-up

Baseline: main `73d10ca6707cb6d5e59662bcbb41039aa683cdcb` (PR #88).
PR #87's AGENTS.md and all three Saathi skills were read; that guidance PR
remains separate. Existing stack, right-side History, one composer, stored
source permissions, attachment/retry controllers and saved-object handlers stay.

## Reproduced before changing behavior

- Actual chat keydown handler submitted on composing Enter and keyCode 229.
  These two checks failed; Shift+Enter and ordinary Enter behaved correctly.
- Ctrl/Cmd+K focused a still-hidden History search before opening the drawer;
  the registered-handler test failed to obtain focus.
- The first Chromium run also caught shared workspace search competing for
  that shortcut. Chat now owns History search; Dashboard keeps workspace search,
  and Chat's explicit workspace search button stays available.
- Repeated assignment-detail follow-ups lost the original user-selected title
  in English, Gujarati and Hindi (three failing tests). English became an
  ambiguous generic assignment reference; Gujarati/Hindi left the local reader.
- Public health returned a release label shared by multiple revisions. PR #88's
  three changed assets were fetched and matched its local SHA-256 bytes, but
  health alone could not establish the deployed commit.

## Changes and intended experience

Writing comes first: accepting a native-script candidate keeps the draft;
ordinary Enter still sends. History opens with keyboard focus inside it, its
search shortcut works from the collapsed state, and mobile Tab/Shift+Tab stay
inside the modal drawer. Escape/close restore the trigger. Native dialogs keep
their own Escape behavior. No new translated labels or alternate composer.

Assignment follow-ups retain the nearest original user request across at most
five prior exchanges. Assistant text never supplies a title. Refusals, new
topics, attachments and non-dialogue rows stop inheritance; ambiguous titles
still require clarification. Reads use existing ownership, source consent,
freshness and deterministic instruction formatting, without AI generation.

Health includes only a validated full Render Git SHA, or null when unknown.
Use `python scripts/smoke_test.py URL --expected-revision FULL_MERGE_SHA` after
release. A healthy stale/missing revision fails this check. No secrets, instance
identifiers or user data are returned. No schema/configuration changes required.

## Verification and open gates

Focused tests and all local Python/controller gates are run before publishing;
PostgreSQL and real Chromium checks must pass in CI before merge. CI exercises
EN/GU/HI keyboard behavior at 320/360/390/768/1280px and captures the 360px History
drawer. Existing fixtures cover quota/provider failures, exact retries,
cancellation, receipt read-back, timezone boundaries and privacy exclusions.

These are synthetic-provider checks, not live success rates or first-word SLOs.
The current browser profile has no recorded Saathi sign-in; protected live
Classroom/AI/PDF checks are unverified. No login/Google consent is performed.
Physical phone upload/IME/keyboard, actual reminder receipt, independent native
speaker review and independent live trust retest still need external evidence.
No production records, notification permissions, billing or quotas are changed.

Next usability experiment: on a student's real phone, compose a Gujarati question,
accept a candidate, open/search/close History and resume the exact draft. Record
accidental sends, focus loss and task completion time before claiming improvement
in real student outcomes.
