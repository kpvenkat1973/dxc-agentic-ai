@echo off
REM ===== START_DAY.bat 5 : syncs, then opens that day's page. (Same as SYNC.bat + open page) =====
if not defined ASKIT_SD (
  set ASKIT_SD=1
  copy /y "%~f0" "%TEMP%\askit_sd.bat" >nul
  call "%TEMP%\askit_sd.bat" %*
  exit /b
)
cd /d C:\AskIT\dxc-agentic-ai || (echo [!!] Repo not found & pause & exit /b 1)
set N=%~1
if "%N%"=="" set /p N=Which day? Type 5 or 6 and press Enter: 
set D=0%N%
set D=%D:~-2%
call SYNC.bat
start "" "C:\AskIT\dxc-agentic-ai\Day%D%\Content\index.html"
