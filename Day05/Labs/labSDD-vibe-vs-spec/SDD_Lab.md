# Lab: Vibe Prompt vs Spec-Driven Development (SDD)

**Time: 30 min** · Solo or pairs · GitHub Copilot Chat in VS Code (Agent mode) · Python + pytest on your VM

| | |
|---|---|
| **What we do** | Build the same small AskIT function twice: once from a one-line "vibe" prompt, once from a written spec. Then the client changes the rules. |
| **Why** | AI builds exactly what you say, not what you mean. A written spec is the contract between you, the AI and the client. |
| **Outcome** | You see the score gap, the rework gap on a spec change, and when SDD is worth the effort. |
| **How** | Same hidden-style test file for both builds. Count passing tests. Compare effort on the curveball. |

**Time plan:** Setup 2 → A Vibe 6 → B Spec 10 → C Curveball 8 → D Debrief 4

---

## The use case (AskIT ticket triage)

AskIT receives IT tickets. We need a function `triage(ticket)` that returns the priority, the queue and the SLA. Deterministic Python, no LLM inside.

---

## 0. Setup (2 min)

```
cd C:\AskIT\dxc-agentic-ai\Day05\Labs
mkdir labSDD-vibe-vs-spec\vibe
mkdir labSDD-vibe-vs-spec\sdd
cd labSDD-vibe-vs-spec
code .
```

In VS Code open **Copilot Chat** and set the mode to **Agent**. Use **New Chat** (the `+` icon) for each build so the two don't share context.

Create `test_triage.py` (block below) and **copy it into both** `vibe\` and `sdd\`.

<details><summary>test_triage.py (click to expand)</summary>

```python
import pytest
from triage import triage

def t(title, users=1, desc=""):
    return {"title": title, "description": desc, "affected_users": users}

# (ticket, expected priority, expected queue, expected sla_hours)
CASES = [
    (t("Printer jam", 60),                  "P1", "General",  4),
    (t("Email outage"),                     "P1", "General",  4),
    (t("VPN is DOWN", 1),                   "P1", "Network",  4),
    (t("Slow download speed"),              "P4", "General", 72),
    (t("Wifi dropping", 12),                "P2", "Network",  8),
    (t("URGENT: cannot print"),             "P2", "General",  8),
    (t("Keyboard broken", 3),               "P3", "Hardware", 24),
    (t("Need a mouse"),                     "P4", "General", 72),
    (t("Password reset"),                   "P4", "Access",  72),
    (t("Laptop wifi broken"),               "P4", "Network", 72),
    (t("Screen flicker", 2, "after login"), "P3", "Access",  24),
    (t("Account locked", 50),               "P1", "Access",   4),
    (t("Unlocked door", 1),                 "P4", "General", 72),
]

@pytest.mark.parametrize("ticket,prio,queue,sla", CASES)
def test_rules(ticket, prio, queue, sla):
    assert triage(ticket) == {"priority": prio, "queue": queue, "sla_hours": sla}

def test_missing_users_defaults_to_one():
    assert triage({"title": "Need a mouse"})["priority"] == "P4"

def test_empty_title_rejected():
    with pytest.raises(ValueError):
        triage({"title": "  ", "affected_users": 1})

def test_bad_users_rejected():
    with pytest.raises(ValueError):
        triage(t("Need a mouse", 0))
```

</details>

Total tests: **16**. Run with `python -m pytest -q` inside `vibe\` or `sdd\`. Don't read the tests before Step A. They are the "client's acceptance tests".

---

## A. Vibe build (6 min)

1. Open a **New Chat** in Copilot. Paste exactly this prompt (don't improve it):

```
Write a Python function triage(ticket) in triage.py that prioritizes IT support tickets.
ticket is a dict with title, description, affected_users.
Return a dict with priority, queue and sla_hours.
Save it as vibe/triage.py
```

2. Check that Copilot created `vibe\triage.py` (save it manually if it only showed code).
3. Run `python -m pytest -q` in `vibe\`.
4. Write down: **Vibe score = ___ / 16 passed**

Don't fix anything yet. Keep this chat open for Step C.

---

## B. Spec-driven build (10 min)

1. Create `sdd\SPEC.md` with the content below.
2. **Your decision (2 min):** the spec has two `TODO` lines. Fill them in however you like (the tests accept either). Reading the spec closely is the exercise.
3. Open a **New Chat** in Copilot and paste this prompt (`#file:` attaches the spec):

```
Implement sdd/triage.py strictly from #file:sdd/SPEC.md. Do not add behaviour that is not in the spec.
If anything is ambiguous, ask me before coding.
Also write sdd/test_spec.py with one test per Acceptance Criterion (AC).
```

4. Check the files landed in `sdd\` and run `python -m pytest -q`.
5. Write down: **SDD score = ___ / 16 passed**

### SPEC.md

```markdown
# SPEC: AskIT Ticket Triage v1

## Purpose
Classify an IT support ticket into a priority, a queue and an SLA. Pure function, no I/O, no LLM.

## Interface
`triage(ticket: dict) -> dict` in `triage.py`

Input keys: `title` (str, required), `description` (str, optional), `affected_users` (int, optional, default 1)
Output keys: `priority` ("P1".."P4"), `queue` (str), `sla_hours` (int)

## Rules
- R1 Text = title + description, matched case-insensitive, **whole words only** ("download" does not match "down").
- R2 Priority, first match wins:
  P1 if affected_users >= 50 or text has the word `outage` or `down`
  P2 if affected_users >= 10 or text has the word `urgent` or `blocked`
  P3 if affected_users >= 2
  P4 otherwise
- R3 Queue, first match wins:
  Network: vpn, wifi, network
  Access: password, login, locked
  Hardware: laptop, keyboard, screen
  General: none of the above
- R4 SLA hours: P1 = 4, P2 = 8, P3 = 24, P4 = 72
- R5 Empty or missing title: raise ValueError
- R6 affected_users missing: treat as 1. affected_users < 1 or not an int: raise ValueError
- R7 TODO: decide what happens when the description is None (we say: ______)
- R8 TODO: decide whether to log anything (we say: ______)

## Acceptance Criteria
- AC1 60 affected users -> P1, SLA 4
- AC2 "Email outage" -> P1
- AC3 "Slow download speed" -> P4 (whole word rule)
- AC4 12 users -> P2, SLA 8
- AC5 "URGENT: cannot print" -> P2
- AC6 3 users -> P3, SLA 24
- AC7 "Laptop wifi broken" -> queue Network (order matters)
- AC8 "Password reset" -> queue Access
- AC9 empty title -> ValueError; 0 users -> ValueError

## Out of scope
Persistence, authentication, ML, UI.

## Changelog
- v1 initial
```

---

## C. Curveball (8 min)

> Don't scroll below until your trainer announces it.

The client has changed the rules. **Same change for both builds. Use a stopwatch.**

### New requirements (v2)

1. New optional input `customer_tier` = `"standard"` (default) or `"vip"`. Anything else raises ValueError. A VIP ticket gets its priority raised one level after R2 (P4 to P3, P3 to P2, P2 to P1, P1 stays P1). SLA follows the final priority.
2. The P1 SLA drops from 4 hours to **2 hours**.
3. New queue **Security**, checked **first** (before Network): `phishing`, `breach`, `malware`.

### C1. Vibe path (4 min)

In the **same vibe chat** (Agent mode), paste the three requirements above in plain English and say: "Update the function." Save the result, then run the v2 tests (below) in `vibe\`.

### C2. Spec path (4 min)

1. Edit `SPEC.md` only (about 6 lines): add the `customer_tier` input, add R2b (VIP bump), change the P1 SLA in R4, add Security to R3, add 3 ACs, add `- v2 client change: VIP, Security queue, P1 SLA 2h` to the Changelog.
2. In the **same SDD chat**, say:

```
#file:sdd/SPEC.md changed (see Changelog v2). Update sdd/triage.py and sdd/test_spec.py to match.
Change only what the diff requires. List what you changed.
```

3. Run the v2 tests in `sdd\`.

### v2 tests

Save as `test_triage_v2.py` in **both** folders, then run `python -m pytest -q test_triage_v2.py`.

<details><summary>test_triage_v2.py (click to expand)</summary>

```python
import pytest
from triage import triage

def t(title, users=1, desc="", tier=None):
    d = {"title": title, "description": desc, "affected_users": users}
    if tier:
        d["customer_tier"] = tier
    return d

# (ticket, expected priority, expected queue, expected sla_hours)
CASES = [
    (t("Printer jam", 60),                  "P1", "General",  2),
    (t("Email outage"),                     "P1", "General",  2),
    (t("VPN is DOWN", 1),                   "P1", "Network",  2),
    (t("Slow download speed"),              "P4", "General", 72),
    (t("Wifi dropping", 12),                "P2", "Network",  8),
    (t("URGENT: cannot print"),             "P2", "General",  8),
    (t("Keyboard broken", 3),               "P3", "Hardware", 24),
    (t("Need a mouse"),                     "P4", "General", 72),
    (t("Password reset"),                   "P4", "Access",  72),
    (t("Laptop wifi broken"),               "P4", "Network", 72),
    (t("Screen flicker", 2, "after login"), "P3", "Access",  24),
    (t("Account locked", 50),               "P1", "Access",   2),
    (t("Unlocked door", 1),                 "P4", "General", 72),
    # --- new in v2 ---
    (t("Need a mouse", tier="vip"),         "P3", "General", 24),
    (t("Keyboard broken", 3, tier="vip"),   "P2", "Hardware",  8),
    (t("Email outage", tier="vip"),         "P1", "General",  2),
    (t("Need a mouse", tier="standard"),    "P4", "General", 72),
    (t("Phishing email received"),          "P4", "Security", 72),
    (t("Malware on laptop wifi", 12),       "P2", "Security",  8),
    (t("Data breach suspected", 60),        "P1", "Security",  2),
]

@pytest.mark.parametrize("ticket,prio,queue,sla", CASES)
def test_rules(ticket, prio, queue, sla):
    assert triage(ticket) == {"priority": prio, "queue": queue, "sla_hours": sla}

def test_missing_users_defaults_to_one():
    assert triage({"title": "Need a mouse"})["priority"] == "P4"

def test_empty_title_rejected():
    with pytest.raises(ValueError):
        triage({"title": "  ", "affected_users": 1})

def test_bad_users_rejected():
    with pytest.raises(ValueError):
        triage(t("Need a mouse", 0))

def test_bad_tier_rejected():
    with pytest.raises(ValueError):
        triage(t("Need a mouse", tier="gold"))
```

</details>

Total tests: **24**.

---

## D. Scorecard and debrief (4 min)

| | Vibe | SDD |
|---|---|---|
| v1 score (of 16) | | |
| v2 score (of 24) | | |
| Tests that passed in v1 but **fail in v2** (regressions) | | |
| Minutes to absorb the curveball | | |
| Lines of **your own** text changed for the curveball | | |
| Can a teammate see *why* the code behaves this way? | | |

Discuss in 2 min:
1. Where did the vibe build guess wrong, and who owned that wrong guess: you, the AI, or the missing spec?
2. When the client changed the rules, what did you update in the vibe path? What did you update in the SDD path?
3. Would you put the vibe code or the spec in front of the client for sign-off?

### Takeaways

- **The spec is the source of truth.** Code and tests are generated output that can be rebuilt from it.
- **Change the spec first, then let AI re-sync the code.** Don't patch code by chat history.
- **Acceptance criteria turn opinions into tests.** "Done" becomes measurable.
- **Questions before code.** A good spec prompt makes the AI ask about ambiguity instead of guessing.

### Product and trade-off view (for your client conversations)

| Approach | Good for | Watch out |
|---|---|---|
| Vibe prompting in chat | Throwaway scripts, prototypes, exploring ideas | Hidden assumptions, no audit trail, rework on every change |
| Plain `SPEC.md` + any assistant (this lab) | Zero tooling, works with any model, easy to review in a PR | Discipline is manual, no built-in task breakdown |
| Spec-driven toolkits (for example GitHub Spec Kit, AWS Kiro) | Teams that want spec, plan and tasks as a workflow | Extra process and learning curve. Check each tool's current features and pricing before recommending |
| Repo instruction files (for example `.github/copilot-instructions.md`, `CLAUDE.md`) | Persistent rules and standards across sessions | Instructions are not a full spec for each feature |

**When SDD is overkill:** one-off scripts, spikes you will throw away, anything under about 30 minutes of work.
**When it pays off:** shared code, regulated or audited work, multi-person teams, and anything the client will change their mind about.

### Bridge to Day 5

An agent's tool is a function the model calls without you watching. The tool's **contract** (inputs, outputs, errors, limits) is a spec. That is why Day 6 pairs ADR-004 with a tool contract.

---

## Stretch (fast finishers)

1. Add a rule R9 in the spec: tickets mentioning "ceo" always get P1. Update the code through the spec only. How many lines did you touch?
2. Ask Copilot: "Review #file:sdd/SPEC.md for contradictions and missing edge cases." Fix what it finds in the spec, not the code.
