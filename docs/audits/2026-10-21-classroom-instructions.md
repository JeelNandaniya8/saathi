# Classroom assignment instructions — 21 October 2026

## Report and reproduction

After a pending-work list, a student asked what a named assignment contained and what they had to do. Saathi claimed it could see only titles/deadlines and asked the student to paste the instructions.

The existing Google read-only sync already stores `courseWork.description` in `classroom_assignments.instructions`. The chat query selected only status metadata and always used the pending-list formatter. Some named/quoted instruction requests missed that reader entirely. This was a routing/read-path defect, not evidence that the account lacked a connection.

Before changing production code, the new unit suite produced **19 failures / 10 passes**. Nine instruction-query cases were either unrouted or routed as status lists; the remaining failures specified the missing contextual/detail formatter behavior. All examples and instructions in the repository are synthetic.

## Minimal change

- Recognize direct instruction/content questions in English, Gujarati, Hindi and Roman Gujarati. Preserve quoted literal assignment titles without treating quoted commands as source permission.
- Resolve complete titles against the signed-in owner's available assignments in selected courses. Duplicate titles require a matching subject or clarification. Preserve Indic vowel marks; `Assignment 1` cannot select `Assignment 10`.
- A generic “this assignment” can refer to the immediately preceding user-selected title. Assistant prose cannot select a different assignment. Ambiguous lists and unknown/new titles ask for the exact title and subject.
- Fetch only the selected row's stored description and original Classroom URL. Display original instructions with line breaks, account-timezone deadline and checked timestamp. Escape source text so it cannot execute a save, HTML or a remote Markdown image.
- State explicitly that attached-file contents have not been read. Empty descriptions remain empty; no inferred requirements. Existing selected-assignment AI explanation consent, OAuth scopes and schema are unchanged.
- Both chat transports retain existing Stop, persistence and request replay guards. Contextual source reads cannot use general-AI regeneration.

No teacher instructions are sent to an AI provider by this path. It is a deterministic read, not an AI-generated breakdown or a completed submission.

## Validation before publication

- Focused routing/source/detail suite: **141 passed**.
- Full local Python suite: **685 passed / 293 skipped**, 11.80 seconds. The skipped cases require isolated PostgreSQL; they are not counted as passes.
- Browser JavaScript/race/cancellation/receipt/quota suites passed; patch whitespace passed.
- Added 33 unit cases and 10 PostgreSQL integration cases. The integration cases cover both transports and EN/GU/HI, stale denial history, sharing disabled, owner/course isolation, exact request/replay, persisted read-back, contextual follow-up, ambiguity and real refresh failure. CI must execute them before merge.

## Limits

The fix reads Classroom descriptions, not the contents of attached Drive/PDF/image files. Ambiguous references require clarification. No live account's private assignment bodies are included in this report. Production retest and exact deployment provenance are to be recorded in the pull request after CI and deployment; this document makes no production success-rate, latency or mobile certification claim.
