# Evening Mission: Build the AskIT Gatekeeper (with a spec + Copilot)

**Do it after office hours · 45 to 60 minutes · on your VM · you write a spec, Copilot writes the code**

| What we do | Why | Outcome | How |
|---|---|---|---|
| Build the "safety brain" of AskIT: which team gets a ticket, when a human must approve, and what AskIT may remember. | In class you SAW these ideas in the apps (Lab 7 memory, Lab 8 router + approval). Tonight you BUILD them yourself. | A working `gatekeeper.py`, a test score, and your design decisions in writing. | Read the spec, fill 3 decisions, paste one prompt into Copilot, run one command to check. |

This is the same method as the "Vibe vs Spec" lab: **the spec is the source of truth, the AI writes the code, the tests prove it.**

---

## STEP 0. Get the folder (2 minutes)

1. In File Explorer open `C:\AskIT\dxc-agentic-ai` and double-click **SYNC.bat**.
2. Open **VS Code**. Click **File > Open Folder**, paste this path and click **Select Folder**:

```
C:\AskIT\dxc-agentic-ai\Day08\Labs\homework-askit-gatekeeper
```

3. Open **Copilot Chat** (Ctrl + Shift + I) and set the mode to **Agent**.

You see only this README, `score.bat` and a `submission` folder. The client's tests are kept outside this folder on purpose, so Copilot cannot copy them.

---

## STEP 1. Read the spec and make 3 decisions (10 minutes)

Read the spec in STEP 2 once. It has three rules:

| Rule | What it does | Where you saw it |
|---|---|---|
| R1 `route()` | Picks the team for a ticket | Lab 8: the Router |
| R2 `needs_approval()` | Decides if a human must approve an action | Lab 8: Policy + Human approval |
| R3 `safe_to_remember()` | Decides if a fact may be saved in long-term memory | Lab 7: Long-term memory, "never store secrets" |

Three lines in the spec say `______`. **You decide them.** The tests accept any sensible choice. Think like the architect:

- **D1.** A VIP only wants to READ something (search the knowledge base, read a ticket). Does that need approval? Write **yes** or **no**.
- **D2.** A write action arrives at night (8 pm to 8 am). Who approves? Write **on-call** (an on-call person approves now) or **queue** (it waits until 8 am).
- **D3.** How many days do we keep remembered facts? Write a number (for example 30 or 90). Not tested, but your trainer will ask why.

---

## STEP 2. Build it with Copilot (10 minutes)

1. Click the **+** (New Chat) in Copilot.
2. Copy the whole block below. **Before you send it**, replace the three `______` with your decisions D1, D2, D3.
3. Send it. Copilot saves `SPEC.md` and builds `gatekeeper.py`.

```
Save the spec below as SPEC.md, then implement gatekeeper.py strictly from it.
Plain Python only, no external libraries, no LLM, no files, no network.
Do not add behaviour that is not in the spec. If anything is unclear, ask me before coding.

# SPEC: AskIT Gatekeeper v1

## Purpose
Three small, testable safety functions for the AskIT helpdesk agent.

## R1 route(text: str) -> str
- Returns one team: "Security", "Access", "Network", "Hardware" or "General".
- Match words case-insensitive, WHOLE WORDS only ("download" does not match "down").
- First match wins, in this order:
  Security: phishing, malware, breach, suspicious
  Access: password, locked, login, mfa, access
  Network: vpn, wifi, network, internet
  Hardware: laptop, printer, screen, keyboard, phone
  General: none of the above
- Empty or blank text: raise ValueError.

## R2 needs_approval(action: str, user_id: str, hour: int) -> dict
- Returns {"approval": True or False, "approver": "<who>"}.
- Read actions: "search_kb", "get_ticket". Write actions: "reset_password", "update_ticket", "grant_access".
- Any other action: raise ValueError. hour must be an int from 0 to 23, else raise ValueError.
- VIP users: EMP-1001, EMP-1012, EMP-1023.
- Night means hour >= 20 or hour < 8.
- Rules, first match wins:
  1. Read action by a VIP: approval = ______ (D1: yes or no). If yes, approver "it manager", else approver "none".
  2. Read action by anyone else: approval False, approver "none".
  3. Write action by a VIP (day or night): approval True, approver "it manager".
  4. Write action at night: approval True, approver "______" (D2: on-call or queue).
  5. Write action in the day: approval True, approver "service desk lead".

## R3 safe_to_remember(text: str) -> bool
- Returns True if the fact may be saved in long-term memory, else False.
- False if the text is empty or blank.
- False if it contains the whole word password, passcode, otp or pin (case-insensitive).
- False if it contains a number with 6 or more digits, ignoring spaces and dashes (card numbers, OTPs, account numbers).
- Otherwise True.
- Saved facts are kept for ______ days (D3), then deleted. (Not coded here, recorded for the design.)

## Acceptance Criteria (examples)
- AC1 route("VPN error 809 since morning") -> "Network"
- AC2 route("Phishing email asked for my password") -> "Security" (order matters)
- AC3 route("Cannot download files") -> "General" (whole words)
- AC4 needs_approval("reset_password", "EMP-1002", 10) -> approval True, approver "service desk lead"
- AC5 needs_approval("update_ticket", "EMP-1001", 10) -> approval True, approver "it manager"
- AC6 needs_approval("delete_user", "EMP-1002", 10) -> ValueError
- AC7 safe_to_remember("My laptop is a Dell XPS 13") -> True
- AC8 safe_to_remember("Card 4111 1111 1111 1111 please") -> False

## Out of scope
UI, database, LLM calls, logging.

## Changelog
- v1 initial
```

If Copilot only shows the code and does not create the files, click **Keep** / **Apply**, or ask it: `Please create the files SPEC.md and gatekeeper.py now.`

---

## STEP 3. Check it (5 to 10 minutes)

In VS Code click **Terminal > New Terminal**. Type this and press Enter:

```
.\score.bat
```

You see a line like `21 passed`. That is your score out of **21**.

**Not 21?** Read the red lines: they say which example failed. Fix it **through the spec**, not by editing code. In the SAME Copilot chat, paste:

```
These acceptance tests failed: <paste the red lines here>.
Check gatekeeper.py against SPEC.md and fix the code so it follows the spec exactly. Change only what is needed.
```

Then run `.\score.bat` again.

---

## STEP 4. The client changes the rules (10 minutes)

Orbit Corp's CISO calls: **"Add 'ransomware' to Security. And nobody may ever save an employee's home address in memory."**

Do it the spec-driven way. In the SAME chat, paste:

```
The client changed the rules. Spec first: update SPEC.md, then update gatekeeper.py to match. List what you changed.
1. R1: add the word ransomware to Security.
2. R3: return False if the text contains the word address or the phrase home address.
3. Add a v2 line to the Changelog: "v2 client change: ransomware, no home addresses".
```

Then check two things yourself. In the terminal type:

```
python -c "import gatekeeper as g; print(g.route('ransomware on my laptop'), g.safe_to_remember('My home address is 12 MG Road'))"
```

You should see: `Security False`. Run `.\score.bat` once more: still 21 passed? (A change must not break old rules.)

---

## STEP 5. Write 3 short notes and push (5 minutes)

Open `submission\my_notes.md` and answer in one or two lines each:

1. Your D1, D2 and D3, and **why** (as you would say it to a client).
2. Which ONE rule in this spec would you never let an LLM decide on its own? Why?
3. In the change request, did you edit the spec or the code first? Why does that order matter?

Save (Ctrl+S). In File Explorer open `C:\AskIT\dxc-agentic-ai` and double-click **SYNC.bat**. Your trainer sees your `SPEC.md`, `gatekeeper.py`, `score.txt` and notes.

---

## If something goes wrong

| What you see | What to do |
|---|---|
| `.\score.bat` is not recognized | You are in the wrong folder. Repeat STEP 0 |
| `No module named pytest` | Type `python -m pip install pytest` and press Enter, then run `.\score.bat` again |
| `No module named gatekeeper` | Copilot did not create the file. Ask it: `Please create gatekeeper.py now.` |
| Copilot asks you a question | Good! That is the spec working. Answer it in one line |

## Stretch (only if you want more)

Ask Copilot in a NEW chat (this is "vibe coding", and that is fine for a screen):

```
Create app.py: a small Streamlit page with a text box and buttons that call route, needs_approval and safe_to_remember from gatekeeper.py and show the results. Do not change gatekeeper.py.
```

Run it with `python -m streamlit run app.py`. **Lesson:** write a spec where it matters (rules, safety), vibe-code where it does not (the screen).

## What you practised

- Turning a design decision (who approves, what to remember) into **rules a machine can check**.
- **Plain-code policy** for safety decisions, not the LLM. That is what the Lab 8 Policy node does.
- **Spec first, then code**: a change request is a spec change, and the tests prove nothing old broke.
