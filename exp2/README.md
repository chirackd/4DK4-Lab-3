# Experiment 2: Fixed-mean backoff: throughput, delay-throughput, and attempt load

From this folder, run `.\run_exp2.ps1`; from the repository root, run
`.\run_exp2.ps1` or `.\exp2\run_exp2.ps1`.

Parameters: `-SimulationTime 1000000`, `-Seeds 400452897,333333`, `-Workers 4`,
and `-OutputDir <path>`. Compilation is automatic and does not use Make or WSL.

Outputs go to `output/exp2/runs.csv`, `stations.csv`, `manifest.json`, and
`exp2_results.txt`. The C model is shared in `lab/simulator.c` and links against
the original root-level Simlib files; it is not copied into six divergent versions.

Parts 1 and 2 measure the same fixed-backoff simulations. Running `run_all.ps1`
computes them once and exports their observations to both experiment folders.
Run all experiments before generating the combined 16 plots and fresh report.
