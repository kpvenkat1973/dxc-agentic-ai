@echo off
REM ===== SYNC.bat : 2-way sync. Trainer's new files -> your VM. Your work -> your GitHub fork. =====
REM Run it any time: morning, end of day, or when told "sync". Safe to run again and again.
if not defined ASKIT_SYNC (
  set ASKIT_SYNC=1
  copy /y "%~f0" "%TEMP%\askit_sync.bat" >nul
  call "%TEMP%\askit_sync.bat" %*
  exit /b
)
set REPO=C:\AskIT\dxc-agentic-ai
set UP=https://github.com/askanilkumar/dxc-agentic-ai.git
cd /d %REPO% || (echo [!!] Repo not found at %REPO% & pause & exit /b 1)
git config --global --add safe.directory C:/AskIT/dxc-agentic-ai >nul 2>&1
git config gc.auto 0 >nul 2>&1
git config maintenance.auto false >nul 2>&1
git config user.email >nul 2>&1 || git config --global user.email "student@askit.local"
git config user.name  >nul 2>&1 || git config --global user.name "AskIT Student"
git remote get-url upstream >nul 2>&1 || git remote add upstream %UP%
git merge --abort >nul 2>&1
git rebase --abort >nul 2>&1

echo [1/3] Saving your work on this VM...
git add -A >nul 2>&1
git commit -q -m "sync %DATE% %TIME%" >nul 2>&1

echo [2/3] Getting the trainer's new content...
git fetch -q upstream
if errorlevel 1 (echo [!!] Cannot reach GitHub - skipping download & goto push)
git merge upstream/main -X ours --no-edit -q >nul 2>&1
if errorlevel 1 (
  git merge --abort >nul 2>&1
  echo     Clash found - copying the trainer's files one by one...
  for /f "delims=" %%f in ('git diff --name-only --diff-filter=A HEAD upstream/main') do git checkout upstream/main -- "%%f" >nul 2>&1
  for /f "delims=" %%f in ('git diff --name-only --diff-filter=M HEAD upstream/main ^| findstr /v /i "/Labs/"') do git checkout upstream/main -- "%%f" >nul 2>&1
  git add -A >nul 2>&1
  git commit -q -m "sync trainer files" >nul 2>&1
)

:push
echo [3/3] Saving your work to your GitHub...
git push -q origin HEAD >nul 2>&1
if errorlevel 1 (
  git fetch -q origin >nul 2>&1
  git merge origin/main -X ours --no-edit -q >nul 2>&1
  git push -q origin HEAD >nul 2>&1
)
if errorlevel 1 (echo [!!] Push failed - take a screenshot of this window and call the trainer) else (echo [OK] Sync complete)
pause
