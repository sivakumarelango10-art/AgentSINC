$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$backend = Join-Path $repoRoot "backend"
$python = Join-Path $backend ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    throw "Backend virtual environment not found. Run the setup commands in backend/README.md first."
}

$ollama = Get-Process -Name "ollama" -ErrorAction SilentlyContinue
if (-not $ollama) {
    Write-Warning "Ollama desktop process was not detected. Start Ollama before assigning missions."
}

$apiCommand = "Set-Location '$backend'; & '$python' -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
$workerCommand = "Set-Location '$backend'; & '$python' -m app.worker"

Start-Process -FilePath "powershell.exe" -ArgumentList @("-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $apiCommand)
Start-Sleep -Seconds 2
Start-Process -FilePath "powershell.exe" -ArgumentList @("-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $workerCommand)

Write-Host "AgentSINC API and worker launched in separate PowerShell windows." -ForegroundColor Green
Write-Host "API: http://127.0.0.1:8000/healthz"
Write-Host "Keep both windows and Ollama running for local background work."
