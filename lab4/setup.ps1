$ErrorActionPreference = 'Stop'
python -m pip install -r "$PSScriptRoot/requirements.txt"
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
