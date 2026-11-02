# November 2 maintenance batch

Baseline: `b50b6561d91f19025fc781309953c09d43a99803`.

## Dependency and project maintenance

Consolidates proposed updates from #90, #89, #10, #8, #4, #85, #3, #2 and #1
on current main. Pins: pypdf 6.21.4, cryptography 50.0.2, psycopg2-binary 2.9.13,
Gunicorn 26.2.0 and pytest 9.2.0. PyPI metadata confirms Python 3.12 support;
installation and `pip check` succeed. Actions checkout/setup-python/setup-node/
upload-artifact move to v7. Official action READMEs require a Node 24-capable
runner (minimum 2.327.1); hosted CI must prove this configuration. The student
app remains Flask/PostgreSQL/vanilla JS/Gemini. No new production dependencies,
schema migration, billing setting or provider switch.

Includes AGENTS.md and all three original Saathi skills from #87. Their design,
trust and release instructions were read before implementing this batch. The
separately pinned Classroom scheduler workflow is preserved; its credentials
and schedule are unchanged. Superseded PRs can close after this batch merges.

## Reply speed: evidence and bounded change

Read-only, duration-filtered Render application logs yielded 5 preparation and
6 provider timing samples dated October 27–29. No message, note, Classroom text,
account identifier or credential was retrieved. Preparation took 2,187–3,305ms
(median 3,036ms); provider first text took 891–9,749ms (median 2,694ms).
These are separate historical cohorts, not paired end-to-end measurements or
current-release SLOs. The last-day timing query returned no matching samples;
HTTP metric responses were empty, not evidence of zero traffic. No production
99% success or p95 first-words claim follows from these samples.

The auth read previously began a transaction and needed a wire rollback before
returning the connection. Two regression checks failed on baseline: the Lease
did not delegate an autocommit assignment, and two fresh auth reads caused two
wire rollbacks. Delegate autocommit correctly, run the single auth SELECT in
autocommit, then always restore transactional mode and return the lease. After
the change the same fixture makes two fresh reads, rejects the revoked session,
and makes zero wire rollbacks. This removes one unnecessary database round trip
per authentication read; it does not remove provider waiting or cache identity.
Returning a lease also restores transactional mode for subsequent writes.

The observed service is on Render's free plan. No paid compute change, keepalive
scheme, quota bypass, model override or fabricated production benchmark is used.
New production samples are needed to quantify the deployed auth-time difference.

## Mobile keyboard and uploads

An on-screen keyboard can reduce VisualViewport height while layout viewport
and `100dvh` stay unchanged. Track visual height, coalesce resize events, and
keep the original composer/drawer above the keyboard. A temporarily reduced
empty-state layout prioritises input. Closing the keyboard restores the normal
layout; pinch zoom does not resize the app, and browser resize/pageshow work
without VisualViewport support. Draft/file/retry/Stop handlers are preserved.

Chromium regression checks disable just the new viewport controller for the
before comparison, then test the controller enabled with the same synthetic
400px visible area in a 900px layout. Cover empty/active chats, EN/GU/HI,
320/360/390px widths, zoom, retained exact draft and selected PNG. Screenshots
are clipped actual browser rendering of that simulated visible area, not an
image-generated design or physical-keyboard evidence.

## Notifications and release gates

The updated cryptography/Web Push stack runs real encryption and VAPID signing
against intercepted transport. Existing scheduler, pause/retry, revoked-session,
generic lock-screen copy and safe-click tests remain required. No real reminder,
permission, subscription or private data is changed. Actual device receipt,
physical phone uploads/IME and current-release first-word latency remain external
acceptance checks; an accepted push is not proof of phone delivery.

Local pure-Python/controller checks pass with the new packages. Disposable DB,
real Gunicorn entrypoint/streaming and Chromium gates must pass in CI. Managed
local Gunicorn process tests hit an OS `Operation not permitted` restriction
and cleanup timeouts; this is not a runtime pass and those tests are not skipped
in CI. After an authorised merge, verify Render's deploy and exact public health
revision, versioned assets and the read-only smoke checker before claiming live.

References read: https://pypi.org/pypi/PACKAGE/VERSION/json for the pinned packages;
official actions/* v7 READMEs; https://gunicorn.org/news/;
https://developer.mozilla.org/en-US/docs/Web/API/VisualViewport.
Some vendor changelog pages returned 403; compatibility is established by the
installed versions and runtime tests, not an invented changelog review.
