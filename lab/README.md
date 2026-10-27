# 4DK4 Lab 3 — complete experiment package

Read [Lab_3_Report.pdf](Lab_3_Report.pdf) or the editable [REPORT.md](REPORT.md).
All six experiment groups in the supplied 2026 PDF are implemented and discussed.
Group members: Daniel Chirackal and Ryan Phiby Mathew.

## Native Windows workflow

See the repository-root [README](../README.md) for prerequisites and the
Lab-2-style PowerShell entry points. From the root, run:

```powershell
.\setup.ps1
.\run_all.ps1
```

GCC and Python 3.11+ are sufficient; no WSL, virtualization, or Make is needed.
For a single part use `run_expN.ps1` at the root or in `expN/`. New runs write to
`output/`, with separate part results and the combined plots. The supplied
`lab/results`, `lab/figures`, and report remain the reviewed reference snapshot.

Build-only: `python lab/runtime.py`. Full portable Python workflow:
`python lab/run_all.py`. Add `--quick` for a smoke run, `--output PATH` to retain
another run, or `--skip-analysis` for a standard-library-only simulation run.

`build_report.py` retypesets the original reference writeup and uses fonts bundled
with Matplotlib, so it also runs on Windows. Its narrative examples describe the
reference results; new Windows random streams can differ. It is intentionally
not called by `run_all.ps1` with new data.

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
