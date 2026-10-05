param([int]$ApiPort=8012,[int]$UiPort=4185,[switch]$RecoveryStages,[string]$TestNamePattern='')
$ErrorActionPreference='Stop'
if($RecoveryStages){
    # Each stage owns fresh servers: reseeding DB does not reset API rate-limit state.
    foreach($pattern in @('^en: all screens, review errors, responsive and import regression$','login|navigation, direct forbidden|expired or revoked|integration permissions','')){
        & $PSCommandPath -ApiPort $ApiPort -UiPort $UiPort -TestNamePattern $pattern
    }
    return
}
$projectRoot=Split-Path -Parent $PSScriptRoot
$pythonPath=Join-Path $projectRoot '.venv/Scripts/python.exe'
$nodePath=(Get-Command node -ErrorAction Stop).Source
$testUrl=$env:TEST_DATABASE_URL
if (!$testUrl) { $testUrl='postgresql+psycopg://astrasynq@127.0.0.1:55432/astrasynq_test' }
if (!$testUrl.EndsWith('/astrasynq_test')) { throw 'Browser QA requires a separate database named astrasynq_test.' }
foreach ($port in @($ApiPort,$UiPort)) {
    if (netstat -ano | Select-String ":$port\s+.*LISTENING") { throw "QA port $port already in use." }
}
$previous=@{}
foreach($name in @('DATABASE_URL','TEST_DATABASE_URL','AUTH_ALLOWED_ORIGINS','AUTH_COOKIE_SECURE','ASTRASYNQ_API_URL','ASTRASYNQ_PREVIEW_URL','PYTHONPATH','ASTRASYNQ_MODE')) { $previous[$name]=[Environment]::GetEnvironmentVariable($name,'Process') }
$apiProcess=$null;$uiProcess=$null
try {
    $env:DATABASE_URL=$testUrl;$env:TEST_DATABASE_URL=$testUrl
    $env:AUTH_ALLOWED_ORIGINS="http://127.0.0.1:$UiPort,http://127.0.0.1:$ApiPort"
    $env:AUTH_COOKIE_SECURE='false';$env:ASTRASYNQ_MODE='test'
    $env:ASTRASYNQ_API_URL="http://127.0.0.1:$ApiPort"
    $env:ASTRASYNQ_PREVIEW_URL="http://127.0.0.1:$UiPort"
    Push-Location (Join-Path $projectRoot 'backend')
    try { & $pythonPath -c 'from app.database import engine; from sqlalchemy import text; c=engine.connect(); assert c.execute(text("SELECT 1")).scalar()==1; c.close(); print("Test PostgreSQL ready")'; if($LASTEXITCODE -ne 0){throw 'Test PostgreSQL not ready.'}; & $pythonPath -m alembic upgrade head; if($LASTEXITCODE -ne 0){throw 'Test migration failed.'} } finally {Pop-Location}
    Push-Location (Join-Path $projectRoot 'frontend')
    try { & $nodePath node_modules/typescript/bin/tsc --noEmit; if($LASTEXITCODE -eq 0){ & $nodePath node_modules/vite/bin/vite.js build --configLoader native }; if($LASTEXITCODE -eq 0){ & $nodePath scripts/prepare-sites-build.mjs }; if($LASTEXITCODE -ne 0){throw 'Build failed.'} } finally {Pop-Location}
    $basePython=& $pythonPath -c 'import sys; print(sys._base_executable)'
    $env:PYTHONPATH=(Join-Path $projectRoot 'backend')+';'+(Join-Path $projectRoot '.venv/Lib/site-packages')
    $apiProcess=Start-Process -FilePath $basePython -ArgumentList "-m uvicorn app.main:app --host 127.0.0.1 --port $ApiPort --no-access-log" -WorkingDirectory (Join-Path $projectRoot 'backend') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $projectRoot '.local/browser-api.log') -RedirectStandardError (Join-Path $projectRoot '.local/browser-api-error.log')
    $uiProcess=Start-Process -FilePath $nodePath -ArgumentList "node_modules/vite/bin/vite.js preview --configLoader native --host 127.0.0.1 --port $UiPort --strictPort" -WorkingDirectory (Join-Path $projectRoot 'frontend') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $projectRoot '.local/browser-ui.log') -RedirectStandardError (Join-Path $projectRoot '.local/browser-ui-error.log')
    $connected=$false
    for($n=0;$n -lt 30;$n++) {
        try {if($apiProcess.HasExited -or $uiProcess.HasExited){throw 'QA server exited.'};$health=Invoke-RestMethod "$env:ASTRASYNQ_API_URL/health/ready" -TimeoutSec 2;if($health.version -ne '0.5.0-rc.1'){throw 'Unexpected API version.'};Invoke-WebRequest $env:ASTRASYNQ_PREVIEW_URL -TimeoutSec 2 | Out-Null;$proxyHealth=Invoke-RestMethod "$env:ASTRASYNQ_PREVIEW_URL/health/ready" -TimeoutSec 2;if($proxyHealth.version -ne $health.version -or $proxyHealth.status -ne 'ready'){throw 'Frontend API proxy not ready.'};$csrf=Invoke-WebRequest "$env:ASTRASYNQ_PREVIEW_URL/api/v1/auth/csrf" -TimeoutSec 2;if($csrf.StatusCode -ne 200 -or $csrf.Headers['Content-Type'] -notmatch 'application/json' -or !(($csrf.Content | ConvertFrom-Json).csrf_token)){throw 'Frontend CSRF bootstrap not ready.'};$connected=$true;break} catch {Start-Sleep -Milliseconds 300}
    }
    if(!$connected){throw 'Browser QA servers did not become ready.'}
    Push-Location (Join-Path $projectRoot 'frontend')
    try {
        Write-Host "Isolated QA: frontend=$env:ASTRASYNQ_PREVIEW_URL API=$env:ASTRASYNQ_API_URL DB=astrasynq_test"
        $testArgs=@('--test')
        if($TestNamePattern){$testArgs+="--test-name-pattern=$TestNamePattern"}
        $testArgs+='tests/i18n.e2e.mjs'
        & $nodePath @testArgs
        if($LASTEXITCODE -ne 0){throw 'Browser regression failed.'}
    } finally {Pop-Location}
} finally {
    foreach($processEntry in @($apiProcess,$uiProcess)) { if($processEntry -and !$processEntry.HasExited){Stop-Process -Id $processEntry.Id -ErrorAction SilentlyContinue} }
    foreach($name in $previous.Keys){[Environment]::SetEnvironmentVariable($name,$previous[$name],'Process')}
}

