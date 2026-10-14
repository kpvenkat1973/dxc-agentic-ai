@echo off
REM Runs the client acceptance tests (kept outside this folder) and saves the result in submission\score.txt
cd /d "%~dp0"
python -m pytest -q ..\_homework_tests\test_gatekeeper.py -p no:cacheprovider > submission\score.txt 2>&1
type submission\score.txt
