# Classroom title overlap — 21 October 2026

PR #77 passed 990 isolated backend/security tests, was merged and deployed, but its first owned-account live instruction probe returned a clarification. It was recorded as a failure, not a successful instruction read. Optional follow-up/cold-reload checks were not run in that session.

Read-only inspection of the actual persisted user/assistant pair and Classroom metadata confirmed that the named assignment was available and had a non-empty description. Spacing after the hyphen was already normalized correctly. The important difference from the fixtures was a separate generic assignment whose whole title was the suffix of the requested subject-prefixed title.

Synthetic reproduction: the owned selected course contains **BIO- Assignment 1**, **Assignment-1**, and **BIO-Assignment 10**. Asking `What do I have to do in "BIO-Assignment 1"?` matched both the subject-prefixed title and the generic suffix title, so the reader asked for clarification. Six new unit cases failed before the fix; three existing suffix/Unicode cases selected by the same test filter passed.

The fix compares the spans of complete title occurrences in the current query (or the prior user-selected reference). An occurrence wholly contained in a longer matched title no longer counts as a separately named assignment. Equal title occurrences retain duplicate rows and require subject disambiguation. A short title independently mentioned elsewhere still counts: `Explain BIO-Assignment 1 and Assignment-1` asks for clarification. The existing numeric/Indic boundaries, owner/course selection, source refusal, consent, persistence and no-AI behavior are unchanged.

Before publication:

- Focused source/detail suite: **159 passed**.
- Full local Python suite: **703 passed / 299 PostgreSQL cases skipped**, 15.54 seconds. Skips are not passes.
- Added six unit and six PostgreSQL cases, including EN/GU/HI through both chat transports, exact replay and persisted read-back with distinct source bodies.
- Patch whitespace passed. Full CI and a fresh post-deployment live read remain required before claiming recovery.

No private teacher instructions, course names or account identifiers are committed. This correction reads original descriptions; attached-file contents remain unread. No production success-rate, first-word latency or physical-device certification is claimed.
