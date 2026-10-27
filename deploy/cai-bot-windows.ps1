# Cai rcr-bot thanh Scheduled Task tren Windows: tu bat khi dang nhap, chay lai khi loi.
# Chay: powershell -ExecutionPolicy Bypass -File deploy\cai-bot-windows.ps1   (khong can admin)
# Cau hinh doc tu bien User cua Windows hoac ~/.config/rcr/bot.env (KEY=VALUE).
$ErrorActionPreference = "Stop"

$Repo = Split-Path -Parent $PSScriptRoot
$Bin = Join-Path $Repo ".venv\Scripts\rcr-bot.exe"
$Out = Join-Path $Repo "out"
$Log = Join-Path $Out "bot-run.log"

if (-not (Test-Path $Bin)) {
    Write-Error "Chua co $Bin. Chay: cd $Repo; .venv\Scripts\python -m pip install -e `".[dev,bot]`""
}
if (-not (Get-Command claude -ErrorAction SilentlyContinue)) { Write-Error "Khong thay 'claude' trong PATH" }
if (-not (Get-Command adb -ErrorAction SilentlyContinue)) { Write-Error "Khong thay 'adb' trong PATH" }
New-Item -ItemType Directory -Force $Out | Out-Null

# conhost --headless: chay AN, khong cua so. Ban dau chay cmd.exe thang -> hien cua so den,
# dong cua so la giet bot giua luot cai (0xC000013A, do 27/10/2026).
# Vong for /l vo han: bot thoat thi ~30s sau tu bat lai. RestartCount cua Task Scheduler chi
# chay lai khi task KHONG KHOI DONG duoc, khong chay lai khi bot dang chay roi thoat.
# Cho bang ping vi `timeout` trong console an bao loi va thoat ngay -> vong quay lien tuc.
$Lap = "for /l %i in (0,0,1) do (`"$Bin`" >> `"$Log`" 2>&1 & ping -n 31 127.0.0.1 >nul)"
$Lenh = "--headless cmd.exe /s /c `"set PYTHONIOENCODING=utf-8&& $Lap`""
$Action = New-ScheduledTaskAction -Execute "conhost.exe" -Argument $Lenh -WorkingDirectory $Repo
$Trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$Settings = New-ScheduledTaskSettingsSet -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
# Cai lai: dung ban cu truoc (ca bot con cua no) keo 2 bot cung tra loi.
Stop-ScheduledTask -TaskName "rcr-bot" -ErrorAction SilentlyContinue
Get-Process rcr-bot -ErrorAction SilentlyContinue | Stop-Process -Force
Register-ScheduledTask -TaskName "rcr-bot" -Action $Action -Trigger $Trigger -Settings $Settings -Force | Out-Null
Start-ScheduledTask -TaskName "rcr-bot"

Write-Host "Da cai task rcr-bot (tu bat khi dang nhap). Log: $Log"
Write-Host "Dung: Stop-ScheduledTask rcr-bot; Stop-Process -Name rcr-bot   Go: Unregister-ScheduledTask rcr-bot -Confirm:`$false"
