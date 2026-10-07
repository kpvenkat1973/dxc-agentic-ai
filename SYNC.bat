@echo off
REM SYNC.bat - participant VM: get trainer's new files + save your work to your fork
cd /d C:\AskIT\dxc-agentic-ai || (echo Folder not found & pause & exit /b 1)
git config core.pager ""
git add -A
git commit -m "save" >nul 2>&1
git pull upstream main --no-rebase -X ours --no-edit
git push origin main
echo.
echo SYNC done. If you see "rejected" or "error" above, call the trainer.
pause
