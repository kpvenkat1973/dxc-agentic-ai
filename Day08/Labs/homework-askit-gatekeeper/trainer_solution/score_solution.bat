@echo off
REM Runs the tests against the TRAINER model solution in this folder.
cd /d "%~dp0"
python -m pytest -q test_solution.py -p no:cacheprovider
