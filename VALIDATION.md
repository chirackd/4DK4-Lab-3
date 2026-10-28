# Validation of the report-aligned simulation profile

The user-supplied `COE4DK4_Lab3_Report.docx` was parsed for its assumptions, relevant
code appendices, tables, and all 13 embedded graphs. Model choices and retained
differences are recorded in `docs/reference_alignment.md`.

## Current local evidence

Platform: Linux, GCC 14.2 in C11 mode, Python 3.12; actual PowerShell 7.5.4 used
for the full entry point. Native Windows execution remains a separate CI check.

- **29 model checks pass**, including queueing-theory limits, exact flow accounting,
  repeatability, capped/uncapped BEB, uniform/exponential alternatives, immediate
  persistence, guard-time service overhead, the bounded single-outstanding
  reservation model, capacity ordering, and completion-target stopping.
- **4 integration tests pass**: build/run under paths containing spaces, individual
  experiment exports, missing-compiler guidance, and replay of a non-binary
  minislot ratio from its exact recorded configuration.
- The full **`run_all.ps1`** pipeline completed **1,905 main replications**, **180
  sensitivity replications**, **16 figures** (PNG and vector PDF), and a new
  CSV-backed report. Raw main output contains **16,600 station records**.
- **7 conceptual trend checks pass** on those actual full-run measurements. They
  compare broad relative behaviors, not golden coordinates from the DOCX.
  Their observations are saved in `lab/results/trend_validation.json`.
- A one-seed quick PowerShell pipeline also completed and correctly labeled its
  shorter run and missing confidence intervals in the generated report.
- The final executable replays **selected configurations across every protocol
  and all N=10 capacity ratios** with identical measured values, using exact CSV
  parameter strings. Configuration floats now retain 17 significant digits;
  earlier 9-digit minislot output could change a replayed trajectory.
- Every main and sensitivity replication verifies arrivals minus completions
  against backlog change, and reconciles station completions. The reservation
  implementation asserts at most N packets in its data stage by default.
- The new PDF contains the group names, all 16 figure captions, current native
  commands, and values read from this run's summaries. Extracted PDF text is
  within page bounds. Representative scientific plots and the first PDF page
  were visually inspected; no exact graphical equality to the DOCX is claimed.

## Representative independently measured trends

For N=10, capped BEB at λ=.5 carries approximately .50 packets/X. At λ=.2 its
mean delay is approximately 176 X, while slotted BEB is approximately 4.08 X.
At λ=1.5, adding the persistent station reduces total throughput from about .95
to .49 packets/X. Reservation busy-fraction capacity for N=10 rises from about
.21 at X/Xr=.25, to .47 at ratio 1, and nearly 1 at ratio 5. These values are
observations, not targets imposed on the simulation.

## Limits

The baseline uses cap 10 as the comparison report's explicit assumption, while
`--beb-cap 0` retains the handout's uncapped variant. Fixed-time stopping and
warmup differ from the reference report's completion-count runs. Overloaded
completed-packet delay is a finite-window statistic; a balanced flow screen does
not prove stationarity. Windows libc random streams can change numerical values.
The existing Windows GitHub Actions job exercises PowerShell, native GCC, model
checks, quick graphs/report generation, and integration tests; its result is not
represented by the local Linux evidence above.
