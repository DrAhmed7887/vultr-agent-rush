# Stress test, 4 Nov 2026

Run against the live demo (`64-177-33-215.sslip.io`, one vc2-2c-4gb VM), three rounds, fixing between them. The script is kept outside the repo; it does the following.

| Check | What it does | Round 1 | Round 3 |
|---|---|---|---|
| A1 | 10 sessions at once | pass | pass (p95 0.8 s) |
| A2–A3 | 16 quizzes at once; a run that didn't happen must not be graded | 4 busy runs produced fake quiz cards | all 16 ran (median 3.4 s, max 8.0 s); no fake grades |
| A4–A5 | break-him chips and beyond-the-guard tests during that load | pass, some busy | pass: timeout, OOM, blocked; network unreachable, fork bomb stopped, no secrets |
| B1–B3 | 6 teach turns at once (real Vultr inference) | the doubling rule was flagged "unkind" by the safety model | all right: 4 cures at 40/40, tenths-first partial, doubling stopped by the sandbox |
| C1–C18 | oversized bodies, bad audio, forged homework, path traversal, bad ids, broken JSON, fake sessions, rate limits, forged `X-Forwarded-For` | oversized bodies gave 502 | all refused correctly (413, 400, 404, 422, 429) |
| D1–D4 | afterwards: health, containers left, tracebacks, memory | a ClientDisconnect traceback | healthy, 0 containers left, 0 tracebacks, 626 of 3,910 MB used |

**Fixes made between rounds:**
- 4 sandbox slots instead of 2, with an 8 s wait.
- A busy quiz or test now returns 503.
- Caddy refuses oversized bodies before they reach the app.
- The safety check reads fraction words as maths ("bottoms" → "denominators") only in sentences that are clearly about maths, so "show me your bottom" is still checked as written.
- The safety check now runs before the compiler.
- Thoth's objection now means the brain isn't kept.
- The anti-smuggling check now sees helper calls.
- Tighter global and daily caps.
- No access log, so session ids don't end up in the logs.
