param([int]$Workers = 4)
$ErrorActionPreference = 'Stop'
python "$PSScriptRoot/../run.py" --exp 6 --workers $Workers
if ($LASTEXITCODE -ne 0) { throw 'Experiment 6 failed.' }
