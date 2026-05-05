# PowerShell script to process Excel files on a schedule
# This can be run via Windows Task Scheduler

$scriptPath = "C:\Users\castrk05_adm\AppData\Local\Programs\Python\PROJECTS\Classify"
$pythonPath = "C:\Users\castrk05_adm\AppData\Local\Programs\Python\Python313\python.exe"
$processScript = "process_all_files.py"

# Change to the script directory
Set-Location $scriptPath

# Run the processing script
& $pythonPath $processScript

# Log the execution
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$logMessage = "$timestamp - Excel file processing completed"
Add-Content -Path "processing_log.txt" -Value $logMessage
