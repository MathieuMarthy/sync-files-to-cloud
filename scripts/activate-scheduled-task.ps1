# Variables
$TaskName = "Sync-files-task"
$projectPath = "path to the project" # CHANGE ME
$PythonPath = "`"$projectPath\venv\Scripts\pythonw.exe`""
$ScriptPath = "`"$projectPath\main.py`""

# Remove existing task if it exists
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# Create the action to run the Python script
$Action = New-ScheduledTaskAction -Execute $PythonPath -Argument $ScriptPath -WorkingDirectory $projectPath

# Create a trigger to run the task at user logon
$Trigger = New-ScheduledTaskTrigger -AtLogOn

# Create task settings
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -Hidden -StartWhenAvailable

# Register the scheduled task to run
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -User "$env:USERNAME"
