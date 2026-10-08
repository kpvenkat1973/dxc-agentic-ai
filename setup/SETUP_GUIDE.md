# One-Time Setup (Session 1 · Lab A · ~20 min)

Everything happens **on your Azure VM**. Follow the steps exactly — every VM must look the same.

## Before you start (already on the VM)
Python 3.11+ · Git for Windows · VS Code · Edge or Chrome. Check in Command Prompt:
```
python --version
git --version
```

## Step 1 — Fork the course repo
1. On the VM browser, sign in to **your** GitHub account.
2. Open the trainer repo link shared in the Teams chat.
3. Click **Fork** → keep the name **dxc-agentic-ai** → **Create fork**.
   (Trainer repo: https://github.com/askanilkumar/dxc-agentic-ai)

## Step 2 — Clone your fork to C:\AskIT
Open **Command Prompt** and run (replace `YOUR-GITHUB`):
```
mkdir C:\AskIT
cd C:\AskIT
git clone https://github.com/YOUR-GITHUB/dxc-agentic-ai.git dxc-agentic-ai
```
✅ You now have `C:\AskIT\dxc-agentic-ai` (the last word in the command renames the folder — keep it exactly)

Git commands (identity, daily pull, daily push): see **GIT_INSTRUCTIONS.md**.

## Step 3 — Run SETUP.bat
In File Explorer, double-click **`C:\AskIT\dxc-agentic-ai\SETUP.bat`**. It will:

| Step | You do |
|---|---|
| Link trainer repo, create Python environment, install packages | Wait (2–4 min) |
| Ask your **name**, **GitHub username**, **team (A/B/C/D)** | Type them |
| First push to GitHub | If a GitHub sign-in window opens → **sign in** |
| Open `.env` in Notepad | Paste the keys the trainer shares → **Save** → close Notepad |
| Environment check | Every line must say **[OK]** |

## Step 4 — Open the project in VS Code
1. VS Code → **File → Open Folder** → `C:\AskIT\dxc-agentic-ai`
2. `Ctrl+Shift+P` → **Python: Select Interpreter** → choose the one with **.venv**
3. Open a terminal (`Ctrl+`\``) — you should see `(.venv)` at the start of the line.

## Step 5 — Start the day
In Command Prompt: `cd C:\AskIT\dxc-agentic-ai` then **`START_DAY.bat 1`** (Day 1) or **`START_DAY.bat 2`** (Day 2). The session page opens at `http://localhost:8765`. Keep the black window open.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `python` not recognised | Tell the trainer — Python not on PATH on your VM |
| `[!!] Repo must be at C:\AskIT\dxc-agentic-ai` | You cloned somewhere else. Repeat Step 2 exactly |
| Push failed | Sign in to GitHub when prompted; check you cloned **your fork**, not the trainer repo |
| `[!!] AWS credentials` | Re-check keys in `.env` (no spaces, no quotes), save, run `python tools\verify_env.py` |
| Bedrock `AccessDenied` / model not found | Call the trainer — model access or model ID issue |
| Page doesn't open | Open `http://localhost:8765` manually while START_DAY.bat window is open |
| `(.venv)` not showing / `ModuleNotFoundError` | Run `.venv\Scripts\activate` in **Command Prompt** (START_DAY.bat does this by itself) |
| PowerShell says "running scripts is disabled" | Use **Command Prompt**, or run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first |
| AWS console opens in the wrong region | Top-right region menu → **US East (N. Virginia) us-east-1** |
| `.env` not visible in Explorer | It starts with a dot. Open it with `notepad .env` from `C:\AskIT\dxc-agentic-ai` |
| `verify_env.py` not found | It is in `tools\`: `python tools\verify_env.py` |
