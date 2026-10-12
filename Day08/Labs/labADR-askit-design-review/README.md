# Team Exercise: AskIT Design Review (ADR + Sales Call)

**Session 8 · Team breakout · about 60 minutes · no code, no app**

| What we do | Why | Outcome | How |
|---|---|---|---|
| As a team, make the 6 big design decisions for AskIT (one per topic we covered), write ONE decision record, and answer a client's tough questions. | In real projects, architects and pre-sales people defend designs in front of clients and review boards. The technology is only half the job. | A one-page design review in your team folder, and a 3-minute pitch to the "client". | Breakout room. Read, discuss, tick a choice, write one line why. One person types. |

---

## STEP 0. Open the files (one person per team: the "scribe")

1. In VS Code: **File > Open Folder** > paste this path and click **Select Folder**:

```
C:\AskIT\dxc-agentic-ai\Day08\Labs\labADR-askit-design-review
```

2. Open `design_review_template.md`.
3. Click **File > Save As**. Save it into YOUR team folder with this name (use your team letter):

```
C:\AskIT\dxc-agentic-ai\teams\team-a\AskIT_Design_Review.md
```

4. Share your screen in the breakout room. Everyone discusses, the scribe types.

---

## The client brief (read it together, 3 minutes)

> **Orbit Corp CIO, on a call with your team:**
> "We have 5,000 employees and about **10,000 IT helpdesk tickets a day**. Half of them are repeats: password resets, VPN errors, laptop issues.
> I want **AskIT** live in **8 weeks**. It must answer from **our** IT policies, not from the internet.
> It may reset passwords, but **I don't want a robot locking out my CEO**.
> Budget for AI usage: **under $2,000 a month**. Our data must stay in our cloud account.
> Convince me your design is safe, cheap and will not embarrass us."

Your team = the vendor's solution team. Roles (pick quickly): **Scribe** (types), **Architect** (leads decisions), **Presenter** (pitches at the end), **Client voice** (plays devil's advocate in your room).

---

## PART 1. Make 6 decisions (25 minutes, about 4 minutes each)

For each decision: discuss, **tick ONE option** in your file, and write **one line why**. There is no single right answer. The board scores your *reasons*.

### D1. Which model? (Day 1)

| Option | Good | Watch out |
|---|---|---|
| A. Small model everywhere (Nova Micro / gpt-mini) | Cheapest, fastest | Weaker on vague or tricky tickets |
| B. Large model everywhere (Claude Sonnet / GPT-5) | Best answers | Many times the cost per token |
| C. Mix: small model for routing and simple answers, large model only for hard cases | Balances cost and quality | Two models to test and monitor |

Discuss: which tickets are "hard"? Who decides?

### D2. How does AskIT know Orbit Corp's IT policies? (Day 3)

| Option | Good | Watch out |
|---|---|---|
| A. RAG: search our knowledge base and give the model the best articles | Up to date, cites sources | Needs a good search (chunking, index) |
| B. Fine-tune a model on our policies | Policies "inside" the model | Costly, goes stale when policies change, no citations |
| C. Paste ALL policies into every prompt | Very simple | Huge token cost on every call, context limit |

Discuss: a policy changes tomorrow. Which option updates fastest?

### D3. How good must the search be? (Day 4)

| Option | Good | Watch out |
|---|---|---|
| A. Simple vector search (naive RAG) | Easy, quick to build | Misses exact words like error codes ("809") |
| B. Hybrid search (keywords + vectors) + reranker | Finds exact codes AND meaning, better top results | More parts, a bit slower |
| C. Start with A, measure, move to B only if answers are wrong | Cheapest start | Needs an evaluation set to measure |

Discuss: how would you prove to the CIO that answers are correct?

### D4. What may AskIT DO? (Days 5–6)

| Option | Good | Watch out |
|---|---|---|
| A. Answer only (read tools: search KB, read ticket) | Safe | Users still wait for humans for resets |
| B. Answer + act (reset password, update ticket) on its own | Biggest time saving | One wrong action = security incident |
| C. Answer + act, but every write action needs a human approval | Saves time, keeps control | Approvers must respond; slower for resets |

Discuss: the CIO's line "don't lock out my CEO". Which option answers it?

### D5. What should AskIT remember? (Day 7)

| Option | Good | Watch out |
|---|---|---|
| A. Nothing between chats | No privacy risk | Users repeat themselves |
| B. The current chat only, with compaction (summary of old messages) | Cheaper long chats | Summary may drop a detail |
| C. Current chat + a few facts per user across chats (laptop, location) | Feels personal | Privacy: what is stored, who sees it, delete on request |

Discuss: what must NEVER be stored? Who can delete it?

### D6. One agent or a team of agents? (Day 8)

| Option | Good | Watch out |
|---|---|---|
| A. One agent with all tools | Simple, fewest LLM calls | Big prompt, wrong tool picks, hard to govern |
| B. Router + specialist agents (Network, Access, Hardware, General) + human approval step | Clean routing, small prompts, clear approval point | About one extra LLM call per ticket |
| C. Handoffs: agents pass the user from one to another | Natural for long conversations | Harder to trace who decided what |

Discuss: if you have not done Lab 8 yet, make your best guess now. After Lab 8, check your guess with the numbers in its tab 3.

---

## PART 2. Quick cost check (5 minutes)

Use this simple formula (approximate list prices, input tokens only):

```
tokens per month = tickets per day × tokens per ticket × 30
cost per month   = tokens per month ÷ 1,000,000 × price per million tokens
```

Use **10,000 tickets a day** and **3,000 tokens per ticket** (RAG articles + chat + tools) = **900 million tokens a month**.

| Model (approx. price per 1M input tokens) | Monthly cost |
|---|---|
| Small: Nova Micro (~$0.035) | about $32 |
| Small: gpt-mini class (~$0.25) | about $225 |
| Large: Claude Sonnet class (~$3) | about $2,700 |

Write in your file: does your D1 choice fit the **$2,000** budget? If you chose the mix (C), say what % of tickets go to the large model.

---

## PART 3. Write ONE decision record (10 minutes)

Pick the decision your team **argued about most**. Fill the short ADR section in your file:
Context · Decision · Alternatives rejected (and why) · Consequences (good and bad) · How we will measure it.

---

## PART 4. The client fights back (5 minutes in your room, then live)

Prepare a 1-sentence answer to each question. The trainer (as the CIO) will fire **two of them** at your presenter.

1. "Why not just buy ChatGPT Enterprise or Copilot and skip all this?"
2. "Your bot will make up policies. How do I know it won't?"
3. "Will it reset passwords on its own at 2 am?"
4. "What will this cost me per month, really?"
5. "Why several agents? Isn't one enough?"
6. "What happens to my employees' chat data?"
7. "If AWS or Azure changes prices next year, are we locked in?"
8. "How will I know in 3 months that it is working?"

---

## PART 5. Pitch (3 minutes per team, in the main room)

When the trainer closes the breakout rooms, come back to the main room. **Teams present when the trainer calls your team name.** The presenter shares the screen with your `AskIT_Design_Review.md` open.


1. Your 6 decisions in one line each.
2. Your ADR in 30 seconds.
3. Answer the CIO's 2 questions.

Then save your file and push it: in File Explorer open `C:\AskIT\dxc-agentic-ai` and double-click **SYNC.bat**.

### How the board scores you (0–5 each, 25 points to the leaderboard)

| Criterion | Full marks when |
|---|---|
| Decisions | All 6 made, each with a real reason |
| Fits the brief | Budget, 8 weeks, "don't lock out my CEO", data stays in our cloud |
| ADR | Clear decision, at least one alternative rejected with a reason, honest downside |
| Client answers | Short, honest, no buzzwords, uses evidence from the labs |
| Teamwork | Everyone spoke in the room; the presenter is not the scribe |

---

## Takeaways

- Every design choice is a **trade-off**: cost vs quality, speed vs control, convenience vs privacy.
- A client buys **reasons and evidence**, not technology names.
- The labs give you the evidence: token bars (Lab 7), retrieval quality (Labs 3–4), routing and approvals (Lab 8).
