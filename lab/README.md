# 4DK4 Lab 3 — complete experiment package

Read [Lab_3_Report.pdf](Lab_3_Report.pdf) or the editable [REPORT.md](REPORT.md).
All six experiment groups in the supplied 2026 PDF are implemented and discussed.
Group members: Daniel Chirackal and Ryan Phiby Mathew.

## Build and run

Use the existing repository checkout. Requirements: GCC, Make, Python 3, and the
Python packages listed in `requirements.txt` (already available in this environment).

```sh
make -C lab
lab/simulator --mode fixed --stations 10 --backoff 10 --rate .1 --seed 400452897 --time 1000000 --warmup 100000
lab/simulator --mode beb --stations 5 --rate .2 --seed 400452897
lab/simulator --mode beb --stations 10 --rate .3 --persistent 0 --seed 400452897
lab/simulator --mode slotted --stations 10 --rate .2 --seed 400452897
lab/simulator --mode reservation --stations 10 --xr .1 --rate .9 --seed 400452897
```

`--time` is the total horizon and `--warmup` is the excluded initial interval.
Defaults: total time 200000, warmup 20000, N=10, lambda=.1, mean backoff=10,
Xr=.1, mode=fixed, seed=333333, persistent=-1 (none). Unit data duration X=1.
Every option takes a value. Output includes one aggregate CSV record, followed by
per-station CSV records. Throughput counts data completions, not reservations.

## Regenerate everything

Run from the repository root:

```sh
make -C lab
python3 lab/test_simulator.py
python3 lab/run_experiments.py --time 1000000 --seeds 400452897 333333 222222 44444 987654321 --workers 4
python3 lab/run_sensitivity.py
python3 lab/analyze.py
python3 lab/build_report.py
```

The main sweep performs 1525 replications; sensitivity adds 180. `run_experiments.py`
asserts exact packet conservation and station completion accounting in every run.
It overwrites generated CSVs; retain them first if you want an earlier result set.

`analyze.py` creates 14 figures, each as PNG and vector PDF, plus numerical summaries.
`build_report.py` produces Markdown and PDF from the same report content definition.
A few narrative examples are intentionally recorded numbers, so if changing the grid,
seeds, model or durations, revise the report discussion and accuracy table as well.
`results/provenance.json` records the delivered source checksums and environment versions.
For bitwise reproducibility use the recorded Linux/libc and GCC: Simlib uses libc rand().

## Experiment mapping

| PDF part | Mode and outputs |
|---|---|
| 1 | `fixed`; `fixed_delay_arrival` |
| 2 | `fixed`; `fixed_throughput_arrival`, `fixed_delay_throughput`, `fixed_throughput_load` |
| 3 | `beb`; `beb_comparison` |
| 4 | `beb --persistent 0`; `persistent_delay`, `persistent_throughput` |
| 5 | `slotted`; `slotted_delay_throughput`, `slotted_throughput_arrival`, `slotted_throughput_load` |
| 6 | `reservation`; `reservation_delay`, `reservation_throughput`, `reservation_capacity` |
| Accuracy | `accuracy_runlength`, `results/sensitivity*.csv` |

## Model decisions worth retaining

- The PDF describes exponential fixed-mean backoff, while the supplied code draws
  uniform backoff. This implementation follows the PDF for Parts 1–2 and documents
  the discrepancy. The original sources are unchanged and are not used as if their
  results came from the exponential model.
- BEB is uncapped as specified. Slotted BEB uses integer slot windows including zero.
- In Part 4 only station 0 retries at the next unit time boundary; other stations
  retain unslotted BEB. This resolves “next slot” before the separate slotted part.
- Reservations and data run concurrently. A successful reservation dequeues the
  station packet into the shared data queue, allowing that station's next reservation.
  Mean data length is 1 and reservation backoff is measured in minislots.
- Filled plot markers indicate a descriptive flow-balance check, not proven stability.
  Whiskers are seed min–max, not confidence intervals. Overload delay is the completed-
  packet finite-window mean; unfinished packets are not silently counted as delivered.
- The conventional Poisson ALOHA curves are derived analytical references. The actual
  lecture slides were not provided. Capture and finite-source correlations can cause
  measured throughput to exceed those reference peaks.

The available Data skills' shared web-report runtime and referenced shared resources
were unavailable in this machine. The requested academic writeup is therefore delivered
as a standalone PDF/Markdown package, not a hosted editable Data app. No publication or
course submission has been performed.
