[CmdletBinding()]
param(
    [Alias('Time')][ValidateRange(1, 1000000000)][double]$SimulationTime = 1000000,
    [int[]]$Seeds = @(400452897, 333333, 222222, 44444, 987654321),
    [ValidateRange(1, 128)][int]$Workers = 4,
    [string]$OutputDir = (Join-Path $PSScriptRoot 'output')
)
$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'exp1/run_exp1.ps1') `
    -SimulationTime $SimulationTime -Seeds $Seeds -Workers $Workers -OutputDir $OutputDir
