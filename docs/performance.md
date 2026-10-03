# Loading and reply performance

The UI palette and layout are unchanged by this update.

## Findings and changes

* The Render blueprint configured four Gunicorn threads. Long AI streams occupy threads for their lifetime and can queue unrelated requests. The blueprint now configures eight threads, matching the existing eight-connection database pool. Render must apply the updated start command for this change to take effect. This is more headroom, not an unlimited-concurrency guarantee.
* Chat startup waited for the profile before fetching message history. History now begins when the conversation list is available, concurrently with the profile, with one consumed promise rather than a duplicate request. No private data is stored in a shared cache.
* Authentication already queries the user on every API request. That same request now reuses validated plan and language fields, removing two additional user queries on chat startup before generation. Session revocation is still checked on each request; there is no cross-request authentication cache.
* Public CSS and JavaScript are gzip compressed with a bounded compression cache. Versioned URLs may be cached for one hour. Unversioned assets still revalidate. APIs, signed-in HTML, streams, and the service worker are excluded. Local aggregate CSS/JS size decreased from 206,346 to 66,532 bytes with gzip (67.8%). This is transfer size, not a measured page-speed improvement.
* Normal-mode instructions request two to four sentences for simple questions while retaining detailed answers when needed.
* Responses expose application preparation duration in Server-Timing. It excludes proxy/network transit, Gunicorn queueing and streamed generation; do not equate it to total reply latency.

## Hosting and provider limits

The blueprint uses Render's free plan. Render documents a shutdown after 15 idle minutes and approximately one minute to resume: https://render.com/docs/free . These cold starts cannot be removed with frontend CSS or application caching. No paid plan was enabled.

Public endpoint checks from this workspace returned HTTP 200 but took about 11–14 seconds end to end. Without Render logs or server timing from the previous deployment, that does not isolate network, proxy, server queue or cold start time. No authenticated production prompt or real provider timing was available. Existing token streaming is retained; model latency and quota errors cannot be claimed fixed by this patch.

## Verification

142 backend tests passed covering the new compression/privacy/session behavior and existing core, reply recovery, security and reliability paths. Eight JavaScript behavior suites passed. Browser tests cover 1280px and 390px and assert that history starts while the profile is pending and is fetched only once.

## October 3 follow-up

Updated three stale CI expectations to reflect the single voice conversation control, accessible New chat button and eight-thread blueprint. Chat loads now reject older responses even when the user switches A → B → A. Failed history loads show a retry control and block sending until history is recovered; saved drafts survive the retry. The release label now distinguishes this deployment from September 26.

Public production checks from the execution workspace returned HTTP 200 for the homepage and a versioned stylesheet in 6.56s and 6.50s respectively, while both reported `Server-Timing: app;dur=0.4` milliseconds. The stylesheet was gzip encoded and carried the intended one-hour cache policy. This confirms that application timing and asset compression are deployed, but does not establish a user-perceived speed improvement or isolate the remaining network/proxy/queue delay. The live Gunicorn command cannot be verified without hosting access.

Local verification: 214 Python tests passed, 31 database integration tests require the isolated PostgreSQL CI service; nine JavaScript behavior suites passed. Added out-of-order history and retry tests plus desktop/mobile browser checks for failed history, blocked sending and draft restoration after retry/reload. Production AI first-text and full-response timings still require a signed-in account; no credentials or provider request were used in this audit.
