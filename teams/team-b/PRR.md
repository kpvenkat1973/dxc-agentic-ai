# Production Readiness Review (PRR): AskIT

**Team:** team-b   **Date:** Thu 22 Oct 2026   **Presenter:** ______   **Reviewers (other teams):** ______ , ______

> How to fill this in (25 minutes, in your team): one line per check. **Evidence** = where a reviewer can SEE it (a lab tab, a file, a number).
> **Status:** ✅ ready · 🟡 gap, with an owner and a date · ❌ not ready. A visible gap with an owner beats a hidden one.
> **Rule:** any ❌ in *Safety* or *Operations* means the answer cannot be a plain GO.
> Look at `PRR-EXAMPLE_askit.md` first. Edit this file; do not start from a blank page.

## 1. What are we shipping?

| | |
|---|---|
| Agent purpose (one sentence) | |
| Who uses it and how many questions per day | |
| What it can DO that changes data (tools) | |
| Owner (the person on call) | |

## 2. The checks

| # | Area | Check | Evidence (where to see it) | Status | Gap → owner → date |
|---|---|---|---|---|---|
| Q1 | Quality | The eval exam was run on the exact version we ship | Day 10 · Lab 10 · tab 4 | | |
| Q2 | Quality | Every FAIL in the exam has a decision: fix it or accept it, in writing | | | |
| S1 | Safety | Red-team run done; the set of defences is listed | Day 11 · Lab 12 · tab 3 | | |
| S2 | Safety | "Never" rules are enforced by code or policy, not only by the prompt | Day 12 · Lab 16B · tab 4 | | |
| S3 | Safety | The policy was tested with awkward inputs (spelling, spaces, missing ids) | Lab 16B · tab 5 | | |
| S4 | Safety | Irreversible actions need a human yes; no keys in GitHub, wikis or chat | | | |
| R1 | Reliability | Timeouts, retries and a fallback are set; a failing tool is shown honestly | Day 11 · Lab 14 · tab 3 | | |
| R2 | Reliability | The cold start is known and the screen shows progress | Day 12 · Lab 16A · tab 3 | | |
| O1 | Observability | Every run leaves a trace we can open | Langfuse / AgentCore trace | | |
| O2 | Observability | An alarm exists for errors and for cost | | | |
| O3 | Observability | One person can answer "what did the agent do for ticket X?" in 5 minutes | | | |
| C1 | Cost | Cost per ticket is measured, not guessed | Day 10 · Lab 10 · tab 3 | | |
| C2 | Cost | Monthly estimate at the expected volume; biggest cost line named | Lab 16A · tab 5 | | |
| C3 | Cost | A budget alarm or cap is set | | | |
| P1 | Operations | We can go back to the previous version in 10 minutes | | | |
| P2 | Operations | A kill switch exists: turn the agent off and humans take over | | | |
| P3 | Operations | A runbook covers the top 3 failures | | | |
| D1 | Data | We know where personal data appears (prompts, logs, traces) | | | |
| D2 | Data | Retention and region are decided | | | |

## 3. Our numbers (copy them from your labs)

| What | Value | Where from |
|---|---|---|
| Exam pass rate (overall, and the weakest category) | | Lab 10 · tab 4 |
| Attacks stopped / false alarms (Lab 12 best defence set) | | Lab 12 · tab 3 |
| Cost per ticket and per month at our volume | | Lab 10 · tab 3, Lab 16A · tab 5 |
| Slowest and typical answer time, and the cold start | | Lab 14, Lab 16A · tab 3 |

## 4. Our top 3 risks (rank them, worst first)

1.
2.
3.

## 5. Decision

☐ **GO**  ☐ **GO WITH CONDITIONS**  ☐ **NO-GO**

**Because:** ______

**Conditions (each with an owner and a date):**

1.
2.

## 6. How the board scores you (5 criteria, 0 to 5 each, 25 points)

Evidence is real and visible · Gaps are stated honestly · Risks are ranked sensibly · The decision fits the evidence · Conditions are specific (who, what, when).
Pitch: 3 minutes + 1 minute questions.
