# Lab 3 model and reproducible analysis

Start with the root [README](../README.md). Run `setup.ps1` then `run_all.ps1`
natively in PowerShell. No WSL or Make is required. The run creates fresh
`output/results`, 16 figures, and a report whose numbers are read from that run.

The checked-in [PDF](Lab_3_Report.pdf), [Markdown](REPORT.md), results, and figures
are a complete regenerated example under the **report-aligned-v2** configuration.
See [model differences](../docs/reference_alignment.md) for the supplied DOCX
interpretation and the retained differences in stopping rule/seeds.

| Part | Driver mode | Main figures |
|---|---|---|
| 1 | `fixed` | `fixed_delay_arrival` |
| 2 | `fixed` | `fixed_throughput_arrival`, `fixed_delay_throughput`, `fixed_throughput_load` |
| 3 | `beb --beb-cap 10` | `beb_comparison`, `capture_repeat_fraction` |
| 4 | `beb --persistent 0` | `persistent_delay`, `persistent_throughput`, `persistent_total_throughput` |
| 5 | `slotted --beb-cap 10 --guard .001` | `slotted_delay_throughput`, `slotted_throughput_arrival`, `slotted_throughput_load` |
| 6 | `reservation` | `reservation_delay`, `reservation_throughput`, `reservation_capacity` |
| Accuracy | selected cases at three horizons | `accuracy_runlength` |

Default C controls: `--mode fixed`, `--stations 10`, `--rate .1`, `--backoff 10`,
`--time 200000`, `--warmup 20000`, `--seed 333333`, `--xr .1`, `--persistent -1`,
`--fixed-distribution uniform`, `--beb-cap 10`, `--guard .001`,
`--reservation-pipeline 0`, `--packets 0`. Every option takes a value. The full
runner supplies its own documented grids, horizons, and five-seed list.

Alternative controls are explicit: `--beb-cap 0` is uncapped; fixed distribution
can be `exponential`; pipeline `1` releases the station FIFO head at reservation
success. These are different model assumptions, not graphical style settings.
`--packets N` stops after N measured completions or the hard `--time` horizon,
whichever comes first; the printed actual elapsed time is used in rate denominators.

Packet conservation is exact across warmup and the measurement interval.
Reservation packet throughput, completed-work rate, attempted minislot load, and
exact data-server utilization are separate columns. Data capacity plots use
utilization at a dedicated overloaded arrival rate, rather than a peak of the
ordinary delay sweep. The data queue is bounded by N under the default model.

`test_simulator.py` runs 29 model/reproducibility checks. `validate_trends.py`
checks seven conceptual relationships on a full generated dataset. The standard
library integration tests under `tests/` cover native build paths and exports.
`results/provenance.json` records source/data hashes and the comparison document's
hash; it does not substitute the comparison report's measurements for our own.
