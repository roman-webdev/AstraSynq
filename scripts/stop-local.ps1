$ErrorActionPreference='Stop'
$stateFile=Join-Path (Split-Path -Parent $PSScriptRoot) '.local/processes.json'
if (!(Test-Path -LiteralPath $stateFile)) { Write-Output 'No recorded preview session.'; exit }
$record=Get-Content -LiteralPath $stateFile -Raw | ConvertFrom-Json
foreach($entry in @($record.api,$record.ui,$record.worker)) {
    if (!$entry) { continue }
    $process=Get-Process -Id $entry.id -ErrorAction SilentlyContinue
    if (!$process) { continue }
    # PowerShell 7 may deserialize ISO strings to DateTime automatically.
    $expected=if ($entry.start -is [datetime]) { $entry.start.ToUniversalTime() } else { [datetime]::Parse($entry.start).ToUniversalTime() }
    if($process.StartTime.ToUniversalTime().Ticks -ne $expected.Ticks) { throw 'Recorded PID was reused; refusing to stop another process.' }
    Stop-Process -Id $entry.id -Force -ErrorAction Stop
    $process.WaitForExit(5000) | Out-Null
    if (!$process.HasExited) { throw 'Recorded process did not exit; state file preserved.' }
}
Remove-Item -LiteralPath $stateFile
Write-Output 'Stopped the recorded AstraSynq API/frontend/worker; database preserved.'

