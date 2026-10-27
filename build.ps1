[CmdletBinding()]
param([switch]$Force)
. (Join-Path $PSScriptRoot 'scripts/Common.ps1')
$arguments = @((Join-Path $ProjectRoot 'lab/runtime.py'))
if ($Force) { $arguments += '--force' }
Invoke-LabPython -Arguments $arguments
