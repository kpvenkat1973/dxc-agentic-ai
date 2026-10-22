# ADR Exercise 2: The Orbit Corp solution decision

**We are doing the ADR 2 team exercise now (adr2-askit-hosting).**

**You are the solution architects on a pre-sales call.** The customer asked: "Tell us how to run AskIT in production, and what it will cost us in trade-offs." Your ADR is the recommendation you send after the call.

**Time:** 12 min ADR v1 · trainer update · 6 min ADR v2 · 2 teams present (3 min each)
**Work:** teams of 3 in a breakout room · **Output:** two short files in your team folder
**Helpers:** the Day 12 page `AskIT_Goes_Live.html` (AgentCore map, "AgentCore vs DIY", Tab 6 reference design) and the options table in `ADR_TEMPLATE.md`

---

## What the customer told you on the call

**Orbit Corp** (fictional): 50,000 employees in 12 countries. AskIT, the IT helpdesk agent you built, runs today on one developer's VM. IT wants it live for every employee in **6 weeks**.

| Topic | What they said |
|---|---|
| Load | about 6,000 questions a day, **3 times busier on Monday 9 to 10 am** |
| Knowledge | about 20,000 documents (IT policies, how-tos), changed every week. **Some HR documents are confidential: only the right roles may see them** |
| Tools | ticket system, HR system, knowledge search, **password reset** |
| Risk | a wrong password reset for a VIP (CEO, CFO) is a security incident |
| Security | wants SSO with the company login. Asks: "Who asked, which tool ran, was it allowed?" for every action |
| Data | **EU employees' data must stay in the EU** |
| Quality | last year's chatbot gave an **out-of-date policy** and caused a complaint |
| Team | 2 developers + 1 SRE. No platform or Kubernetes specialist |
| Existing | AWS enterprise account. Another team runs a Kubernetes (EKS) cluster |
| Budget | modest. The sponsor says: "no big up-front platform build, and tell me what it costs per question" |

---

## Your task

Write **ADR v1** in two parts:

1. **The decision table (section 3).** For each layer of the stack, pick an option from the menu (or your own) and write **one line: why, and what you give up.**
   - **Must do (5 rows):** Hosting · Knowledge (RAG) · Tools (MCP / Gateway) · Guardrails and policy · Observability and evaluation
   - **Do if time allows (3 rows):** Model · Identity · Cost and release
2. **The recommendation to the customer (sections 4 to 6):** your top 3 trade-offs in plain words, the biggest risk, and your **go / no-go with conditions.**

> There is no single right answer. The review board marks **reasoning and trade-offs**, not the choice. An honest "we accept this risk because..." scores higher than a perfect-sounding answer.

---

## Step by step

One person in the team is the **scribe** and types. The others read the Day 12 page and argue. `team-x` means **your** folder: `team-a`, `team-b`, `team-c` or `team-d`.

### Part 1: ADR v1 (12 minutes)

```
cd C:\AskIT\dxc-agentic-ai
copy Day12\Labs\adr2-askit-hosting\ADR_TEMPLATE.md teams\team-x\ADR-002_v1.md
notepad teams\team-x\ADR-002_v1.md
```

Fill the template, save, close Notepad. **Do not push yet.** Do not edit v1 again after the trainer's update.

### Part 2: ADR v2 (6 minutes, when the trainer announces the update)

```
copy teams\team-x\ADR-002_v1.md teams\team-x\ADR-002_v2.md
notepad teams\team-x\ADR-002_v2.md
```

- Set **Status** to `Proposed - v2`.
- Fill the **What changed and why** box (2 lines).
- Change only the rows the update affects.

Then push **both** files once:

```
git add teams
git commit -m "ADR-002 v1 and v2 - team x"
git push origin HEAD
```

### If something goes wrong

| Problem | Fix |
|---|---|
| "cannot find the path" | You typed `team-x` literally. Use `team-a`, `team-b`, `team-c` or `team-d` |
| Push rejected | `git pull origin main --no-edit`, then push again |
| Anything else | Tell the trainer. Do not use `git push --force` |

---

## Be ready to present (3 minutes if chosen)

1. Your recommendation in one sentence.
2. The 3 trade-offs you would say out loud to the customer.
3. What changed from v1 to v2, and which rows moved.
4. The risk you accepted, and your go or no-go.
