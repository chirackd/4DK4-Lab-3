param([int]$Workers = 4)
$ErrorActionPreference = 'Stop'
python "$PSScriptRoot/../run.py" --exp 3 --workers $Workers
if ($LASTEXITCODE -ne 0) { throw 'Experiment 3 failed.' }
