@echo off
REM Double-click shortcut: run the exam as LangSmith experiments (Part D).
cd /d "%~dp0"
python langsmith_lab.py
pause
