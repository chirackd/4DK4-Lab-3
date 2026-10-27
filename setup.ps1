[CmdletBinding()]
param([switch]$SkipDependencies)
. (Join-Path $PSScriptRoot 'scripts/Common.ps1')
if (-not (Get-Command gcc -ErrorAction SilentlyContinue) -and -not $env:CC) {
    throw 'GCC was not found. Add your native GCC bin directory (for example C:\msys64\ucrt64\bin) to PATH and reopen PowerShell. See README.md.'
}
Invoke-LabPython -Arguments @('-c', 'import sys; assert sys.version_info >= (3, 11), "Python 3.11+ required"')
$venv = Join-Path $ProjectRoot '.venv'
if (-not (Test-Path -LiteralPath $venv)) {
    Invoke-LabPython -Arguments @('-m', 'venv', $venv)
}
if (-not $SkipDependencies) {
    Invoke-LabPython -Arguments @('-m', 'pip', 'install', '-r', (Join-Path $ProjectRoot 'lab/requirements.txt'))
}
Invoke-LabPython -Arguments @((Join-Path $ProjectRoot 'lab/runtime.py'))
Invoke-LabPython -Arguments @((Join-Path $ProjectRoot 'lab/test_simulator.py'))
Write-Host 'Setup complete. Run .\run_all.ps1, or an expN\run_expN.ps1 script.'
