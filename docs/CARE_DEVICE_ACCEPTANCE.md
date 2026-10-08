# Care release acceptance — required real evidence

Clinical gate remains off. This document is an executable manual acceptance procedure, not a claim of clinical safety or physical-device delivery.

Use a non-medical fixture named `Test routine` with a neutral instruction such as `Check the calendar`. Test two accounts and consented devices. Never test using an important real medicine schedule.

| Check | Expected result | Evidence required |
| --- | --- | --- |
| Android Chrome / installed iOS Safari / desktop | Device support accurately shown; permission is requested only after action | Browser/OS version and observed permission state |
| Foreground / closed tab / locked screen | Distinguish in-app display, service acceptance and physical receipt | Scheduled time, server attempt, service result, device receipt separately |
| Denied / revoked permission / expired endpoint | Clear unavailable state; no success claim from an attempted send | UI and sanitized server result |
| Quiet hours / digest / timezone / DST | Respect explicit settings, avoid double notifications | Fixture schedule and timestamps |
| Pause / resume / snooze | Pausing stops future alerts; snooze does not edit clinician timing | Device observations and occurrence log |
| Logout / switch account | No sensitive old-account content or notifications on the shared device | Two-account device test |
| Care sharing pending / accepted / changed / revoked / expired | Only selected fields after bilateral consent; changes reset acceptance | Two-account visibility and denied access after revocation |
| Instruction correction | Elapsed/reported records retain original instructions; future pending records reflect confirmed edit | History and current views |
| Export / delete | Owned records exported; account removal deletes stored care records; tokens not exported | Sanitized fixture export and test database checks |

Clinical review must independently inspect decimal/unit errors, multilingual/illegible transcription, duplicate schedules, missed-dose wording, user-entered recurrence, instructions and patient comprehension. No automatic dose changes, therapeutic diet allocations, emergency monitoring or caregiver messaging are implemented. A qualified reviewer must record reviewer/date/decision and required changes before enabling the clinical gate. Do not place patient data or a reviewer's private details in the public repository.

GitHub Classroom scheduling is deliberately excluded from this protocol: it is not a reliable medication clock. Phone receipt and clinical acceptance cannot be proven by mocked CI, log inspection or an AI review.
