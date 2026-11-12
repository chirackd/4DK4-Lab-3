# 4DK4 Lab 4 — Simulation of ARQ Protocols

Complete S&W, GBN, and SR simulator, experiments 1–7, measured results, and writeup.

- [PDF report](Lab_4_Report.pdf)
- [Readable writeup](REPORT.md)
- [Model](src/arq.c)
- [Validation evidence](results/validation.txt)
- [Per-run data](results/runs.csv) and [means with 95% intervals](results/summary.csv)
- [Six event traces](results/traces/)
- [All 17 plots](figures/), in PNG and vector PDF

## Native Windows / PowerShell

Install Python 3.10+ and native GCC (for example, MinGW-w64), with `python` and
`gcc` on PATH. No WSL, Make, or virtualization is required.

```powershell
.\setup.ps1
.\run_all.ps1
```

Run an individual part with `.\run_exp1.ps1` through `.\run_exp7.ps1`, or the
matching script inside `expN/`. Experiment 3 runs both 3(a) and 3(b). Individual
runs preserve results for other experiments. `python build_report.py` requires
all seven experiments to have completed. Scripts are provided for native Windows;
this delivery was executed and validated on Linux, not Windows.

## Linux / macOS

Requires GCC, Python 3.10+, and the packages in requirements.txt:

```sh
python -m pip install -r requirements.txt
python run.py --workers 4
python check_reliability.py
python build_report.py
```

`python run.py --exp 1` only compiles and verifies, including all six event traces.
`python run.py --plots-only` regenerates plots and summary.csv from saved runs.
All figure simulation data uses markers, without interpolating between points.

## One simulation

```sh
gcc -O2 -std=c11 -I vendor src/arq.c vendor/simlib.c -lm -o arq
./arq 32 16 0.1 0.05 15 400452897 110000 10000 0 0
```

Arguments: `Ws Wr pd pa timeout_ms seed duration_ms warmup_ms N trace`.
`N=0` means backlogged; positive `N` means a finite file. Use warmup=0 for finite
files. The duration is an upper bound; a finite run fails if it cannot finish.
`trace=1` prints event records. The final CSV record is:

`RESULT,efficiency,attempts_per_delivery,completion_ms,attempts,delivered`

For backlogged runs, completion_ms=0. Time units are milliseconds. All ACK and
timer-policy assumptions, and the meaning of efficiency, are stated in the report.
Wr=1 selects GBN receiver/timer policy; Ws=Wr=1 is S&W. For Wr>1, SR uses
cumulative-plus-selective ACKs and per-packet timers. These design choices matter
when comparing against other implementations or lecture formula assumptions.

## Reuse and licensing

The `vendor/` files are unchanged Terence D. Todd simlib files from Lab 3. The
same simlib.c blob occurs in Lab 2. Lab 2's serialized start/end transmission
pattern and both labs' per-experiment PowerShell layout were reused. ARQ protocol
logic is new. Vendor copyright notices are retained; this derivative is provided
under GPL-3.0-or-later, with the complete license in LICENSE.

Source repositories:

- https://github.com/chirackd/4DK4-Lab-3, commit `1089334e06ed30eeedd6e0dadbde3b42b7d273d7`
- https://github.com/chirackd/COMPENG_4DK4_Lab_2, packet_transmission.c blob `0a4e164335825ab1eae9ea8ee61e50013066267c`

Student-ID seed `400452897` comes from the existing Lab 3 report. Main-suite
backlogged runs use five seeds; finite transfers use 30. There are 13,550 stored
main-suite rows, reusing 10,890 unique configurations. See the report for the full
parameter grid and reliability sweep. No original Lab 2 or Lab 3 main-branch code
is modified by this Lab 4 delivery.
