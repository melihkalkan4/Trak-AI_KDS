<#
.SYNOPSIS
    Remove the TrakAI_FLOV_Daily scheduled task.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\uninstall_flov_scheduled_task.ps1
#>

$taskName = "TrakAI_FLOV_Daily"
$existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($null -eq $existing) {
    Write-Host "No task named '$taskName' is registered."
    exit 0
}
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
Write-Host "✓ Unregistered scheduled task '$taskName'" -ForegroundColor Green
