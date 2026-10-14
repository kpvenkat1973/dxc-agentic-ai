@echo off
REM Runs the MCP test against the TRAINER model solution in this folder.
cd /d "%~dp0"
python -m pip install -q fastmcp==4.1.0
python test_gatekeeper_server.py
