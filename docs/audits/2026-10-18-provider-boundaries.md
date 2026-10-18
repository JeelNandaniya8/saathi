# Provider retry boundaries — 18 October 2026

Baseline: `0298fb32625e71cdc7d6938237431c4067e2da4e`, release
`2026-10-18-map-reopen`. Prior Normal map generation/receipt work is in PR57/58.

Read-only Render logs contain genuine historical HTTP503/AI_BUSY and startup
timeouts (October 13–17). The October 16 busy rejections used the fast streaming
path. Those older logs omit attachment counts, so they cannot establish which
individual PNG/PDF request caused each error. No new busy event was found in the
retrieved October 18 window; absence of a log is not a successful live test.
The current source already routes Normal attachments to the study model.

## Reproduce before changing the transport

Eight controlled cases failed against the baseline:

- Four combinations of fast/study and stream/JSON automatically retried after
  one second despite an HTTP-date `Retry-After` ninety seconds in the future.
- Two compatibility-recovery cases started a second provider call after their
  forty/sixty-five-second attempt budget had already expired.
- Two short-remaining-budget cases assigned a five-second connect plus a
  one-second read timeout when only two seconds remained.

These are reproduced application retry defects, not proof that every historical
provider outage had the same cause. All reproductions used mocks without network,
production quota exhaustion, real waiting or account secrets.

## Minimal change

- Parse HTTP-date and integer Retry-After values consistently for busy and quota
  errors. Do not shorten a valid two-hour delay to one hour. Unknown/malformed
  supplied retry headers do not trigger an immediate automatic retry.
- Keep the existing maximum of two attempts, models, fallback selection and
  forty/sixty-five-second startup budgets. Check remaining time before another
  provider attempt or model discovery. Connect/read timeout allocations share
  the remaining budget rather than forcing another six seconds.
- Preserve sanitized errors, exact request payloads, ownership, transactions and
  all existing quota checks. No UI, schema, vendor, model or paid-resource change.

This is retry-attempt scheduling and socket timeout allocation. Requests' socket
timeouts are not a hard total execution deadline; discovery, upload, trickling
responses and provider-side work can still extend elapsed wall time. No first-word
p95 or guaranteed cancellation of provider billing is claimed.

## Regression scope

Unit cases exercise both header forms, quota versus busy, malformed values,
expired budgets and short timeout allocations. Six isolated PostgreSQL cases use
real PNG/PDF multipart requests or Normal maps, both chat transports, and the real
transport with fixture provider responses. They check no records/charge after
failure; an exact user retry after the cooldown; unchanged provider payload,
file-only flag and original name; committed receipt/reopen; and replay without
another provider call, record or quota charge. Skipped local database cases are
not passes; the exact-candidate CI result belongs in the PR/release record.

Protocol reference: [RFC9110 section10.2.3](https://www.rfc-editor.org/rfc/rfc9110.html#section-10.2.3)
permits both HTTP-date and delay-seconds. [Google troubleshooting](https://ai.google.dev/gemini-api/docs/troubleshooting)
distinguishes service unavailability from quota/resource exhaustion. Neither
reference proves that a particular user's request is now reliable.

## Remaining live limits

The prior cloud-browser credential-state restriction remains a limitation for
protected upload/reopen observations. Physical phone keyboards/uploads, actual
notification receipt, genuinely connected Classroom data, representative live
>=99% completion and p95 first useful words <5s remain unverified. No independent
review or seven-day pilot has been completed. Do not infer 10/10 from CI.
