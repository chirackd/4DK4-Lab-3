# Experiment 1: Fixed-mean backoff: delay versus arrival rate

From this folder, run `.\run_exp1.ps1`; from the repository root, run
`.\run_exp1.ps1` or `.\exp1\run_exp1.ps1`.

Parameters: `-SimulationTime 1000000`, `-Seeds 400452897,333333`, `-Workers 4`,
and `-OutputDir <path>`. Compilation is automatic and does not use Make or WSL.

Outputs go to `output/exp1/runs.csv`, `stations.csv`, `manifest.json`, and
`exp1_results.txt`. The C model is shared in `lab/simulator.c` and links against
the original root-level Simlib files; it is not copied into six divergent versions.

Parts 1 and 2 measure the same fixed-backoff simulations. Running `run_all.ps1`
computes them once and exports their observations to both experiment folders.
Run all experiments before generating the combined 16 plots and fresh report.
