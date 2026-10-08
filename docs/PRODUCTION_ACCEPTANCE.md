# Production acceptance — 8 October 2026

- Scheduler run 37818528429 ran both the selected-course refresh and general alert dispatcher successfully. Zero accounts were due and zero alerts were eligible. This proves cron authorization/configuration, not physical delivery. GitHub scheduling remains best-effort; use neither this schedule nor free hosting for guaranteed medicine timing.
- The selected Gemini model and credentials were reachable. A public demo math reply succeeded, taking around 26 seconds including HTTP latency. One bounded retry now covers explicit 5xx rejection only; access/quota failures, ambiguous timeouts and partially streamed output are never automatically replayed. No paid service was added.
- Live startup logs identified a missing FLASK_SECRET_KEY, which previously regenerated session signatures on every restart. A securely generated persistent key was installed directly in Render. The production entry now refuses to start without a sufficiently long configured key. Local development retains its normal behavior. An existing cookie validates across two real backend processes in the restart regression test. Browser-session versus 30-day login remains the user's explicit choice.
- 389 backend/PostgreSQL checks and five browser widths passed for PR20, including a joined onboarding → selected Classroom import → separate AI consent → Planner → practice/result history → general reminder journey and owner isolation. Public production smoke checks passed. Provider calls in the integrated journey are fixtures; it is not proof of public Google approval.
- Google Cloud Console was unavailable to the audit browser. Production audience, sensitive-scope review and actual Google approval cannot be inferred from a working test-account connection. Follow GOOGLE_CLASSROOM_VERIFICATION.md in the owner's existing project. No approval or console publication is claimed.

## Outstanding external acceptance

On the user's physical phone, enable Saathi notifications, use Account → Send test alert, lock the phone and verify receipt. Then schedule an ordinary non-medical reminder and allow for best-effort scheduler delays. Check Account's last dispatch and failure status. A push-provider acceptance is not a receipt confirmation.

In Google Auth Platform, check Audience and Verification Center for the existing Saathi project and the two requested read-only scopes. Preserve accurate contacts/domain ownership and submit the required application evidence. Do not paste passwords, client secrets or tokens into chat.
