@echo off
rem Chay remote config testcase KHONG can Claude. Chay tren may dang cam dien thoai (USB debugging).
rem   chay-khong-claude.bat <package> [tab SDK, vd 3.4.0 / rating / "daily checkin"]
rem Khong neu tab thi tool tu do ban SDK First Open tu log app roi chon tab.
rem Chay moi case tool chay duoc; case BLOCKED / NOT_VERIFIABLE ghi "Can nguoi xem".
rem Ket qua ghi sau moi case vao out\rc-*.luot.json; bi tat giua chung thi chay tiep:
rem   .venv\Scripts\rcr-check.exe --package <package> --khong-claude --tiep out\rc-....luot.json
rem Report HTML nam trong out\, Discord gui kem file report (neu co DISCORD_WEBHOOK_URL).
setlocal
cd /d "%~dp0"
if "%~1"=="" (
  echo Cach dung: chay-khong-claude.bat ^<package^> [tab SDK]
  exit /b 1
)
if not exist out mkdir out
rem Kiem may, ban debuggable, sheet, RAM truoc - hong o day thi khoi ton 1-2 gio chay.
".venv\Scripts\rcr-check.exe" --package "%~1" --preflight > nul
rem `if errorlevel 1` bo lot ma thoat am (tien trinh crash) -> so sanh khac 0.
if not "%ERRORLEVEL%"=="0" (
  echo Chua chay duoc: xem cac dong LOI o tren.
  exit /b 1
)
set TAB=
if not "%~2"=="" set TAB=--tab "%~2"
".venv\Scripts\rcr-check.exe" --khong-claude --package "%~1" --case all %TAB% > "out\lan-chay-cuoi.json"
set MA=%ERRORLEVEL%
if %MA%==0 (echo Xong. Ket qua JSON: out\lan-chay-cuoi.json - duong dan report o truong "report".)
exit /b %MA%
