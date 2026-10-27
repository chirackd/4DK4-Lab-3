# COMPENG 4DK4 Lab 3 — native Windows experiments

**Daniel Chirackal · Ryan Phiby Mathew**

Run the lab directly in **Windows PowerShell**. WSL, Ubuntu, virtualization, and
GNU Make are not required. Like [COMPENG_4DK4_Lab_2](https://github.com/chirackd/COMPENG_4DK4_Lab_2),
each experiment has a `run_expN.ps1` entry point and its own folder. One shared C
model avoids copying and editing six versions of the simulator.

## First-time setup

You need:

- **Native GCC** available as `gcc` in PowerShell. If you used GCC for Lab 2,
  use that same installation. The build uses C11 for compatibility with older
  MinGW GCC versions. Check with `gcc --version`.
- **Python 3.11 or newer** (3.12 recommended), installed from
  [python.org](https://www.python.org/downloads/windows/), with its launcher/PATH enabled.
  Check with `py -3 --version` or `python --version`.

If GCC is missing, install [MSYS2](https://www.msys2.org/). Open its **UCRT64**
terminal once and run `pacman -S --needed mingw-w64-ucrt-x86_64-gcc`. Add
`C:\msys64\ucrt64\bin` to your Windows user PATH and reopen PowerShell. All lab
commands below run in ordinary PowerShell; MSYS2 supplies the native compiler.

From your existing downloaded repository:

```powershell
cd C:\Users\danie\Downloads\4DK4-Lab-3
.\setup.ps1
.\run_all.ps1
```

`setup.ps1` creates `.venv`, installs the plotting/report packages, compiles the C
simulator, and runs the 19 model checks. No administrator session is needed for
these repository scripts. The virtual environment is selected automatically;
you do not need to activate it.

If PowerShell blocks downloaded scripts, open a fresh session with:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass
```

Then run the commands above. This changes the policy for that session only.

## Run everything, or one experiment

```powershell
# Full scientific runs: 1,525 main replications + 180 sensitivity replications
.\run_all.ps1

# Short end-to-end smoke run; not suitable for lab conclusions
.\run_all.ps1 -Quick

# The Lab-2-style individual entry points
.\run_exp1.ps1
.\run_exp2.ps1
.\exp3\run_exp3.ps1
.\exp4\run_exp4.ps1
.\exp5\run_exp5.ps1
.\exp6\run_exp6.ps1

# Customize a part without editing C headers or recompiling every rate
.\run_exp3.ps1 -SimulationTime 1000000 -Seeds 400452897,333333 -Workers 4

# Keep another run separately
.\run_all.ps1 -OutputDir .\output-repeat
```

Root-level `run_exp1.ps1` through `run_exp6.ps1` are also available. Each folder's
script works when run from inside that folder. Experiments 1 and 2 share the same
fixed-backoff grid; `run_all.ps1` computes it once and exports it to both folders.
Individual scripts generate that part's results; the combined 14 plots require
a complete `run_all.ps1` run. Later runs overwrite files in their chosen output
directory, so use a new `-OutputDir` to retain an earlier run.

## Outputs

```text
exp1/ ... exp6/              # Per-part entry points and notes
scripts/                    # Shared PowerShell helpers
lab/simulator.c             # All protocol modes in one C model
build/simulator.exe         # Native Windows build (ignored by Git)
output/
  exp1/ ... exp6/
    expN_results.txt        # Lab-2-style readable per-run records
    runs.csv                # Per-replication aggregate measurements
    stations.csv            # Per-station measurements
    manifest.json           # Seeds, horizon, replication count
  results/                  # Combined observations and summary tables
  figures/                  # All 14 plots, PNG and vector PDF
```

Default experiments use student-ID seed **400452897** plus 333333, 222222, 44444,
and 987654321. All time units are mean data-packet times, X = 1. Full runs use
1,000,000 X per main replication and discard the first 10%. `-Quick` uses one
seed and short horizons and explicitly identifies itself as a smoke run.

The original [PDF report](lab/Lab_3_Report.pdf), [editable writeup](lab/REPORT.md),
and `lab/results`/`lab/figures` remain the **reviewed Linux reference results**.
Native Windows runs use the same model but libc random streams may differ,
so the new `output` results can differ numerically. The automated runner does
not overwrite the report or silently combine fresh plots with its recorded
numerical discussion. Use your new CSVs and plots when updating that discussion.

## Build or analyze manually

```powershell
.\build.ps1
.\build\simulator.exe --mode slotted --stations 10 --rate .2 --seed 400452897

# After running all experiments and sensitivity:
.\.venv\Scripts\python.exe lab\analyze.py --results-dir output\results --figures-dir output\figures

# Rebuild the reference PDF from its original reference data (portable fonts):
.\.venv\Scripts\python.exe lab\build_report.py
```

For simulations only, `setup.ps1 -SkipDependencies` followed by
`run_all.ps1 -SkipAnalysis` needs just GCC and Python's standard library. Plotting
requires the installed packages. `CC` may select another compatible compiler,
for example `$env:CC = 'clang'`.

Linux/macOS users can use the same native Python runner:

```sh
python3 -m pip install -r lab/requirements.txt
python3 lab/run_all.py
```

The original `lab/Makefile` remains an optional legacy entry point. It is not
used by any PowerShell or Python experiment runner. The GitHub Actions workflow
checks the native PowerShell path on Windows and the Python path on Linux.
See [lab/README.md](lab/README.md) for protocol decisions and experiment mapping.
