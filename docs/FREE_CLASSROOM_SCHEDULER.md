# Free beta Classroom refresh

This repository is public. Standard GitHub-hosted Actions runners can run this workflow without purchasing Render compute. Keep the repository public and do not enable paid/larger runners. No paid service is provisioned by this change.

## Activation (owner-only)

1. Merge the workflow and backend together. Keep `CLASSROOM_SCHEDULER_READY=false` on Render until a real job is verified.
2. Generate a new random scheduler secret privately. Put the same value in Render as `CLASSROOM_CRON_SECRET` and GitHub repository Settings → Secrets and variables → Actions → New repository secret as `CLASSROOM_SYNC_SECRET`. Do not paste it into chat, commits, logs, screenshots or a URL. This key authorizes only the Classroom job; it does not replace medication/reminder `CRON_SECRET`.
3. In GitHub Actions repository Variables, add `CLASSROOM_SYNC_ENABLED=true`. It is a non-secret activation flag. The workflow is otherwise skipped, including on forks.
4. From Actions → Classroom background refresh, run the workflow on **main**. Check a successful job. An idle result of zero proves the protected endpoint is reachable, not that student data synced.
5. Set `CLASSROOM_SCHEDULER_READY=true` on Render and redeploy. In the student's Classroom panel, save the separate background-refresh preference for already-selected courses. Run the job again and verify Last successful sync changes and an actual new/changed assignment imports. Never enable this preference silently for a student.
6. Check provider denial, disconnect and course deselection in a permitted test account. Changing courses disables the preference. A failed complete snapshot retains the old assignments. Switch the repository activation variable to false and the Render readiness flag to false to stop this scheduler. Students can disable their preference separately.

The workflow requests no OAuth secrets or student tokens; it sends only the scheduler secret to the fixed Saathi endpoint over HTTPS. HTTP redirects are rejected. It processes at most eight due accounts per run, stops when idle, has a seven-minute call budget and prevents overlapping workflows. Each account normally becomes due six hours after its last success. Error/backoff is handled by the server. Capacity and lateness must be monitored as the beta grows.

## Limits

GitHub schedules are best-effort: runs can be delayed or dropped, only main schedules run, and inactivity for 60 days can disable a public repository's schedule. Render Free can sleep; this is no guarantee of an always-on service or exact refresh timing. Do not use this workflow for medication delivery, emergencies or time-critical reminders. No push/email/AI work is triggered by it.

Testing-mode Google refresh tokens can expire; reconnect when asked. This job cannot bypass Google's testing/verification rules. Secrets cannot currently be installed with the connected GitHub plugin; the owner must enter the repository secret once through Settings. Do not substitute a public variable for the secret.

Sources:
- https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule
- https://docs.github.com/en/billing/concepts/product-billing/github-actions
- https://render.com/docs/free
