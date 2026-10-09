@echo off
rem Usage:  .\score.bat vibe      or  .\score.bat sdd      (16 v1 tests)
rem         .\score.bat vibe v2   or  .\score.bat sdd v2   (24 v2 tests)
set T=test_triage.py
if /I "%2"=="v2" set T=test_triage_v2.py
if not exist "%1\" (echo Folder %1 not found. Use: score vibe  or  score sdd & exit /b 1)
if not exist "..\_client_tests\%T%" (echo Client tests not found in ..\_client_tests & exit /b 1)
copy /Y "..\_client_tests\%T%" "%1\%T%" >nul
python -m pytest -q %1/%T%
del "%1\%T%" >nul 2>&1
