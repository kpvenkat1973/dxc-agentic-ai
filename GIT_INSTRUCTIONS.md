# Git Instructions — Participants (use on your VM)

Trainer repo: **https://github.com/askanilkumar/dxc-agentic-ai**
Your copy (fork): **https://github.com/YOUR-GITHUB/dxc-agentic-ai**
Your folder on the VM: **`C:\AskIT\dxc-agentic-ai`** (never move or rename it)

**How it works:** the trainer publishes content to his repo (called `upstream`). You keep your own copy on GitHub (called `origin`).
- **Pull** = trainer's new content → your VM (`upstream`)
- **Push** = your results → your GitHub fork (`origin`)

`origin` and `upstream` are just **nicknames** Git keeps for two GitHub web addresses. They are **not folders** — nothing is created on disk. Check them anytime with `git remote -v`.

**Your Command Prompt opens at `C:\Users\Admin>` (or your user folder) — that is normal.** The commands below move you to `C:\AskIT` themselves (`cd /d C:\AskIT\dxc-agentic-ai`). Each time you open a new Command Prompt for git, run that `cd` line first.

You never push to the trainer's repo. You do **not** need `git init` — `git clone` creates the repo for you.

---

## PART 1 — First time only (Day 1, ~10 min)

Open **Command Prompt** (Windows key → type `cmd` → Enter).

### 1. Check Git works
```
git --version
```

### 2. Tell Git who you are (once per VM)
```
git config --global user.name "Your Full Name"
git config --global user.email "your-github-email@example.com"
git config --global pull.rebase false
git config --global --add safe.directory C:/AskIT/dxc-agentic-ai
```
Check: `git config --global --list`

### 3. Fork the trainer repo (in the browser)
1. Sign in to **your** GitHub account.
2. Open https://github.com/askanilkumar/dxc-agentic-ai
3. Click **Fork** → **Create fork**. You now have `https://github.com/YOUR-GITHUB/dxc-agentic-ai`

### 4. Clone YOUR fork into C:\AskIT (replace YOUR-GITHUB)
Run from any folder — `mkdir` creates `C:\AskIT` and `cd` moves you there:
```
mkdir C:\AskIT
cd /d C:\AskIT
git clone https://github.com/YOUR-GITHUB/dxc-agentic-ai.git dxc-agentic-ai
cd dxc-agentic-ai
```
A GitHub sign-in window may open — sign in and click authorize (it remembers you after that).

### 5. Link the trainer repo as `upstream` (SETUP.bat also does this)
```
git remote add upstream https://github.com/askanilkumar/dxc-agentic-ai.git
git remote -v
```
You must see **origin = your fork** and **upstream = askanilkumar/dxc-agentic-ai**.
If `origin` shows `askanilkumar` you cloned the wrong repo → fix:
```
git remote set-url origin https://github.com/YOUR-GITHUB/dxc-agentic-ai.git
```

### 6. Run setup
Double-click **`C:\AskIT\dxc-agentic-ai\SETUP.bat`** (see setup\SETUP_GUIDE.md). Every line must say **[OK]**.

---

## PART 2 — Every morning: get the day's code and HTML

**Easy way:** in Command Prompt run **`START_DAY.bat 3`** (or 4, 5 ...). Double-click also works: it asks "Which day?". It **saves your work, gets the trainer's new content, fixes any clash by itself** and opens that day's page. You never need `git stash`, even if you forgot Day End. Keep the black window open.

**Manual way** (if START_DAY says "could not update"):
```
cd /d C:\AskIT\dxc-agentic-ai
git status
git fetch upstream
git merge upstream/main --no-edit
```
(Same result as `git pull upstream main --no-edit`.)

A new `DayNN` folder appears: `DayNN\Content\index.html` (today's page) and `DayNN\Labs\` (today's lab code).

---

## PART 3 — During and end of class: push your results

**Easy way:** last page of the session → click **🏁 Day End · Save & Push**. It saves your XP, checks your labs, commits and pushes.

**Manual way** (if the button fails, or you want to save mid-day):
```
cd /d C:\AskIT\dxc-agentic-ai
git add .
git commit -m "Day 1 - your name"
git push origin HEAD
```
Check on GitHub: open your fork → you should see your latest commit and the `progress\` folder.

---

## Fixing common problems

| Problem | Fix |
|---|---|
| `git` is not recognised | Tell the trainer — Git not on PATH |
| Push asks for a password / fails | Sign in through the GitHub browser popup (passwords no longer work for git); make sure you cloned **your** fork |
| `403` / permission denied on push | `origin` is the trainer repo. Run: `git remote set-url origin https://github.com/YOUR-GITHUB/dxc-agentic-ai.git` |
| Push rejected (fork is ahead/behind) | `git pull origin main --no-edit` then push again |
| Merge conflict after pulling | You edited a file outside `DayNN\Labs\` or `teams\`. Run `git merge --abort`, then call the trainer |
| `Author identity unknown` | Redo step 2 (git config user.name / user.email) |
| "dubious ownership" | Run the `safe.directory` command from step 2 |
| Want to see what changed | `git status` and `git log --oneline -5` |

## Rules
0. Forgot Day End or edited a wrong file? Do nothing special: START_DAY handles it. Your lab code is always kept; trainer files (`tools\`, `DayNN\Content\`, `tests\`) are always reset to the trainer's version.
1. Edit **only** files in the `DayNN\Labs\` folders and your own `teams\team-x\` folder.
2. Never put keys in code or push `.env` (it is ignored automatically).
3. Pull every morning **before** you start; push at the end of every day.
4. Never use `git push --force`.
