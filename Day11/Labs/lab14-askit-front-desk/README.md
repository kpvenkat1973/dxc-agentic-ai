# Lab 14: AskIT Front Desk

**Session 11 · From a Python script to a product people can use** · about 50 minutes · **no code to write**

| What we do | Why | Outcome | How |
|---|---|---|---|
| Open a real web page for AskIT. Watch the answer **stream** word by word, then switch to a **Task** screen for long jobs. Then break it: slow tool, tool error, dropped connection. | Users do not run Python. They need a screen that shows progress, survives a bad network and never hides a failure. | You can choose **Chat** or **Task** for a use case, and explain timeouts, reconnect and why a restart can cost money twice. | One command opens a page in your browser. Buttons only. |

---

## STEP 0. Open the right folder (do this first)

**We are doing Lab 14 · AskIT Front Desk now (`lab14-askit-front-desk`).**

1. Open **VS Code** → **File** → **Open Folder**.
2. Paste this path and click **Select Folder**:

```
C:\AskIT\dxc-agentic-ai\Day11\Labs\lab14-askit-front-desk
```

3. **Terminal** → **New Terminal**. The prompt must end with **lab14-askit-front-desk**.

Folder not there? Open `C:\AskIT\dxc-agentic-ai` and double-click **SYNC.bat**, then repeat.

## STEP 1. Start it

Is an older lab app still running? Click its terminal and press **Ctrl+C**.

```
python run.py
```

The browser opens the page. If not, the terminal prints an address like `http://127.0.0.1:8014`. Open it. Keep the terminal open.

At the top of the page choose the model: **Offline stand-in** (works always) or **AWS Bedrock**.

## STEP 2. Follow the page (start with the 🏁 Start here tab)

The page has its own instructions: **🏁 Start here** lists, tab by tab, what to do, what you will see and what you learn. This table is the short version.

| Tab | What you do |
|---|---|
| **Chat** | Pick a question, press Send. Watch words arrive, tool cards appear, the clock run. |
| **Task** | Start a long job. Close the page tab, open it again, the job is still there. Press **Cancel** on another. |
| **Break it** | Press ▶ Run this on the five tries (slow tool, tool error, dropped connection, resume vs restart, leave a long job). Change the **timeout** and the **reconnect** choice (resume / restart / none). |
| **How it works** | One diagram: events, ids, resume. |
| **Lessons learnt** | Unlocks after you answer the two questions at the bottom of tabs 1 to 3. |

## The 4 things to remember

1. Chat with the slow tool on and timeout 3 s. The page says it gave up. Who paid for the work already done?
2. Drop the connection with **resume**. Then with **restart**. Compare the cost line.
3. Tool error on: does the page show the real reason or a friendly lie?
4. Task screen: why is polling every 1 s better than every 0.1 s?

## If something goes wrong

| Problem | Fix |
|---|---|
| Port busy | Close other lab terminals. The app tries ports 8014 to 8029 by itself. |
| Page blank | Press **Ctrl+F5**. |
| Bedrock error | Choose **Offline stand-in**. The lesson is the same. |

Never put AWS keys in files, GitHub, wikis or chat.
