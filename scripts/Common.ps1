# Shared helpers compatible with Windows PowerShell 5.1 and PowerShell 7.
Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot

function Get-LabPython {
    foreach ($candidate in @(
        (Join-Path $ProjectRoot '.venv/Scripts/python.exe'),
        (Join-Path $ProjectRoot '.venv/bin/python')
    )) {
        if (Test-Path -LiteralPath $candidate) {
            return [PSCustomObject]@{ Command = $candidate; Prefix = @() }
        }
    }
    foreach ($name in @('py', 'python', 'python3')) {
        $found = Get-Command $name -ErrorAction SilentlyContinue
        if ($null -ne $found) {
            $prefix = @()
            if ($name -eq 'py') { $prefix = @('-3') }
            return [PSCustomObject]@{ Command = $found.Source; Prefix = $prefix }
        }
    }
    throw 'Python 3.11 or newer was not found. Install Python from python.org, enable PATH, and reopen PowerShell.'
}

function Invoke-LabPython {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)
    $python = Get-LabPython
    $command = $python.Command
    $pythonArguments = @($python.Prefix) + $Arguments
    & $command @pythonArguments
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed (exit $LASTEXITCODE): $($Arguments -join ' ')"
    }
}
