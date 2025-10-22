# Variables
$TaskName = "Sync-files-task"

# Check if the task exists
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Write-Host "Removing scheduled task '$TaskName'..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Scheduled task '$TaskName' has been successfully removed." -ForegroundColor Green
} else {
    Write-Host "Scheduled task '$TaskName' does not exist." -ForegroundColor Red
}
