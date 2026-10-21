# Classroom attachment recovery — 21 October 2026

## Reproduced before implementation
The existing selected-course sync requested description and deadline fields but
omitted materials. The old chat instructions reader could show a description,
but could not know the attachment list or read its contents.

Test-only commit: d151e3a05ea5e413e1ce3fe74fbbd397c6ba174b.
CI run 39627697373, job 119317218745: **9 failed, 1002 passed in 276.54s**.
The sync assertion specifically failed because its fields omitted materials.
All fixtures and example files are synthetic; no owned teacher text is included.

## Change and boundaries
- Ordinary selected-course sync stores at most 20 Drive attachment references,
  never file contents. NULL means an older unchecked import; [] means the latest
  import listed no Drive files. Other material kinds may still exist.
- A separate, disabled-by-default Google OnePick flow requests drive.file only
  for the selected imported file. Existing Classroom scopes/refresh tokens are
  unchanged. State, PKCE, account session, course selection and source metadata
  bind the one-use callback. Broader returned scopes or another selected file
  are rejected. No Drive refresh token is stored.
- A short-lived encrypted grant permits fixed-host, no-redirect downloads.
  PDFs/images are bounded at 5 MB; Google documents/slides/sheets export as PDF.
  Unsupported types, expiry, permission failure and changed bytes fail closed.
  Source ownership and selection are checked again after provider I/O.
- Preparing a file does not call AI or create a conversation message. The Chat
  review action uses chooseFiles and the existing Send/upload allowance path.
  Existing content, mode, request ID and file-only choice survive failed
  preparation and recovered-attachment matching. New attachments default to
  file-only. Download cancellation and changes to the draft/chat prevent
  replacement. The user must explicitly press Send to request analysis.
- Existing upload, Stop, retry, saved receipt and citation handling are reused.
  Downloading to a draft does not spend the send allowance, like local selection.
- New copy is available in English, Gujarati and Hindi. No login redesign.

## Required owner configuration before enabling
The feature remains off unless CLASSROOM_FILE_PICKER_ENABLED=true. With it off,
the UI offers original Drive links and manual PDF/image attachment instructions.

In the existing Google Cloud project, enable Google Picker API and Google Drive
API. Reuse the existing web OAuth client and its registered
CLASSROOM_REDIRECT_URI (/api/classroom/callback). Google documents the redirected
OnePick flow for web apps: request only drive.file, prompt=consent,
trigger_onepick=true, optional file_ids, and verify picked_file_ids in the return.
No new browser API key or browser-visible token is required.

Official references:
- https://developers.google.com/workspace/drive/picker/guides/desktop-mobile-picker
- https://developers.google.com/workspace/drive/api/guides/api-specific-auth
- https://developers.google.com/workspace/drive/api/reference/rest/v3/files/get

Enabling APIs and granting the user's actual per-file Google consent have not
been performed by this patch. No permission is granted automatically.

## Validation
Local execution is unavailable: the supplied workspace is offline.
Implementation validation is recorded in PR #79 checks and its final tested-head report; the red reproduction run above is deliberately kept separate.
The CI timeout is raised from 10 to 12 minutes to retain the full existing suite
plus additional disposable-PostgreSQL file checks. No existing check is removed.

## Remaining limits
No live Google Picker or owned attachment-to-AI analysis has been verified.
Scanned PDF quality, provider availability, native-document PDF export behavior,
and actual citations require a separately authorized live test after setup.
A later export that changes bytes is rejected for the same grant. Expired grants
require fresh selection; they do not overwrite a recovered draft automatically.
The synthetic browser checks do not certify a physical phone, notifications,
production >=99% success, or p95 first text below five seconds.
