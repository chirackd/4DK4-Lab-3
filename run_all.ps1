param([int]$Workers = 4)
$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    python run.py --workers $Workers
    if ($LASTEXITCODE -ne 0) { throw 'Simulation or validation failed.' }
    python check_reliability.py
    if ($LASTEXITCODE -ne 0) { throw 'Reliability check failed.' }
    python verify_reference.py
    if ($LASTEXITCODE -ne 0) { throw 'Reference/analysis checks failed.' }
    python test_oracle.py
    if ($LASTEXITCODE -ne 0) { throw 'Independent oracle checks failed.' }
    python build_report.py
    if ($LASTEXITCODE -ne 0) { throw 'Report generation failed.' }
} finally { Pop-Location }
