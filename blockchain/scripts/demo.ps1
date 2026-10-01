# PowerShell Live Demonstration Launcher for SIH-26228 Blockchain Evidence Layer
param(
    # Override with the interpreter of your virtual environment, e.g. -PythonPath .\.venv\Scripts\python.exe
    [string]$PythonPath = "python"
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$WorkspaceRoot = Split-Path -Parent (Split-Path -Parent $ScriptDir)
$DemoScript = Join-Path $ScriptDir "demo.py"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " Launching Trustworthy CV Integrity & Blockchain Demo CLI" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan

if (Test-Path $PythonPath) {
    & $PythonPath $DemoScript
} else {
    Write-Host "Specified Python executable not found at $PythonPath. Using default python..." -ForegroundColor Yellow
    python $DemoScript
}
