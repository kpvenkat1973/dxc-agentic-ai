@echo off
REM Double-click shortcut: connect your free LangSmith account (Part D).
cd /d "%~dp0"
python langsmith_setup.py
pause
