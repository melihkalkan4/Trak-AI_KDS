<#
.SYNOPSIS
    Install a Windows Task Scheduler job that runs the FLOV daily update.

.DESCRIPTION
    Registers a daily task named "TrakAI_FLOV_Daily" that runs
    scripts/flov_daily_update.py with the project venv's Python.

    Triggers daily at 06:30 local time (after ERA5 reanalysis publishes
    yesterday's data — typically 06:00 CET = 09:00 TR).  Misfires (laptop
    asleep, machine off) are caught up by the StartWhenAvailable flag.

    Logs to logs/flov_scheduled_<yyyyMMdd>.log via -RedirectStandardOutput.

.PARAMETER TaskTime
    HH:mm string, default 06:30.

.PARAMETER User
    Username to run as (default: current).

.EXAMPLE
    # Run elevated (Task Scheduler requires admin to register tasks for SYSTEM)
    powershell -ExecutionPolicy Bypass -File scripts\install_flov_scheduled_task.ps1

.EXAMPLE
    powershell -File scripts\install_flov_scheduled_task.ps1 -TaskTime 07:15

.NOTES
    To uninstall:    Unregister-ScheduledTask -TaskName "TrakAI_FLOV_Daily" -Confirm:$false
    To run manually: Start-ScheduledTask  -TaskName "TrakAI_FLOV_Daily"
    To inspect:      Get-ScheduledTaskInfo -TaskName "TrakAI_FLOV_Daily"
#>

[CmdletBinding()]
param(
    [string]$TaskTime = "06:30",
    [string]$User = $env:USERNAME
)

$ErrorActionPreference = "Stop"

$ProjectRoot = (Get-Item -Path $PSScriptRoot).Parent.FullName
$VenvPython  = Join-Path $ProjectRoot "venv\Scripts\python.exe"
$Script      = Join-Path $ProjectRoot "scripts\flov_daily_update.py"
$LogDir      = Join-Path $ProjectRoot "logs"

if (-not (Test-Path $VenvPython)) {
    throw "venv python not found at $VenvPython — create the venv first."
}
if (-not (Test-Path $Script)) {
    throw "FLOV daily script not found at $Script."
}
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
}

# Build the action: cmd /c so we can redirect stdout/stderr to a daily log
$logTarget = Join-Path $LogDir "flov_scheduled_%date:~10,4%%date:~4,2%%date:~7,2%.log"
$cmdArgs   = "/c `"`"$VenvPython`" `"$Script`" >> `"$logTarget`" 2>&1`""

$action = New-ScheduledTaskAction `
    -Execute "cmd.exe" `
    -Argument $cmdArgs `
    -WorkingDirectory $ProjectRoot

# Daily trigger
$trigger = New-ScheduledTaskTrigger -Daily -At $TaskTime

# Settings: catch up if the laptop was asleep, retry on transient failure
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -DontStopOnIdleEnd `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit ([TimeSpan]::FromHours(2)) `
    -RestartCount 3 `
    -RestartInterval ([TimeSpan]::FromMinutes(15))

# Principal: interactive (no SYSTEM, no stored password)
$principal = New-ScheduledTaskPrincipal -UserId $User -LogonType Interactive -RunLevel Limited

# Register (overwrite existing)
$taskName = "TrakAI_FLOV_Daily"
Register-ScheduledTask `
    -TaskName    $taskName `
    -Description "TRAK-AI FLOV — daily fetch + predict + validate + alert" `
    -Action      $action `
    -Trigger     $trigger `
    -Settings    $settings `
    -Principal   $principal `
    -Force | Out-Null

Write-Host ""
Write-Host "✓ Registered scheduled task '$taskName'" -ForegroundColor Green
Write-Host "  Trigger : daily at $TaskTime (StartWhenAvailable on misfire)"
Write-Host "  Python  : $VenvPython"
Write-Host "  Script  : $Script"
Write-Host "  Logs    : $LogDir\flov_scheduled_<yyyyMMdd>.log"
Write-Host ""
Write-Host "Run now      : Start-ScheduledTask  -TaskName '$taskName'"
Write-Host "Status       : Get-ScheduledTaskInfo -TaskName '$taskName'"
Write-Host "Uninstall    : Unregister-ScheduledTask -TaskName '$taskName' -Confirm:`$false"
