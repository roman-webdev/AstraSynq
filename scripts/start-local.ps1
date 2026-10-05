param([string]$PythonExecutable = '', [string]$PnpmExecutable = '', [int]$ApiPort=8011, [int]$UiPort=4184, [switch]$ExistingPostgres, [switch]$SkipInstall)
$ErrorActionPreference = 'Stop'
if (!$env:ASTRASYNQ_MODE) { $env:ASTRASYNQ_MODE='development' }
if ($env:ASTRASYNQ_MODE -eq 'production') { throw 'Use the documented production deployment procedure; local launcher is development only.' }
$projectRoot = Split-Path -Parent $PSScriptRoot
$stateDir = Join-Path $projectRoot '.local'
if (Test-Path -LiteralPath (Join-Path $stateDir 'processes.json')) { throw 'A recorded session exists. Run scripts/stop-local.ps1 first.' }
if (!$PythonExecutable) {
    $pythonTool = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonTool) { $PythonExecutable = $pythonTool.Source }
    else { throw 'Install Python 3.12 or supply -PythonExecutable.' }
}
if (!$PnpmExecutable) {
    $pnpmTool = Get-Command pnpm -ErrorAction SilentlyContinue
    if ($pnpmTool) { $PnpmExecutable = $pnpmTool.Source }
    else { throw 'Install pnpm 11.25.0 or supply -PnpmExecutable.' }
}
$nodeTool = Get-Command node -ErrorAction Stop
if (!(Test-Path -LiteralPath $PythonExecutable) -or !(Test-Path -LiteralPath $PnpmExecutable)) { throw 'Python/pnpm unavailable. Supply their executable paths.' }
foreach ($port in @($ApiPort, $UiPort)) {
    if (netstat -ano | Select-String ":$port\s+.*LISTENING") { throw "Port $port is already used. Stop the existing preview or select other ApiPort/UiPort values." }
}
New-Item -ItemType Directory -Force -Path $stateDir | Out-Null
$venvPython = Join-Path $projectRoot '.venv/Scripts/python.exe'
if (!(Test-Path -LiteralPath $venvPython)) {
    & $PythonExecutable -m venv (Join-Path $projectRoot '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'Python environment creation failed.' }
}
if (!$SkipInstall) {
    & $venvPython -m pip install -r (Join-Path $projectRoot 'backend/requirements-dev.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Backend installation failed.' }
}
if (!$ExistingPostgres) {
    & $venvPython (Join-Path $projectRoot 'scripts/setup-postgres.py')
    if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL setup failed.' }
}
Push-Location (Join-Path $projectRoot 'backend')
try {
    & $venvPython -m alembic upgrade head
    if ($LASTEXITCODE -ne 0) { throw 'Database migration failed.' }
    & $venvPython -m app.store
    if ($LASTEXITCODE -ne 0) { throw 'Demo seed failed.' }
} finally { Pop-Location }
$env:ASTRASYNQ_API_URL = "http://127.0.0.1:$ApiPort"
Push-Location (Join-Path $projectRoot 'frontend')
try {
    if (!$SkipInstall) {
        & $PnpmExecutable install --frozen-lockfile
        if ($LASTEXITCODE -ne 0) { throw 'Frontend installation failed.' }
    }
    & $nodeTool.Source node_modules/typescript/bin/tsc --noEmit; if($LASTEXITCODE -eq 0){ & $nodeTool.Source node_modules/vite/bin/vite.js build --configLoader native }; if($LASTEXITCODE -eq 0){ & $nodeTool.Source scripts/prepare-sites-build.mjs }
    if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
} finally { Pop-Location }
$apiProcess = $null
try {
    $basePython = & $venvPython -c 'import sys; print(sys._base_executable)'
    $env:PYTHONPATH = (Join-Path $projectRoot 'backend') + ';' + (Join-Path $projectRoot '.venv/Lib/site-packages')
    if (!$env:AUTH_ALLOWED_ORIGINS) { $env:AUTH_ALLOWED_ORIGINS="http://127.0.0.1:$ApiPort,http://localhost:$ApiPort,http://127.0.0.1:$UiPort,http://localhost:$UiPort" }
    $apiProcess = Start-Process -FilePath $basePython -ArgumentList "-m uvicorn app.main:app --host 127.0.0.1 --port $ApiPort --no-access-log" -WorkingDirectory (Join-Path $projectRoot 'backend') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $stateDir 'api.log') -RedirectStandardError (Join-Path $stateDir 'api-error.log')
    $workerProcess = Start-Process -FilePath $basePython -ArgumentList '-m app.worker' -WorkingDirectory (Join-Path $projectRoot 'backend') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $stateDir 'worker.log') -RedirectStandardError (Join-Path $stateDir 'worker-error.log')
    $uiProcess = Start-Process -FilePath $nodeTool.Source -ArgumentList "node_modules/vite/bin/vite.js preview --configLoader native --host 127.0.0.1 --port $UiPort --strictPort" -WorkingDirectory (Join-Path $projectRoot 'frontend') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $stateDir 'ui.log') -RedirectStandardError (Join-Path $stateDir 'ui-error.log')
    @{api=@{id=$apiProcess.Id;start=$apiProcess.StartTime.ToUniversalTime().ToString('o')};worker=@{id=$workerProcess.Id;start=$workerProcess.StartTime.ToUniversalTime().ToString('o')};ui=@{id=$uiProcess.Id;start=$uiProcess.StartTime.ToUniversalTime().ToString('o')}} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $stateDir 'processes.json')
    $connected=$false
    for($attempt=0;$attempt -lt 20;$attempt++) {
        Start-Sleep -Milliseconds 500
        try {
            if($apiProcess.HasExited -or $uiProcess.HasExited -or $workerProcess.HasExited){throw 'A preview process exited.'}
            $health=Invoke-RestMethod "http://127.0.0.1:$ApiPort/health/ready" -TimeoutSec 2
            if($health.version -ne '0.5.0-rc.1'){throw 'Unexpected API version.'}
            Invoke-WebRequest "http://127.0.0.1:$UiPort/" -TimeoutSec 2 | Out-Null
            $connected=$true;break
        } catch { }
    }
    if (!$connected) { throw 'Preview readiness failed. See .local logs; stop using scripts/stop-local.ps1.' }
    Write-Output "AstraSynq ready: http://127.0.0.1:$UiPort/#/login (API PID $($apiProcess.Id), UI PID $($uiProcess.Id))"
    Write-Output 'First launch: create your local Admin using backend app.bootstrap_admin (hidden password prompt); see docs/authentication.md. No default credentials.'
} catch {
    if ($workerProcess -and !(Test-Path -LiteralPath (Join-Path $stateDir 'processes.json'))) { Stop-Process -Id $workerProcess.Id -ErrorAction SilentlyContinue }
    if ($apiProcess -and !(Test-Path -LiteralPath (Join-Path $stateDir 'processes.json'))) { Stop-Process -Id $apiProcess.Id -ErrorAction SilentlyContinue }
    throw
}



