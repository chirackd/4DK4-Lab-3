# Model and graph alignment with the supplied report

Source inspected: `COE4DK4_Lab3_Report.docx`, uploaded by the user. The document's
paragraphs, tables, relevant code appendices, and 13 embedded graph images were
extracted and reviewed. It is a conceptual reference, not a source of our data or
instructions to run its shell scripts. Our results retain seed 400452897 and the
project's four comparison seeds. The source's authors, student numbers, figures,
and measured values are not copied into our submission.

| Topic | Previous default | Current baseline profile | Source location |
|---|---|---|---|
| Fixed retry distribution | Exponential | Uniform [0, 2B), as in the supplied original C | §1.1, §2.2 |
| BEB exponent | Uncapped | min(Nc, 10), no retry-count limit | §4.1–4.3 |
| Persistent station | Wait to an integer boundary | Retry immediately after failure | §5.2–5.3 |
| Slotted payload/guard | Shorten payload to 1−2ε in a unit slot | Keep payload 1; slot 1+2ε, ε=.001 | §6.1–6.3 |
| Slotted retry choice | Integer slot window | Continuous BEB wait followed by slot alignment | §6.2 |
| Reservation station FIFO | Dequeue after reservation; pipeline successors | Retain FIFO head until data completion; at most one outstanding packet/station | §7.2 |
| Reservation queue links | One link, safe only under early dequeue | Separate station FIFO and data FCFS links | Necessary to implement §7.2 safely |
| Capacity | Peak packet throughput selected from the delay sweep | Busy fraction of the data channel at fixed overload λ=2/X | §7.1–7.5 |
| Reservation coverage | N=10 and ratios ≥1 | N=5,10,20 and ratios .25–100 | §7.1 |
| Delay vs throughput | Include overloaded completed-packet means | Omit non-flow-balanced points | §1.1, Figures 3,6,10 |
| Uncertainty | Seed min–max | Student-t 95% intervals across seeds | §1.1, §8.1 |
| Capture explanation | Qualitative only | Also measure successive successes by the same station | §3.4, Figure 5 |
| Persistence comparison | Persistent vs other stations only | Also compare the all-BEB baseline and total throughput | Figures 7–9 |

## Deliberate differences retained

- The handout's literal BEB is uncapped. The comparison report explicitly chooses
  cap 10. The new baseline adopts that **documented modeling choice**, rather
  than pretending uncapped BEB was intrinsically an implementation bug.
  `--beb-cap 0` remains available for the literal handout model.
- `--fixed-distribution exponential` selects the previous alternate fixed model.
- `--reservation-pipeline 1` retains the alternate pipelined-reservation model.
  It is not used for baseline comparisons.
- The reference stops after 1 million successful packets (shorter for reservation)
  and discards no warmup. Our default remains a fixed 1 million time-unit horizon
  with 10% warmup, for bounded work across heavily overloaded configurations.
  `--packets` supports measured completion targets; `--time` remains a hard bound.
  For an individual reference-style run, for example:

  ```powershell
  .\build\simulator.exe --mode beb --stations 10 --rate .2 --seed 400452897 --beb-cap 10 --packets 1000000 --time 100000000 --warmup 0
  ```

  Different stopping rules, seeds, and Windows libc random streams can change
  numerical estimates, especially overload delays. Exact graph equality is not
  claimed or used as a test.
- Flow balance requires **every seed** to satisfy S ≥ .97λ and queue growth ≤
  .03λ. It is more conservative than checking only the pooled mean. Critical data
  load λ≥1 is excluded from equilibrium interpretations. Neither rule proves
  steady-state stability; unfinished packets remain explicitly counted.
- Reservation uses a tiny 10⁻⁹ time-unit numerical guard, distinct from the .001
  data-slot guard, to avoid ordering ties between end/start events. This does not
  materially change minislot duration or service capacity.
- Packet throughput and data-server utilization are separate CSV measures.
  Exponentially distributed data lengths allow finite-window packet rates above
  1; actual busy-time capacity is integrated and bounded by 1.

## Scientific checks, not curve fitting

`lab/validate_trends.py` reads newly simulated summaries and checks only broad
relationships: fixed-backoff congestion tradeoff, capped BEB carrying more traffic,
more same-station success bursts, persistent-station unfairness and system cost,
slotted delay improvement, and increasing reservation capacity with packet/minislot
ratio. No observations are overwritten or smoothed to make those checks pass.

The graph functions draw simulation markers with seed confidence intervals.
Continuous lines are analytical Poisson/M/M/1 references only. Saturated points
are hollow in arrival-rate plots and omitted from delay-throughput comparisons.
Additional plots (total persistent throughput and capture) now make the same
conceptual comparisons as the supplied report. The generated writeup takes its
numbers from the current CSVs, replacing the previous hardcoded narrative.
