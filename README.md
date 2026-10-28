# COMPENG 4DK4 Lab 3 — native Windows experiments

**Daniel Chirackal · Ryan Phiby Mathew**

Run directly in Windows PowerShell, with native GCC and Python. No WSL, Ubuntu,
virtualization, or GNU Make is required. The `exp1/`–`exp6/` folders and
`run_expN.ps1` scripts follow the preferred Lab 2 structure; one shared C model
keeps the protocol implementations consistent.

## Setup and run

You need GCC on PATH (`gcc --version`) and Python 3.11+ (3.12 recommended).
The C11 build works with older MinGW GCC installations used for Lab 2.

```powershell
cd C:\Users\danie\Downloads\4DK4-Lab-3
git pull origin main
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\setup.ps1
.\run_all.ps1
```

`setup.ps1` creates/selects `.venv`, installs pinned Python packages, builds the C
simulator, and runs 29 model checks. If the packages are already installed, use
`setup.ps1 -SkipDependencies`. The execution-policy command affects this terminal
only. No administrator session is needed for these repository scripts.

If GCC is missing, install [MSYS2](https://www.msys2.org/), use its UCRT64 terminal
once to run `pacman -S --needed mingw-w64-ucrt-x86_64-gcc`, add
`C:\msys64\ucrt64\bin` to your user PATH, and reopen ordinary PowerShell.

```powershell
# Complete scientific sweep: 1,905 main + 180 sensitivity replications
.\run_all.ps1

# Short end-to-end pipeline check, not a reliability assessment
.\run_all.ps1 -Quick

# Per-part scripts (root aliases exist for all six parts)
.\run_exp1.ps1
.\run_exp2.ps1
.\exp3\run_exp3.ps1
.\exp4\run_exp4.ps1
.\exp5\run_exp5.ps1
.\exp6\run_exp6.ps1

# Customize the horizon/seeds or preserve another run
.\run_exp3.ps1 -SimulationTime 1000000 -Seeds 400452897,333333 -Workers 4
.\run_all.ps1 -OutputDir .\output-repeat
```

Scripts can also run from inside their experiment folder. Parts 1 and 2 measure
the same fixed-backoff cases; `run_all.ps1` computes them once and exports to both
part folders. Individual scripts produce that part's CSV/text results; run all
parts and sensitivity for the combined figures/report. Reusing an output folder
overwrites its generated files.

## Model alignment with the supplied comparison report

`COE4DK4_Lab3_Report.docx` was parsed for assumptions, code behavior, and conceptual
graph trends. **Its numerical data and authors are not reused.** All default runs
use our seed 400452897 and four independent comparison seeds.

- Fixed mean backoff is **uniform [0, 2B)**, matching the original supplied C.
- BEB uses **min(Nc, 10)**, an explicitly documented choice in the comparison
  report. `--beb-cap 0` remains available for the literal uncapped handout model.
- The persistent station retries **immediately**, without an added boundary wait.
- A slotted payload remains duration **1**; the slot is **1 + 2ε**, ε=.001.
  Continuous BEB waits are aligned to the next permitted transmission window.
- Each station has **one outstanding reservation/data packet**, retained at its
  FIFO head until data completion. Station and data queue links are independent.
- Reservation capacity is the **exact data-channel busy fraction at λ=2/X**,
  measured for N=5,10,20 and ratios X/Xr=.25–100.
- Delay-versus-throughput plots exclude flow-imbalanced points. Delay-versus-arrival
  plots retain overload points as hollow markers. Seed error bars are 95%
  Student-t intervals; no simulated observations are interpolated or fitted.

The default still uses a fixed 1,000,000-time-unit horizon with 10% warmup, unlike
the reference report's completion-count stopping. Exact coordinates can therefore
differ, particularly overloaded delay. The goal is the same conceptual trends,
not forced numerical agreement. See [reference_alignment.md](docs/reference_alignment.md)
for every change, retained difference, and optional model control.

## Outputs

```text
build/simulator.exe          # Native Windows executable; ignored by Git
output/
  exp1/ ... exp6/
    expN_results.txt         # Readable per-replication records
    runs.csv
    stations.csv
    manifest.json
  results/                  # Combined raw data, summary tables, trend checks
  figures/                  # 16 PNG figures and 16 vector PDFs
  REPORT.md                 # Writeup generated from this run's own numbers
  Lab_3_Report.pdf
```

The full workflow now regenerates the report from its own CSVs, eliminating the
old hardcoded numerical narrative. `lab/results`, `lab/figures`, and the checked-in
[PDF report](lab/Lab_3_Report.pdf) are a refreshed full-run example for the new
baseline profile. Earlier models/results remain in Git history. Windows libc
random streams can differ from Linux; each local report uses the local results.

The 16 graphs include the originally requested families plus same-station capture,
persistent-system total throughput, reservation station-count comparisons, and
run-length sensitivity. Seven broad qualitative checks are recorded in
`results/trend_validation.json`; no values are modified to satisfy them.

## Manual/native Python commands

```powershell
.\build.ps1
.\build\simulator.exe --mode beb --stations 10 --rate .2 --seed 400452897 --beb-cap 10

# Explicit alternate model, not the default comparison profile:
.\build\simulator.exe --mode beb --stations 10 --rate .2 --beb-cap 0

.\.venv\Scripts\python.exe lab\analyze.py --results-dir output\results --figures-dir output\figures
.\.venv\Scripts\python.exe lab\build_report.py --results-dir output\results --figures-dir output\figures --output-dir output
```

For simulations only, `setup.ps1 -SkipDependencies` and `run_all.ps1 -SkipAnalysis`
need just GCC and Python's standard library. Linux/macOS can run
`python3 lab/run_all.py` after installing `lab/requirements.txt`. The legacy
Makefile remains optional; PowerShell/Python runners never call Make.

[VALIDATION.md](VALIDATION.md) records model/integration checks and the actual
platforms tested. GitHub Actions includes native Windows PowerShell and Linux jobs.
