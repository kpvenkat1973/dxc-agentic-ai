# Lab 12: AskIT Break-it Range

**Session 11 · Attack your own agent, then defend it** · about 40 minutes · **no code to write**

| What we do | Why | Outcome | How |
|---|---|---|---|
| Run **6 attacks** on AskIT (secret leak, poisoned ticket, personal data, VIP reset, bulk reset, endless loop). Switch **5 defences** on and off. Find the smallest set that stops every attack and still lets 3 normal requests through. | An agent that can act can be tricked into acting. Clients ask "is it safe?". The honest answer is layers, tested. | You can name the 6 risks, explain why no single defence is enough, and show a pass/fail test. | One command opens an app. Tick boxes and press buttons. |

---

## STEP 0. Open the right folder

**We are doing Lab 12 · AskIT Break-it Range now (`lab12-askit-break-it-range`).**

1. **VS Code** → **File** → **Open Folder** → paste:

```
C:\AskIT\dxc-agentic-ai\Day11\Labs\lab12-askit-break-it-range
```

2. **Terminal** → **New Terminal** (prompt ends with **lab12-askit-break-it-range**).

## STEP 1. Start it

Ctrl+C any older lab app first, then:

```
python run.py
```

Open `http://localhost:8501` if the browser does not open. Leave the model on **Gullible stand-in**: every group sees the same result.

## STEP 2. The tabs

**The app has the same instructions in its first tab, 🏁 Start here:** what to do, what you will see and what you learn, tab by tab.

1. **Meet the attacks.** Run each attack with no defences. All 6 win.
2. **Defend one attack.** Tick one defence, run one attack. See where each defence acts.
3. **Full test.** Tick a set of defences. Goal: 6 stopped and 3 normal requests fine with the **fewest** layers.
4. **How it works.** Where each defence sits, OWASP names, products clients ask about.

## The 5 defences in one minute

Each defence sits at a different place. None sees everything.

| | Defence | What it does | Try it in Tab 2 | What you should see | The learning |
|---|---|---|---|---|---|
| **D1** | Input filter | Blocks a message that contains a phrase from a short bad-phrase list | Attack **A1** (print your instructions) | Blocked before the model runs | Easy to build, but a polite attack passes, and a normal request can be blocked by mistake. Check **Normal L1**. |
| **D2** | Output filter | Hides the secret code and e-mail addresses in the answer | Attacks **A1** and **A3** | The answer arrives with the secret or the e-mail hidden | It cleans the answer but does not stop the action. Too late if a password was already reset. |
| **D3** | Tool guard (code) | A rule in code in front of the tool: no VIP resets, one change per request | Attacks **A2**, **A4** and **A5** | The tool call is refused. The VIP is safe and bulk stops at one change | The strongest fix for risky actions: a rule in code, not a request to the model. |
| **D4** | Limits | Stops the request after 3 model calls | Attack **A6** (cost runaway) | The request stops at 3 calls | The only one that protects your bill. It does nothing for secrets or VIPs. |
| **D5** | Managed guardrail | A managed service checks the user's text and the answer (prompt attacks, personal data) | Attacks **A1** and **A3** | Blocked or hidden, like D1 and D2 but smarter | It catches many ways of saying "ignore your rules". It does **not** see inside tool results or judge whether an action is allowed. |

**What to remember**
1. **No single defence stops all 6 attacks.** Each one covers a different place: input, output, tool, limits.
2. **Attacks hidden inside a ticket (A2) never pass through the user's text**, so input filters cannot see them.
3. **Fewer layers = less cost and fewer false alarms.** Always run the 3 normal requests as well, not only the attacks.

## Challenge (team game)

Smallest perfect set wins. Hint: one defence is a text filter that annoys real users, so check for false alarms.

## Notes

- D5 uses a managed guardrail only if the trainer gives an ID. Otherwise it is simulated. The sidebar says which.
- A real model may refuse some attacks on its own. Write down what you see.

Never put AWS keys in GitHub, wikis or chat.
