# Classroom public verification preparation

Status: a permitted personal test account has connected and imported coursework, as reported by the owner on 8 October 2026. This does not establish public Google approval. Keep the current client in Testing until Google approves the required production configuration. No verification request has been submitted by this change.

## App and policy evidence

- App name: Saathi. Keep Branding, consent screen and homepage consistent.
- Homepage: https://saathi-md5w.onrender.com/
- Privacy: https://saathi-md5w.onrender.com/privacy
- Terms: https://saathi-md5w.onrender.com/terms
- Support: https://saathi-md5w.onrender.com/support
- Exact current callback: https://saathi-md5w.onrender.com/api/classroom/callback
- Support/developer contacts must be monitored by the owner. Do not claim domain ownership without proof. Complete Google's requested domain/brand verification in the owner's project. A provider-owned shared domain is not automatically a domain the owner can verify; resolve the console's actual requirements before public launch. No domain purchase is authorized.

## Narrow scope justifications

`https://www.googleapis.com/auth/classroom.courses.readonly`: list only active courses where the authorizing account is a student, so that the student can choose up to three courses to import. Request fields id/name only. No roster, teacher/classmate profile, messages, course writes or deletion.

`https://www.googleapis.com/auth/classroom.coursework.me.readonly`: retrieve the selected courses' own-student assignment title, instructions, source link and due information for study planning. Although Google describes this as coursework and grades access, this importer requests no grade fields and never retrieves grades or official submission status. The token scope's equivalent own-student read-only name is accepted. No coursework/submission writes or automatic submission.

Explain the actual opt-in data use accurately: imports remain private, encrypted refresh tokens stay server-side, exports omit tokens, disconnect attempts revocation, imports can be deleted, account deletion removes connections/imports, existing local Planner tasks remain after disconnect. A single selected assignment reaches the configured AI only after its own explicit permission. There is no background AI processing. Do not claim provider/model data-use terms that have not been checked in the actual production account.

## Demo recording for the owner

Use a permitted test account and fixture assignment with no private student, school or medical data. Record in English: homepage/privacy/support → signed-in Study → Google Classroom → storage consent → selected Google account → both requested scopes → course list → course selection → manual sync → imported due and no-due assignments → original source → explicit Planner confirmation → optional selected-assignment AI consent → background-refresh preference (only if verified) → disconnect/remove imports. Show the app name and OAuth client ID required by Google's reviewer; never expose client secrets, token keys, authorization codes or refresh tokens. Preserve the evidence of who owns the account and courses outside the public repository.

Upload only this sanitized demo if authorized by the owner. In Google Auth Platform, declare the two exact requested scopes under Data Access, complete Branding and follow Verification Center's current instructions. Review all policy assertions personally before submission. Google reviews/approves the application; code or a publish toggle cannot replace that approval.

Source: https://developers.google.com/identity/protocols/oauth2/production-readiness/sensitive-scope-verification
