[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][ValidateRange(1, 6)][int]$Experiment,
    [ValidateRange(1, 1000000000)][double]$SimulationTime = 1000000,
    [int[]]$Seeds = @(400452897, 333333, 222222, 44444, 987654321),
    [ValidateRange(1, 128)][int]$Workers = 4,
    [string]$OutputDir = (Join-Path (Split-Path -Parent $PSScriptRoot) 'output')
)
. (Join-Path $PSScriptRoot 'Common.ps1')
$arguments = @(
    (Join-Path $ProjectRoot 'lab/run_experiments.py'),
    '--experiment', "$Experiment", '--time', "$SimulationTime",
    '--workers', "$Workers", '--output', $OutputDir, '--seeds'
) + @($Seeds | ForEach-Object { "$_" })
Invoke-LabPython -Arguments $arguments
