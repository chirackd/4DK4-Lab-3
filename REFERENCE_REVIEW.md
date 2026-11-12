# Reference reconciliation and model revision

The supplied `COE4DK4_Lab4_Report.docx` was treated as a secondary comparison
source. Its assertions were investigated, not adopted as a rubric or ground
truth. The original full simulator, raw data and lecture slides were not
provided, so no claim is made to have certified them. The reference document and
the other group's identifiers are not uploaded.

## What changed and why

- Use per-frame timers for all window configurations. The older GBN default
  restarted a single oldest timer when cumulative ACKs advanced, delaying loss
  recovery and producing approximately 0.265 efficiency at pd=0.1.
- On timeout of k, replay k plus unACKed followers >= k+Wr. This recovers go-back
  behavior at Wr=1 and selective recovery at Wr>=Ws. For intermediate Wr this
  is an explicit conservative replay policy, not a deduction that the receiver
  discarded every replayed packet. ACK loss can also cause a timeout.
- Handle one physical ACK atomically, including its cumulative and selective
  fields. Finish all events at a timestamp before choosing the next transmission;
  let a valid ACK win an exact timeout tie. This prevents a fresh transmission
  from taking a slot before a due retry is considered.
- Increase fixed send windows to64, backlogged measurement to1,000,000 ms and
  finite-transfer replications to100. Add high ACK-loss points and fractional
  timeout/boundary values.
- Retain three receiver capacities4,16,64 in the required plots. Match Wr=8 only
  in supplementary reference checks; differing curves are not mislabeled as
  exact copies of the reference's Wr=2/8 profiles.
- Replace the earlier GBN RTT-only reference line with the stated per-frame
  timeout recovery expression, under its assumptions.
- Generate PDF, editable DOCX and Markdown from one set of23 tables and17 plots.
  Raw CSV is now losslessly compressed as `results/runs.csv.gz`.

## Matched efficiency checks

Our replications use our original five seeds and portable generator. Reported
reference values are rounded and have their own uncertainty. Small discrepancies
are not fitted away. See `results/reference_comparison.csv` for full precision.

| Ws/Wr | pd/pa | T ms | Reported reference | Our mean ±95% CI |
| --- | --- | --- | --- | --- |
| 64/1 | 0.1/0 | 15 | 0.3750 | 0.37542 ± 0.00149 |
| 64/8 | 0.1/0 | 15 | 0.6080 | 0.60772 ± 0.00145 |
| 64/64 | 0.1/0 | 15 | 0.9000 | 0.89995 ± 0.00038 |
| 64/1 | 0.1/0.1 | 15 | 0.3760 | 0.37543 ± 0.00148 |
| 64/8 | 0.1/0.1 | 15 | 0.5970 | 0.59725 ± 0.00156 |
| 11/1 | 0.1/0 | 11 | 0.4505 | 0.45000 ± 0.00153 |
| 1/1 | 0.1/0.1 | 11.01 | 0.0736 | 0.07366 ± 0.00012 |
| 1/1 | 0.1/0.1 | 11.5 | 0.0730 | 0.07304 ± 0.00011 |
| 1/1 | 0.1/0.1 | 2 | 0.0872 | 0.08719 ± 0.00003 |

## Reference claims that need qualification

1. Timeout does not imply data was lost; the ACK can be lost. Therefore the
   argument that every follower beyond k+Wr "must" have been discarded is not
   generally valid. The replay cutoff is a sender policy.
2. The shortest non-spurious S&W timeout is11 ms under an ACK-first tie rule.
   It is not the unrestricted maximum-goodput optimum: the reference's own
   short-timeout table and our runs show more goodput at2 ms, paid for by many
   redundant attempts. Our report distinguishes both objectives.
3. Fractional timeouts are meaningful even with integer propagation. For T>=11,
   S&W's exact renewal efficiency changes continuously with T. The matched
   11.01/11.5 cases demonstrate this, contrary to an integer-only claim.
4. Independent Bernoulli experiments do not establish relative rankings under
   burst errors. No burst-channel conclusion is imported.
5. Original lecture slide numbering is not independently verified; the formulas
   actually used are derived and checked under their explicit assumptions.

## Independent verification and preserved differences

- 260 error-free throughput/finite-transfer analytical checks remain valid.
- Four S&W error scenarios agree with the renewal expression.
- 13 new analytical and exact-boundary checks cover error recovery and ACK ties.
- 144 finite cases agree with an independent heap-based Python simulator in
  completion time, attempts and unique deliveries.
- 16 heavy-error finite cases passed address/undefined-behavior sanitizers.
- A representative three-length convergence sweep uses five seeds at100,000,
  1,000,000 and3,000,000 measured ms.
- Current finite samples have100 independent transfers, not the reference's
  thousands per seed. Their own confidence intervals are reported without
  claiming the reference's precision.
- Legacy timer, individual-only recovery and cumulative-only ACK variants are
  available as documented diagnostics and measured in the comparison CSVs.
- The original simlib files, student-ID seed, native PowerShell layout and
  Lab4-only repository structure are preserved. The generator is still
  SplitMix64 rather than the reference's platform-dependent `rand()` stream.
