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

# cmd /s /c giu nguyen nhay trong; log noi them vao out\bot-run.log.
$Lenh = "/s /c `"set PYTHONIOENCODING=utf-8&& `"$Bin`" >> `"$Log`" 2>&1`""
$Action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument $Lenh -WorkingDirectory $Repo
$Trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$Settings = New-ScheduledTaskSettingsSet -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName "rcr-bot" -Action $Action -Trigger $Trigger -Settings $Settings -Force | Out-Null
Start-ScheduledTask -TaskName "rcr-bot"

Write-Host "Da cai task rcr-bot (tu bat khi dang nhap). Log: $Log"
Write-Host "Dung: Stop-ScheduledTask rcr-bot   Go: Unregister-ScheduledTask rcr-bot -Confirm:`$false"
