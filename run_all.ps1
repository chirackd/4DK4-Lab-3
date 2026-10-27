[CmdletBinding()]
param(
    [switch]$Quick,
    [switch]$SkipAnalysis,
    [ValidateRange(1, 128)][int]$Workers = 4,
    [string]$OutputDir = (Join-Path $PSScriptRoot 'output')
)
. (Join-Path $PSScriptRoot 'scripts/Common.ps1')
$arguments = @((Join-Path $ProjectRoot 'lab/run_all.py'), '--workers', "$Workers", '--output', $OutputDir)
if ($Quick) { $arguments += '--quick' }
if ($SkipAnalysis) { $arguments += '--skip-analysis' }
Invoke-LabPython -Arguments $arguments
