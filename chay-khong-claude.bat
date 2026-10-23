@echo off
rem Chay remote config testcase KHONG can Claude. Chay tren may dang cam dien thoai (USB debugging).
rem   chay-khong-claude.bat <package> [tab SDK, vd 3.4.0 / rating / "daily checkin"]
rem Khong neu tab thi tool tu do ban SDK First Open tu log app roi chon tab.
rem Chay moi case tool chay duoc; case BLOCKED / NOT_VERIFIABLE ghi "Can nguoi xem".
rem Report HTML nam trong out\, Discord gui kem file report (neu co DISCORD_WEBHOOK_URL).
setlocal
cd /d "%~dp0"
if "%~1"=="" (
  echo Cach dung: chay-khong-claude.bat ^<package^> [tab SDK]
  exit /b 1
)
if not exist out mkdir out
set TAB=
if not "%~2"=="" set TAB=--tab "%~2"
".venv\Scripts\rcr-check.exe" --khong-claude --package "%~1" --case all %TAB% > "out\lan-chay-cuoi.json"
set MA=%ERRORLEVEL%
if %MA%==0 (echo Xong. Ket qua JSON: out\lan-chay-cuoi.json - duong dan report o truong "report".)
exit /b %MA%
