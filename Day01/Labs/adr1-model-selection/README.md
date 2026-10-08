# ADR Exercise 1 — Model & Deployment Decision

**Time:** 10 min for ADR v1 · then the trainer gives an update · ~10 min for ADR v2
**Work:** individually · **Output:** two files pushed to your fork
**Helper page:** http://localhost:8765/Day01/Content/ai_deployment_landscape.html (calculator, trade-offs, scenario game)

---

## The client

**Bharat Suraksha Insurance** (fictional) — mid-size health & motor insurer, HQ Mumbai, 6 million policyholders, about 3,200 claims staff and agents across India.

Claims adjusters spend most of the day reading long hospital and garage documents, hunting for clauses in policy wording, and writing customer letters. Management wants **ClaimsCopilot**, an AI assistant that does three jobs:

| # | Workload | Volume | Size of one request | Speed needed |
|---|---|---|---|---|
| 1 | **Claim file summary** — summarise hospital discharge summaries & claim PDFs for the adjuster | 40,000 claims / month | ~25,000 tokens in, ~800 out | Within 2 minutes (can run in background) |
| 2 | **Policy Q&A (RAG)** — adjuster asks "is this procedure covered under plan X?" | 2,500 questions / day | ~4,000 in, ~400 out | Answer in under 8 seconds |
| 3 | **Customer letters** — draft approval / rejection letters in English and Hindi | 15,000 / month | ~1,500 in, ~500 out | Within 1 minute |

**Traffic pattern:** weekdays 9–11 am is 3× the normal load. Festival and monsoon seasons bring spikes.

## What you know

- Claim files contain **personal and health data** of customers.
- Compliance's current position (not yet formally signed off): *"Customer data should stay in India wherever possible."* India regions exist on all three public clouds.
- IT already has an **AWS enterprise agreement** and a **VMware data centre in Chennai** with **2 spare GPU servers** (4 × 80 GB GPUs each) bought for an analytics pilot that never launched.
- The team: **3 developers + 1 SRE**. No dedicated MLOps / GPU engineer.
- **Budget:** about **USD 4,000 per month** (≈ ₹3.5 lakh) for AI running costs.
- **Timeline:** pilot with 200 users in **8 weeks**; all 3,200 users within 12 months.
- **Quality bar:** summaries must have fewer than 2% factual errors; a human adjuster always approves before anything is sent to a customer.

## Your task (10 minutes)

Write **ADR v1**. It must clearly state:

1. **Deployment path** — public cloud, private / on-prem, or open-source / 3rd-party platform (or a mix, per workload).
2. **How you pay** — pay-as-you-go, reserved / provisioned GPU, or a mix.
3. **Model choice** — proprietary or open-weight; small / mid / large. Different workloads may use different models.
4. **Data residency** — which region, and how customer data is protected.
5. **Rough monthly cost** — show the arithmetic (use the calculator on the helper page). Does it fit the budget?
6. **Two options you rejected, and why.**
7. **Consequences and risks** — what gets easier, what gets harder.

> Tip: there is no single right answer. The review board marks **reasoning**, not the choice.

---

## Step by step

Open **Command Prompt**. `team-x` below means **your** team folder: `team-a`, `team-b`, `team-c` or `team-d`.

### Part 1 — ADR v1 (now)

```
cd C:\AskIT\dxc-agentic-ai
copy Day01\Labs\adr1-model-selection\ADR_TEMPLATE.md teams\team-x\ADR-001_v1.md
notepad teams\team-x\ADR-001_v1.md
```

Fill the template, save, close Notepad. Then push:

```
git add teams
git commit -m "ADR-001 v1 - your name"
git push origin HEAD
```

You should see a line ending in `main -> main`. **Do not edit the v1 file again** — the board will compare v1 with v2.

### Part 2 — ADR v2 (when the trainer announces the update)

Make a copy of v1 and change **the copy**:

```
cd C:\AskIT\dxc-agentic-ai
copy teams\team-x\ADR-001_v1.md teams\team-x\ADR-001_v2.md
notepad teams\team-x\ADR-001_v2.md
```

In v2:

- Change **Status** to `Proposed – v2`.
- Fill the **"What changed and why"** box at the top (2–3 lines).
- Update the decision, options, cost and consequences that the update affects.

Then push:

```
git add teams
git commit -m "ADR-001 v2 - your name"
git push origin HEAD
```

### Check

Open your fork on GitHub → `teams` → `team-x`. You must see **both** `ADR-001_v1.md` and `ADR-001_v2.md`.

### If something goes wrong

| Problem | Fix |
|---|---|
| `copy` says "cannot find the path" | You typed `team-x` literally — use `team-a`, `team-b`, `team-c` or `team-d` |
| Push rejected | `git pull origin main --no-edit` then push again |
| `Author identity unknown` | Redo step 2 of `GIT_INSTRUCTIONS.md` (git config user.name / user.email) |
| Push asks for sign-in | Complete the GitHub browser sign-in popup, then push again |
| Anything else | Tell the trainer — do not try `git push --force` |

---

## Be ready to present (3 minutes if chosen)

1. The decision in one sentence.
2. Why — the top 2 drivers.
3. What it costs per month.
4. What changed between v1 and v2, and why.
5. The biggest risk you accepted.
