# Read-only Classroom beta

The integration is off until configured and tested with a permitted student account. Google login is a separate feature. No hosting/domain change is required by this code.

## Owner configuration

1. In a Google Cloud project, enable the Classroom API, configure an OAuth consent screen and add authorized test students. School-admin authorization may be necessary.
2. Register a Web application OAuth client and the exact HTTPS callback `https://<existing-site>/api/classroom/callback`.
3. Set `CLASSROOM_CLIENT_ID`, `CLASSROOM_CLIENT_SECRET`, `CLASSROOM_REDIRECT_URI` and an independent persistent Fernet key in `CLASSROOM_TOKEN_KEY` through server environment settings. Generate the key privately; never commit, share, log or paste it into frontend configuration.
4. Requested scopes are only `classroom.courses.readonly` and `classroom.coursework.me.readonly`. Google describes the latter as permission to view own coursework and grades; the importer deliberately does not request or store grade fields. No classmates/rosters or Classroom write scopes.
5. Keep `CLASSROOM_ENABLED=false` until code is merged, migrations applied and configuration verified. Enable only for authorized beta testing.

## Acceptance

Open Study → Google Classroom. Confirm separate storage permission, authorize the selected Google account, refresh the course list, select up to three own-student courses and manually sync. Check an assignment with a deadline and one without. Confirm adding a task to Planner; a retry must reuse that task. Planner completion never submits the work in Google Classroom.

Check course deselection, a changed/deleted assignment, revoked access and school-admin denial. A failed or incomplete sync must retain previous records and show failure. Check disconnect with and without removing imports; Planner tasks stay. Google token revocation can fail; if so remove access manually in Google account settings. Account deletion removes stored connections/imports; remove remote Google access separately.

Each course is capped at five pages of 100 assignments; larger imports fail explicitly without applying partial snapshots. Manual sync is limited to once per minute per connection. A separate opt-in enables six-hour refresh through protected POST /api/cron/classroom with X-Cron-Secret; the owner must configure an external scheduler. Changing course selections disables scheduled sync until reviewed again. Each available selected assignment can be explained by AI only after separate permission; it creates neither a submission nor a Planner task. Official submission-status retrieval is not provided; check the original Classroom link. Live Google verification remains required. See CARE_CLASSROOM_RELEASE.md for retry/backoff and acceptance checks. Tokens are encrypted server-side and excluded from exports. Imported instructions never become system instructions or automatic AI context.

References reviewed 8 October 2026:
- https://developers.google.com/workspace/classroom/guides/auth
- https://developers.google.com/workspace/classroom/reference/rest/v1/courses/list
- https://developers.google.com/workspace/classroom/reference/rest/v1/courses.courseWork/list
- https://developers.google.com/workspace/classroom/reference/rest/v1/courses.courseWork
- https://developers.google.com/identity/protocols/oauth2/web-server
