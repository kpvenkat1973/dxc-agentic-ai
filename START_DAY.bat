@echo off
REM ===== START_DAY.bat 3   (or 4, 5 ...)  opens that day's page. Double-click = it asks. =====
REM It saves your work, gets the trainer's new content and fixes any clash by itself. No git commands needed.
cd /d C:\AskIT\dxc-agentic-ai || (echo [!!] Repo not found at C:\AskIT\dxc-agentic-ai & pause & exit /b 1)
if "%~1"=="" goto ask
set ASKIT_DAY=%~1
goto go
:ask
set /p ASKIT_DAY=Which day? Type 3 or 4 and press Enter: 
:go
echo Opening Day %ASKIT_DAY% ...
echo Saving your work...
git add -A >nul 2>&1
git commit -q -m "auto-save before update" >nul 2>&1
echo Getting new content from the trainer...
git fetch -q upstream
if errorlevel 1 (echo [!!] No connection to GitHub - using the version you already have & goto run)
git merge -q upstream/main -X ours --no-edit >nul 2>&1
if errorlevel 1 (
  git merge --abort >nul 2>&1
  git merge -s ours -q --no-edit upstream/main >nul 2>&1
)
call .venv\Scripts\activate.bat
python tools\post_update.py
:run
call .venv\Scripts\activate.bat
pip install -q -r requirements.txt
python tools\portal.py
pause
