# Lab 7: AskIT Memory Playground

**Session 7 · Context, compaction and memory** · about 45 minutes · **no code to write**

| What we do | Why | Outcome | How |
|---|---|---|---|
| Chat with AskIT and watch, on a chart, how much text is sent to the model at every step. Switch compaction and long-term memory on and off. | The bill, the speed and the privacy risk of an agent all depend on what it remembers. | You can explain, with numbers, why long chats cost more, what compaction saves and loses, and what a memory store should keep. | One command opens an app. Then only buttons, sliders and switches. |

---

## STEP 0. Open the right folder (do this first)

**We are doing Lab 7 · AskIT Memory Playground now (`lab07-askit-memory-playground`).**

1. Open **VS Code**.
2. Click **File** → **Open Folder**.
3. Paste this path and click **Select Folder**:

```
C:\AskIT\dxc-agentic-ai\Day07\Labs\lab07-askit-memory-playground
```

4. Click **Terminal** → **New Terminal**. The prompt must end with **lab07-askit-memory-playground**.

Folder not there? In File Explorer open `C:\AskIT\dxc-agentic-ai` and double-click **SYNC.bat**. Then repeat step 2.

## STEP 1. Start the app

In the VS Code terminal, type this line and press Enter:

```
python run.py
```

The first time it installs a few packages (about a minute). Then your browser opens the app.
If the browser does not open, open this address yourself:

```
http://localhost:8501
```

Keep the black/terminal window open while you work. To stop the app later, click in the terminal and press **Ctrl+C**.

The sidebar on the left shows **1 · Model**. Leave it on **AWS Bedrock**. If Bedrock shows a problem, pick another model. **Offline stand-in** always works (no AI, just rules) so you can still follow the lab.

---

## Part 1 · Tab "1 · Chat + context meter" (15 min)

**Idea:** the model has no memory of its own. At every step it is sent the whole chat again.

1. Check the sidebar: **Summarise old messages** is **OFF**.
2. Press **▶ Next script question**. Read the question and the answer.
3. Press it again, until all 8 questions are done (or press **⏩ Play all 8** once).
4. Look at the right side: one bar per model call. The bars get taller.
5. Read the 3 numbers: model calls, tokens sent, cost of this chat, and the monthly cost at 10,000 chats a day.
6. Open **👀 What the model sees right now**. This is exactly what is sent at the next step.

Now with compaction:

7. In the sidebar press **🆕 New chat**.
8. Switch **Summarise old messages** **ON**. Leave the first slider at **1500**.
9. Play the 8 questions again.
10. Watch the bars: they drop when the summary is written. Open **🗜️ The summary**. What did it keep? What did it drop?

## Part 2 · Tab "2 · Compare: compaction OFF vs ON" (10 min)

**Idea:** compaction is a trade: much less cost, a little less detail.

1. Press **⚖️ Run the 8-question script twice**. Wait about a minute.
2. Read the three numbers at the top: tokens without, tokens with (and the % saved), monthly cost.
3. Look at the line chart: two lines, one flat-ish, one growing.
4. Read the last two answers on both sides. Did AskIT still know the first ticket (TKT-0004) and the employee id (EMP-1002)?
5. In the sidebar move **Summarise when the chat reaches** to **800**. Press the button again. Summaries now fire almost every call: does the extra summary cost eat the saving?

## Part 3 · Tab "3 · Long-term memory" (10 min)

**Idea:** a new chat starts empty. Only a store keeps facts across chats.

1. Press **💬 Chat A: tell AskIT about your laptop**.
2. Press **💬 Chat B (new chat): which laptop do I have?** AskIT should know: Dell XPS 13.
3. Look at the table: this is what the store holds for you.
4. In the sidebar switch **Remember facts across chats** **OFF**. Press **Chat B** again. AskIT no longer knows.
5. Switch it back **ON**. Change **You are** to **Rahul Reddy**. Press **Chat B**. Rahul cannot see Priya's notes.
6. Change back to **Priya Iyer** and press **🗑️ Forget me**. The notes are gone.

## Part 4 · Tab "4 · How it works" (3 min)

Read the picture and the two tables. They answer: which file does what, what each piece becomes in production, and the trade-offs a client will ask about.

## Part 5 · Tab "5 · Questions + takeaway" (5 min)

1. Answer the 3 questions in one or two lines each.
2. Press **💾 Save my answers**. The app writes `submission\lab07_answers.md` for you.
3. In File Explorer open `C:\AskIT\dxc-agentic-ai` and double-click **SYNC.bat** to push your work.

---

## Which file does what

| File | What it does |
|---|---|
| `run.py` | Installs the packages (first time only) and starts the app. `run.bat` does the same on double-click |
| `app.py` | The screen: tabs, buttons, sliders, charts |
| `memory_agent.py` | Builds the agent: tools, middleware (summary + context meter), checkpointer (short-term memory), store (long-term memory) |
| `model_factory.py` | Picks the model: Bedrock (main), Azure, OpenAI or Offline. Holds the approximate prices |
| `diagram.py` | Draws the picture in tab 4 |
| `..\..\..\askit_core\tools.py` | The 4 helpdesk tools from Day 5 |

## If something goes wrong

| What you see | What to do |
|---|---|
| `can't open file ... run.py` | You are in the wrong folder. Repeat STEP 0 |
| `python` is not recognized | Close VS Code, open it again, repeat STEP 0 |
| The browser shows nothing | Open `http://localhost:8501` yourself |
| "Port 8501 is already in use" | Another app (Lab 2 or Lab 8) is still running. Close its terminal window, then run `python run.py` again |
| Sidebar says Bedrock is not ready | Tell the trainer. Meanwhile pick **Offline stand-in** |
| An answer starts with ⚠️ | The model call failed (often throttling). Press the button again |

## Stretch (optional, for those who like code)

1. Open `memory_agent.py`. Find `SCRIPT`. Add a 9th question, save, press **🧹 Reset all** in the app and play again.
2. In `memory_agent.py` find `SummarizationMiddleware(...)`. What do `trigger` and `keep` mean? Match them to the two sliders.

## What you learned

- Every model call re-sends the whole chat, so cost and delay grow with the chat.
- Compaction summarises the old part and keeps the newest messages word for word: big saving, small risk of losing a detail, plus one extra call to write the summary.
- A store keeps **facts** per user across chats. Keep it small, never store secrets, and give users a way to delete it.
