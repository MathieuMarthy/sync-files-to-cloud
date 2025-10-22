# Variables
$TaskName = "Sync-files-task"

# Check if the task exists
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Write-Host "Stopping scheduled task '$TaskName' if running..." -ForegroundColor Yellow
    Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue

    # Wait a moment to ensure the task has stopped
    Start-Sleep -Seconds 2

    Write-Host "Starting scheduled task '$TaskName'..." -ForegroundColor Yellow
    Start-ScheduledTask -TaskName $TaskName

    Write-Host "Scheduled task '$TaskName' has been successfully restarted." -ForegroundColor Green
} else {
    Write-Host "Scheduled task '$TaskName' does not exist. Please run 'activate-scheduled-task.ps1' first." -ForegroundColor Red
}
