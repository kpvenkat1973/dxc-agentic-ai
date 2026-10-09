# Lab: Vibe Prompt vs Spec-Driven Development (SDD)

## What we are building: AskIT Ticket Triage

AskIT is our fictional IT helpdesk. Tickets arrive all day, and each one must be sorted automatically so the right team sees it, in time. You will build **one Python function, `triage(ticket)`**, twice: once with a quick prompt (vibe) and once from a spec (SDD). Plain Python, no LLM inside.

| It receives | It returns |
|---|---|
| A ticket: `title`, `description`, `affected_users` | `priority` (P1 to P4), `queue` (for example Network, Access, Hardware, General) and `sla_hours` (how fast the team must respond) |

Example:

```
triage({"title": "VPN is DOWN", "description": "", "affected_users": 1})
-> {"priority": "P1", "queue": "Network", "sla_hours": 4}
```

The exact rules are **not** given here on purpose. Part of the lab is seeing who ends up deciding them: you, the AI, or a written spec.

---

**Time: 35 min** · Solo or pairs · GitHub Copilot Chat in VS Code (Agent mode) · Python + pytest on your VM

| | |
|---|---|
| **What we do** | Build the same small AskIT function twice: once from a one-line "vibe" prompt, once from a spec. Compare. Then the client changes the rules. |
| **Why** | AI builds exactly what you say, not what you mean. A written spec is the contract between you, the AI and the client. |
| **Outcome** | You see the score gap, the rework gap on a rule change, and when SDD is worth the effort. |

**Time plan:** Setup 1 → A Vibe 5 → B SDD 8 → Compare 4 → C Curveball 10 → Rebuild 4 → D Debrief 4

**Everything is ready for you.** The folders are already in place. You only paste prompts, make one small decision, and run tests.

---

## 0. Setup (1 min)

1. In VS Code: **File > Open Folder** > `C:\AskIT\dxc-agentic-ai\Day07\Labs\labSDD-vibe-vs-spec`
2. Open **Copilot Chat** and set the mode to **Agent**.  (Control + Shift + I)
3. Use **New Chat** (the `+` icon) for each build, so the two don't share context.

You will see `vibe\` and `sdd\`. The client's acceptance tests are kept out of sight on purpose. To score a build you run one command, `.\score.bat`, in the terminal. It brings the tests in, runs them and takes them out again.

---

## A. Traditional (vibe) prompt (5 min)

1. **New Chat.** Paste this prompt exactly (don't improve it):

```
Write a Python function triage(ticket) in triage.py that prioritizes IT support tickets.
ticket is a dict with title, description, affected_users.
Return a dict with priority, queue and sla_hours.
Save it as vibe/triage.py
```

2. Let Copilot create `vibe\triage.py` (save it if it only showed code).
3. Run in the terminal:

```
.\score.bat vibe
```

4. Write down: **Vibe score = ___ / 16**

5. **Rename this chat as Vibe Chat** for easy identification: right-click the chat and choose Rename.

Don't fix anything. Keep this chat open for Step C.

---

## B. Spec-driven (SDD) prompt (8 min)

1. **New Chat.** Copy the whole block below and paste it into Copilot, but **before you send it**, replace the two `______` blanks (R7 and R8) with your own decision. The tests accept either. Read the spec once as you do it: it holds the rules, the acceptance criteria (AC) and what is out of scope.
2. Send it. Copilot saves the spec as `sdd\SPEC.md` and builds `sdd\triage.py` from it.

```
Save the spec below as sdd/SPEC.md, then implement sdd/triage.py strictly from it. Do not add behaviour that is not in the spec.
If anything is ambiguous, ask me before coding.
Also write sdd/test_spec.py with one test per Acceptance Criterion (AC).

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

3. Run in the terminal:

```
.\score.bat sdd
```

4. Write down: **SDD score = ___ / 16**

5. **Rename this chat as SDD Chat** for easy identification: right-click the chat and choose Rename.

Keep this chat open for Step C.

### What is different in this prompt?

| Vibe prompt | SDD prompt |
|---|---|
| The rules live only in your head | The rules live in a file, `SPEC.md`, that everyone can read |
| "Prioritizes tickets": the AI guesses what that means | Exact rules: priority order, queue order, whole words only, SLA hours |
| The AI fills every gap with its own guess | "Do not add behaviour that is not in the spec" |
| The AI never asks questions | "If anything is ambiguous, ask me before coding" |
| No proof it works | "One test per Acceptance Criterion" gives a test for every rule |

---

## Compare (4 min)

Ask the same question in **both chats** (vibe chat and SDD chat), and paste:

```
Which part of the code makes "Laptop wifi broken" go to the Network queue, and why?
```

- SDD chat: points to a rule in the spec (R3). The answer is traceable.
- Vibe chat: explains its own guess. Nobody agreed to that rule.
- Also look: did the vibe build ever ask you a question before coding? Did the SDD build?

---

## C. Curveball (10 min)

> Don't scroll below until your trainer announces it.

The client has changed the rules. **Same change for both builds. Use a stopwatch.**

### New requirements (v2)

1. New optional input `customer_tier` = `"standard"` (default) or `"vip"`. Anything else raises ValueError. A VIP ticket gets its priority raised one level after the priority rules (P4 to P3, P3 to P2, P2 to P1, P1 stays P1). SLA follows the final priority.
2. The P1 SLA drops from 4 hours to **2 hours**.
3. New queue **Security**, checked **first** (before Network): `phishing`, `breach`, `malware`.

### C1. Vibe path (4 min)

In the **same vibe chat**, paste:

```
The client changed the rules. Update vibe/triage.py:
1. New optional input customer_tier = "standard" (default) or "vip". Anything else raises ValueError. A VIP ticket gets its priority raised one level after the normal priority rules (P4 to P3, P3 to P2, P2 to P1, P1 stays P1). SLA follows the final priority.
2. The P1 SLA drops from 4 hours to 2 hours.
3. New queue Security, checked first (before Network): phishing, breach, malware.
```

Then run: `.\score.bat vibe v2`

### C2. SDD path (4 min)

In the **same SDD chat**, paste (spec first, then code):

```
The client changed the rules. Spec first: update sdd/SPEC.md with the changes below (edit the Input line, add R2b, edit R3 and R4, add 3 ACs, add a v2 line to the Changelog).
Then update sdd/triage.py and sdd/test_spec.py to match. Change only what the spec change requires. List what you changed.
1. New optional input customer_tier = "standard" (default) or "vip". Anything else raises ValueError. A VIP ticket gets its priority raised one level after R2 (P4 to P3, P3 to P2, P2 to P1, P1 stays P1). SLA follows the final priority.
2. The P1 SLA drops from 4 hours to 2 hours.
3. New queue Security, checked first (before Network): phishing, breach, malware.
Changelog line: v2 client change: VIP, Security queue, P1 SLA 2h
```

Then run: `.\score.bat sdd v2`

Total v2 tests: **24**.

---

## Rebuild test (4 min)

Delete the code in both folders, then rebuild each in a **New Chat**. In the terminal:

```
del vibe\triage.py
del sdd\triage.py
```

1. **SDD:** New Chat, paste this, then run `.\score.bat sdd v2`

```
Implement sdd/triage.py strictly from #file:sdd/SPEC.md
```

2. **Vibe:** New Chat, paste the same vibe prompt from Step A, then run `.\score.bat vibe v2`

Write down: **SDD v2 = ___ / 24**, **Vibe v2 = ___ / 24**

The spec still holds every rule, including the client's change, so the SDD code comes back. In the vibe path the rules lived only in the old chat, so they are gone.

---

## D. Scorecard and debrief (4 min)

| | Vibe | SDD |
|---|---|---|
| v1 score (of 16) | | |
| v2 score (of 24) | | |
| Tests that passed in v1 but **fail in v2** (regressions) | | |
| Minutes to absorb the curveball | | |
| Rebuilt from scratch: v2 score (of 24) | | |
| Can a teammate see *why* the code behaves this way? | | |

Discuss in 2 min:
1. Where did the vibe build guess wrong, and who owned that wrong guess: you, the AI, or the missing spec?
2. When the client changed the rules, what did you have to explain again in the vibe path? What changed in the SDD path?
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

### Bridge to Day 7

An agent's tool is a function the model calls without you watching. The tool's **contract** (inputs, outputs, errors, limits) is a spec. That is why Day 6 pairs ADR-004 with a tool contract.

---

## Stretch (fast finishers)

1. Add a rule R9 to `sdd\SPEC.md`: tickets mentioning "ceo" always get P1. Update the code through the spec only. How many lines did you touch?
2. Ask Copilot: "Review #file:sdd/SPEC.md for contradictions and missing edge cases." Fix what it finds in the spec, not the code.
