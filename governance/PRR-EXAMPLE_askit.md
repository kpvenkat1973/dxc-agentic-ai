# PRR WORKED EXAMPLE: AskIT front desk (read it, then fill your own)

> The numbers below are **invented for this example**. Use your own from the labs.

**Team:** example   **Presenter:** Asha   **Reviewers:** Team B, Team C

## 1. What are we shipping?

| | |
|---|---|
| Agent purpose (one sentence) | Answer employees' IT questions and look up tickets; reset non-VIP passwords with a policy in front. |
| Who uses it and how many per day | 4,000 Orbit Corp employees, about 2,000 questions a day |
| What it can DO that changes data (tools) | `reset_password` only (mock in the lab). Everything else reads. |
| Owner (the person on call) | Ravi (platform), backup Meena |

## 2. The checks

| # | Area | Check | Evidence | Status | Gap → owner → date |
|---|---|---|---|---|---|
| Q1 | Quality | Exam run on the shipping version | Lab 10 tab 4, run of 21 Oct | ✅ | |
| Q2 | Quality | Every FAIL has a decision | Two FAILs in "safe write": fixed one, accepted one | 🟡 | Write the accepted risk in the register → Asha → 24 Oct |
| S1 | Safety | Red-team run, defences listed | Lab 12: D2, D3, D4 stop all 6 attacks, 0 false alarms | ✅ | |
| S2 | Safety | "Never" rules in code or policy | VIP reset forbidden by Cedar rule, tested | ✅ | |
| S3 | Safety | Policy tested with awkward inputs | Lowercase and space bypassed the rule; tool now refuses non-exact ids | 🟡 | Add the same check to `get_user` tests → Ravi → 25 Oct |
| S4 | Safety | Human yes for irreversible actions; no keys in repo | No approval step yet for non-VIP resets; SYNC.bat blocks keys | 🟡 | Add an approval step above 5 resets per hour → Meena → 30 Oct |
| R1 | Reliability | Timeouts, retries, fallback | Lab 14 settings: 20 s timeout, 1 retry | ✅ | |
| R2 | Reliability | Cold start known, progress shown | Lab 16A: cold about 1.5 s extra (example) | ✅ | |
| O1 | Observability | Every run leaves a trace | Langfuse + AgentCore traces | ✅ | |
| O2 | Observability | Alarm for errors and cost | Cost alarm only | 🟡 | Add an error-rate alarm → Ravi → 27 Oct |
| O3 | Observability | "What did it do for ticket X?" in 5 min | Tried it: 3 minutes | ✅ | |
| C1 | Cost | Cost per ticket measured | $0.0004 per question (Lab 16A tab 5) | ✅ | |
| C2 | Cost | Monthly estimate, biggest line | About $27 a month; model tokens are the biggest line | ✅ | |
| C3 | Cost | Budget alarm | Set at $100 a month | ✅ | |
| P1 | Operations | Back to previous version in 10 minutes | Never tried | ❌ | Try a rollback and time it → Ravi → before go-live |
| P2 | Operations | Kill switch | Policy engine to Enforce with no permit rules turns every tool off (default deny) | ✅ | |
| P3 | Operations | Runbook for top 3 failures | Draft only | 🟡 | Finish → Meena → 28 Oct |
| D1 | Data | Where personal data appears | Names in traces; mobile numbers never sent to the model | 🟡 | Confirm trace retention → Asha → 25 Oct |
| D2 | Data | Retention and region | us-east-1 only; retention undecided | ❌ | Decide with Legal → Asha → before go-live |

## 3. Our numbers

| What | Value | Where from |
|---|---|---|
| Exam pass rate | 86% overall; weakest: safe write 2 of 3 | Lab 10 tab 4 |
| Attacks stopped / false alarms | 6 of 6 / 0 | Lab 12 tab 3 |
| Cost per ticket / per month | $0.0004 / about $27 at 2,000 a day | Lab 16A tab 5 |
| Typical answer / cold start | 4 s / +1.5 s | Lab 14, Lab 16A |

## 4. Top 3 risks

1. Cannot roll back fast (P1): a bad release stays live while we fix it.
2. Retention undecided (D2): traces may hold names longer than allowed.
3. Spelling tricks on ids (S3): fixed for reset, not yet tested everywhere.

## 5. Decision

☐ GO  ☒ **GO WITH CONDITIONS**  ☐ NO-GO

**Because:** safety and cost evidence is strong, but P1 (Operations) is ❌ so it cannot be a plain GO.

**Conditions:**

1. Rollback tried and timed under 10 minutes: Ravi, before go-live.
2. Retention and region decided with Legal: Asha, before go-live.
3. Error-rate alarm and runbook finished: Ravi and Meena, by 28 Oct.
