# Computer Engineering 4DK4 — Lab 4

Simulation of ARQ Protocols

Revised November 12, 2026.


## Executive summary

The link becomes fully utilized without errors when the send window reaches 11 packets. With data errors, preserving correctly received packets behind a missing packet is the decisive advantage of Selective Repeat (SR). At Ws=64, pd=0.1, pa=0 and timeout 15 ms, measured efficiencies are 0.0790 for Stop-and-Wait (S&W), 0.3754 for Go-Back-N (GBN), and 0.9000 for SR with Wr=64. These are simulation results, not hardware measurements. [1, 2]

For a 100-packet file, no-error completion falls from 1100 ms with S&W to 110 ms at Ws≥11. With pd=pa=0.05 and Ws=64, the new mean acknowledged completion times are 1260.05 ms, 191.15 ms, and 121.52 ms for S&W, GBN, and full-buffer SR respectively.

Review against the supplied comparison report identified a timer-policy mismatch in our earlier GBN model and a less general recovery rule for intermediate receive windows. The revised implementation uses one per-frame timer engine and an explicitly stated replay rule. ACK fields are now processed atomically; all events at a timestamp are processed before another transmission starts. Matched comparisons reproduce the reference's main results without using its code or fitting the random seeds to its numbers. Some statements in that report are qualified or rejected where they exceed its own evidence. [5]

The new run length is ten times the earlier measurement interval, and finite transfers use 100 independent replications instead of 30. This report adds an independent Python simulation oracle, analytical and boundary checks, matched-model experiments, numerical tables with confidence intervals, and a record of retained differences. Results should be interpreted with the documented ACK and recovery policies, not as universal values for every implementation called GBN or SR.


## 1. Model, definitions and analytical expectations

The source sends fixed 1000-bit packets over one 1 Mbps data link. Serialization takes Tf=1 ms. Propagation takes 5 ms each way, and ACK serialization and processing are zero. Therefore the propagation round trip is 10 ms while the full transmission-start-to-ACK cycle is t0=11 ms. The default retransmission timeout T=15 ms is measured from transmission start. A failed data transmission generates no ACK. Each generated ACK is independently lost with probability pa; each data attempt is independently lost with probability pd. [1]

Backlogged efficiency is unique in-order delivered bits divided by link bitrate times the measurement interval. In these units, η = delivered packets / elapsed milliseconds. Attempts per delivery A is the number of data transmission starts divided by unique in-order deliveries in the same interval. It counts redundant copies. Finite-transfer completion ends when the sender has acknowledgement evidence for all N initially available packets, including final ACK recovery; it does not stop at the last receiver arrival. Warmup-crossing packets can cause a small count-boundary discrepancy in a long-run ratio.

Without errors, Ws packets can occupy the pipe during an 11 ms ACK cycle, giving η=min(Ws/11,1). Thus Ws=11 is the smallest full-utilization window and S&W efficiency is 1/11. The receive window has no effect when arrivals stay in order.

For S&W when T≥11 ms, let q=(1-pd)(1-pa). There are (1-q)/q failed attempts on average before one success. A failure costs T ms and a successful cycle costs 11 ms. Therefore E[time per delivered packet]=11+T(1-q)/q, η=q/[11q+T(1-q)], and A=1/q. This formula is not applied below 11 ms, where attempts overlap ACKs still in flight.

For a sufficiently large, continuously transmitting GBN window with per-frame timeout recovery and pa=0, the packet-error recovery comparison is η≈(1-pd)/[1+(T/Tf-1)pd]. At T=15 ms this is (1-pd)/(1+14pd). It represents one useful serialization time plus the error recovery penalty per delivered packet; at Ws=T/Tf=11 it gives (1-pd)/(1+10pd). Its assumptions exclude an ACK-restarted oldest-packet timer, small-window idle time, and premature timeouts. Agreement is a check of this specific regime, not a definition of correctness for all GBN implementations.

For SR with enough sender and receiver capacity, no premature timeouts and pa=0, only lost data need retry: η approaches 1-pd and A approaches 1/(1-pd). These are useful limits, not an assurance that any window which fills the error-free pipe also covers multiple losses and their recovery delays.

For finite no-error files, if Ws≥11, completion is N+10 ms. For Ws<11, the exact value is 11 floor((N-1)/Ws) + ((N-1) mod Ws) + 11 ms. Equivalently, N milliseconds of serialization plus a final 10 ms propagation term and a window-limited idle penalty. This formula includes the start and tail, unlike N/η used as a long-file approximation.

Table 1. Fixed parameters and measurement definitions.

| Quantity | Value / interpretation |
| --- | --- |
| Data packet / bitrate | 1000 bits / 1 Mbps |
| Serialization / one-way propagation | 1 ms / 5 ms |
| ACK cycle / default timer | 11 ms / 15 ms from transmission start |
| Data / ACK error model | Independent Bernoulli per attempt / generated ACK |
| Steady useful efficiency | Unique in-order deliveries × 1 ms / measured time |
| Finite completion | First transmission start to sender confirmation of all N |
| Identifier space | Absolute increasing integers; no modulo ambiguity |


## 2. Simulator architecture and recovery policy

src/arq.c implements the new ARQ model. vendor/simlib.c, simlib.h and trace.h remain the earlier labs' event-list and clock library, with their original license notices. Lab 2's serialized start/end transmission pattern and both labs' experiment-directory and PowerShell conventions are retained. ALOHA or queueing arrival logic is not reused because the present source and link differ. [3, 4]

One parameterized receiver buffers an accepted packet inside [recv, recv+Wr), then delivers the largest contiguous prefix. With Wr=1 it discards out-of-order packets, giving GBN reception. With Ws=Wr=1 only one packet can be outstanding, giving S&W. Sender state stores base, next new ID, ACK flags, retry flags, timer generations and busy state. Receiver state stores the next expected ID and buffered IDs. Assertions enforce 0≤next-base≤Ws. Arrays are sized for the configured horizon or finite file; this version does not claim a constant-memory ring buffer.

Every outstanding attempt has its own timer, started at transmission start. On timeout of k, queue k and every unacknowledged outstanding packet j≥k+Wr for replay. Invalidate timers for newly queued packets; restart each timer when its next attempt starts. A timer never directly transmits onto a busy link. Retries take priority over new packets and are selected in increasing ID order. ACKed retry entries are skipped. A transmission already in progress is allowed to finish.

This replay policy is deliberately explicit. When Wr=1, the oldest missing packet causes a go-back burst. When Wr≥Ws, no higher packet satisfies the cutoff, so recovery is selective. Intermediate Wr proactively replays distant followers. It is NOT logically guaranteed that they were discarded: k might have arrived and only its ACK was lost, or later attempts may have changed receiver state. This is a conservative sender policy, not access to hidden receiver knowledge. The alternative that retransmits only the timed-out packet remains available through ARQ_INDIVIDUAL=1 and is quantified in the design checks.

Each successful data reception generates one atomic ACK containing the highest contiguous received ID plus a selective ID if the answered packet remains buffered beyond that prefix. Outside-window arrivals return only the prefix; old duplicates are reacknowledged without another unique delivery. A single ACK-error draw governs the whole ACK. Sender processing applies both fields before sliding the window or starting a transmission. This removes the earlier implementation's split internal ACK events.

Events use absolute millisecond times. All events at a timestamp finish before a new transmission is chosen. A valid ACK at exactly its timeout timestamp wins; the timer handler defers to an ACK already scheduled at that time. There is no added epsilon delay in the default timer. This matters because exact integer delays can make premature new transmissions at a tied timestamp consume a serialization slot before an already-due retry. Simlib's underlying implementation remains unchanged.

Data errors are drawn on data-arrival processing; an unsuccessful transmission is discarded and no ACK is generated. The error outcome becomes known to the model at that event rather than at serialization end; because the sender receives no error feedback and the two channels have separate independent streams, this does not grant the sender additional information. SplitMix64 uses separate data and ACK states derived from the supplied seed. Reusing seeds across protocols matches replications, not every packet's loss outcome: changed retransmission histories consume draws differently.

ARQ_LEGACY=1 retains the old ACK-restarted oldest timer for Wr=1 (and the old individual retry approach for larger Wr) for policy comparisons. ARQ_CUMULATIVE_ONLY=1 removes selective ACK information. These environment switches are diagnostic alternatives, not silently mixed into production plots. No NAK, fast retransmit, finite sequence wrap, header overhead or adaptive timer is modeled. A nominal Wr>Ws is allowed but adds no useful buffer capacity; the largest outstanding span is bounded by Ws.

Table 2. Events and state transitions.

| Event | Scheduled at | Effect |
| --- | --- | --- |
| Transmission end | Start + 1 ms | Release serialization; next start waits for tied events |
| Data arrival | Start + 6 ms | Draw data loss; buffer/deliver or discard; generate ACK |
| ACK arrival | Successful receive + 5 ms | Draw already determined ACK outcome; apply both fields; advance base |
| Timeout | Attempt start + T | If current and unACKed, queue k and followers ≥k+Wr |

```text
on timeout(k), if unacknowledged and timer is current:
    queue k
    for j in outstanding with j >= k + Wr:
        if not acknowledged and not already queued:
            queue j; invalidate its old timer
when all events at this timestamp are finished:
    if link idle:
        send oldest unacknowledged queued packet
        else send a new packet if next < base + Ws
        start timer; schedule transmission end and data arrival
```


## 3. Experimental setup and statistical reliability

The main suite has 42,025 stored replication rows representing 33,695 unique simulations after reusing identical S&W references and configurations shared between experiments. Repeated references are not independent extra evidence. Per-run counts, parameters and metrics are inspectable in results/runs.csv.gz; summary.csv contains means and confidence intervals. Compression is lossless and pandas reads it directly. [2]

Every backlogged replication measures 1,000,000 ms after 10,000 ms warmup, ten times the earlier measurement duration. The five seeds are 400452897, 333333, 2026, 104729 and 8675309. The first is the student-ID seed documented in the existing Lab 3 report. Finite transfers use 100 seeds 400452897+104729k, k=0,...,99, with no warmup. The group's own seed is retained; no identifiers from the comparison report are adopted.

Means have pointwise two-sided 95% Student-t intervals, mean ± t·s/√r, with t=2.776445105 for five backlogged seeds and t=1.984216952 for 100 finite transfers. These intervals estimate the mean, not the distribution of individual file times. Tables round intervals for readability; a displayed 0.0000 is below that rounding precision, not proof of no variation. Full precision is retained in summary.csv. Intervals are not adjusted for multiple comparisons.

S&W always has Ws=Wr=1. GBN has Wr=1. Three SR receiver capacities are 4,16,64 packets. Experiments 3(a), 4 and 5 use Ws=64, so a large full-buffer SR profile is included. This also allows a matched comparison with the supplied report. We keep the original small/intermediate capacities rather than copying its 2/8 choices; supplementary checks explicitly use Wr=8 when matching that report.

Window grids emphasize the threshold at 11 and extend to 64. The timeout grid now includes 10.99, 11, 11.01 and 11.5 ms, so exact ties and fractional timeout effects are visible. ACK errors extend to 0.9 rather than ending at 0.5. Plot markers denote simulated means; error bars denote the stated intervals. Simulation points are not connected by piecewise-linear interpolation. Only labeled analytical functions are drawn as lines.

Table 3. Experiment-specific parameters.

| Part | Varied | Fixed beyond the physical defaults |
| --- | --- | --- |
| 1 | Protocols; pd=pa=0 or 0.5 | N=12; Ws=1 or 12; Wr=1 or 16; ID seed |
| 2 | Ws=1,2,4,6,8,10,11,12,16,24,32,48,64 | pd=pa=0; T=15; three SR capacities |
| 3(a) | pd=0,.01,.025,.05,.1,.2,.3,.4,.5 | pa=0; Ws=64; T=15 |
| 3(b) | Same Ws grid as Part 2 | pd=.1; pa=0; T=15 |
| 4 | pa=0,.01,.025,.05,.1,.2,.3,.4,.5,.7,.9 | pd=.1; Ws=64; T=15 |
| 5 | T=2,5,8,10,10.99,11,11.01,11.5,12,15,20,30,50,75,100 | pd=pa=.1; Ws=64 |
| 6 | Ws grid; three error cases | N=100; (pd,pa)=(0,0),(.05,0),(.05,.05) |
| 7 | Ws=1,4,8,11,16,32,64; three error cases | N=10 and 1000; otherwise Part 6 |


## 4. Experiment 1: verification by traces and independent models

All six traces in results/traces/ transfer N=12 packets: S&W, GBN Ws=12/Wr=1 and SR Ws=12/Wr=16, each with pd=pa=0 and 0.5, seed 400452897. They include time, event, packet ID, sender base, next new ID and receiver base. No-error traces contain no retransmissions. Packet 0 starts at 0, arrives at 6 and is ACKed at 11 ms; full-pipeline transmissions start one millisecond apart until the finite source is exhausted.

With data errors, the traces show a lost arrival without ACK generation. GBN discards subsequent out-of-order arrivals; SR buffers accepted followers and selectively acknowledges them. With ACK errors, successful receiver delivery is not undone. The sender retries if it lacks evidence, and duplicates are reACKed without increasing unique delivery. These behaviors are also checked against an independent implementation, rather than accepted only because one trace looks plausible.

The existing 260 analytical no-error comparisons remain: 52 throughput checks across send/receive windows plus 208 exact finite completion-time and transmission-count checks for N=1,10,100,1000. Four long-run S&W error scenarios are checked against the renewal formula. verify_reference.py adds 13 analytical and exact-boundary checks, including a 100-packet zero-error transfer with T=11 that must have exactly 100 attempts. test_oracle.py independently implements a heap event list, receiver and sender in Python and compares 144 small finite simulations against C. It checks completion time, total attempts and unique deliveries across six window configurations, data-only and ACK-only errors, heavy combined errors, and six timeout values from 2 to 50 ms.

The oracle shares the specified error generator to expose identical loss realizations, but does not reuse the C event scheduler, timer implementation or state transition code. It is a cross-implementation check, not a claim that identical random-number draws alone prove protocol correctness. Sanitizer results and main-suite conservation checks are recorded in results/validation.txt. [2]

Trace excerpt: SW_pd_pa_0.txt (full trace remains in the accompanying evidence).

```text
    0.000 TX new              id=0 sendbase=0 next=1 recvbase=0
    6.000 DATA accepted       id=0 sendbase=0 next=1 recvbase=0
   11.000 ACK cumulative      id=0 sendbase=0 next=1 recvbase=1
   11.000 TX new              id=1 sendbase=1 next=2 recvbase=1
   17.000 DATA accepted       id=1 sendbase=1 next=2 recvbase=1
   22.000 ACK cumulative      id=1 sendbase=1 next=2 recvbase=2
   22.000 TX new              id=2 sendbase=2 next=3 recvbase=2
   28.000 DATA accepted       id=2 sendbase=2 next=3 recvbase=2
   33.000 ACK cumulative      id=2 sendbase=2 next=3 recvbase=3
   33.000 TX new              id=3 sendbase=3 next=4 recvbase=3
```

Trace excerpt: GBN_pd_pa_0.txt (full trace remains in the accompanying evidence).

```text
    0.000 TX new              id=0 sendbase=0 next=1 recvbase=0
    1.000 TX new              id=1 sendbase=0 next=2 recvbase=0
    2.000 TX new              id=2 sendbase=0 next=3 recvbase=0
    3.000 TX new              id=3 sendbase=0 next=4 recvbase=0
    4.000 TX new              id=4 sendbase=0 next=5 recvbase=0
    5.000 TX new              id=5 sendbase=0 next=6 recvbase=0
    6.000 DATA accepted       id=0 sendbase=0 next=6 recvbase=0
    6.000 TX new              id=6 sendbase=0 next=7 recvbase=1
    7.000 DATA accepted       id=1 sendbase=0 next=7 recvbase=1
    7.000 TX new              id=7 sendbase=0 next=8 recvbase=2
```

Trace excerpt: SR_pd_pa_0.txt (full trace remains in the accompanying evidence).

```text
    0.000 TX new              id=0 sendbase=0 next=1 recvbase=0
    1.000 TX new              id=1 sendbase=0 next=2 recvbase=0
    2.000 TX new              id=2 sendbase=0 next=3 recvbase=0
    3.000 TX new              id=3 sendbase=0 next=4 recvbase=0
    4.000 TX new              id=4 sendbase=0 next=5 recvbase=0
    5.000 TX new              id=5 sendbase=0 next=6 recvbase=0
    6.000 DATA accepted       id=0 sendbase=0 next=6 recvbase=0
    6.000 TX new              id=6 sendbase=0 next=7 recvbase=1
    7.000 DATA accepted       id=1 sendbase=0 next=7 recvbase=1
    7.000 TX new              id=7 sendbase=0 next=8 recvbase=2
```

Trace excerpt: SW_pd_pa_0.5.txt (full trace remains in the accompanying evidence).

```text
    6.000 DATA lost           id=0 sendbase=0 next=1 recvbase=0
   15.000 TIMEOUT per-frame   id=0 sendbase=0 next=1 recvbase=0
   32.000 DATA lost           id=1 sendbase=1 next=2 recvbase=1
   41.000 TIMEOUT per-frame   id=1 sendbase=1 next=2 recvbase=1
   47.000 DATA lost           id=1 sendbase=1 next=2 recvbase=1
   56.000 TIMEOUT per-frame   id=1 sendbase=1 next=2 recvbase=1
   62.000 ACK lost            id=1 sendbase=1 next=2 recvbase=2
   71.000 TIMEOUT per-frame   id=1 sendbase=1 next=2 recvbase=2
   77.000 DATA lost           id=1 sendbase=1 next=2 recvbase=2
   86.000 TIMEOUT per-frame   id=1 sendbase=1 next=2 recvbase=2
   92.000 DATA duplicate      id=1 sendbase=1 next=2 recvbase=2
   92.000 ACK lost            id=1 sendbase=1 next=2 recvbase=2
```

Trace excerpt: GBN_pd_pa_0.5.txt (full trace remains in the accompanying evidence).

```text
    6.000 DATA lost           id=0 sendbase=0 next=6 recvbase=0
    8.000 DATA lost           id=2 sendbase=0 next=8 recvbase=0
    9.000 DATA lost           id=3 sendbase=0 next=9 recvbase=0
   10.000 ACK lost            id=4 sendbase=0 next=10 recvbase=0
   11.000 DATA lost           id=5 sendbase=0 next=11 recvbase=0
   12.000 ACK lost            id=6 sendbase=0 next=12 recvbase=0
   13.000 DATA lost           id=7 sendbase=0 next=12 recvbase=0
   14.000 DATA lost           id=8 sendbase=0 next=12 recvbase=0
   15.000 TIMEOUT per-frame   id=0 sendbase=0 next=12 recvbase=0
   15.000 DATA lost           id=9 sendbase=0 next=12 recvbase=0
   16.000 ACK lost            id=10 sendbase=0 next=12 recvbase=0
   17.000 DATA lost           id=11 sendbase=0 next=12 recvbase=0
```

Trace excerpt: SR_pd_pa_0.5.txt (full trace remains in the accompanying evidence).

```text
    6.000 DATA lost           id=0 sendbase=0 next=6 recvbase=0
    8.000 DATA lost           id=2 sendbase=0 next=8 recvbase=0
    9.000 DATA lost           id=3 sendbase=0 next=9 recvbase=0
   10.000 ACK lost            id=4 sendbase=0 next=10 recvbase=0
   11.000 DATA lost           id=5 sendbase=0 next=11 recvbase=0
   12.000 ACK lost            id=6 sendbase=0 next=12 recvbase=0
   12.000 ACK selective       id=1 sendbase=0 next=12 recvbase=0
   13.000 DATA lost           id=7 sendbase=0 next=12 recvbase=0
   14.000 DATA lost           id=8 sendbase=0 next=12 recvbase=0
   15.000 TIMEOUT per-frame   id=0 sendbase=0 next=12 recvbase=0
   15.000 DATA lost           id=9 sendbase=0 next=12 recvbase=0
   16.000 ACK lost            id=10 sendbase=0 next=12 recvbase=0
```


## 5. Experiment 2: error-free window-size dependence

All measured GBN and SR profiles follow min(Ws/11,1). Before Ws=11 the source exhausts its send window and idles while ACKs propagate. At Ws=11 the first ACK returns as the pipeline can accept another useful packet, and efficiency reaches one. Increasing Ws above 11 offers no gain without errors.

The receive window is irrelevant here because no missing packet creates a gap. GBN needs no buffer to reproduce SR's behavior when arrivals are ordered. The curves coincide; overlapping markers are exact agreement, not missing series. The numerical table retains S&W as its own horizontal reference and shows the send-window effect on the other profiles.

Table 4. Experiment 2: efficiency (mean ± pointwise 95% CI).

| ws | S&W | GBN | SR Wr=4 | SR Wr=16 | SR Wr=64 |
| --- | --- | --- | --- | --- | --- |
| 1 | 0.0909 ± 0.0000 | 0.0909 ± 0.0000 | 0.0909 ± 0.0000 | 0.0909 ± 0.0000 | 0.0909 ± 0.0000 |
| 2 | 0.0909 ± 0.0000 | 0.1818 ± 0.0000 | 0.1818 ± 0.0000 | 0.1818 ± 0.0000 | 0.1818 ± 0.0000 |
| 4 | 0.0909 ± 0.0000 | 0.3636 ± 0.0000 | 0.3636 ± 0.0000 | 0.3636 ± 0.0000 | 0.3636 ± 0.0000 |
| 6 | 0.0909 ± 0.0000 | 0.5455 ± 0.0000 | 0.5455 ± 0.0000 | 0.5455 ± 0.0000 | 0.5455 ± 0.0000 |
| 8 | 0.0909 ± 0.0000 | 0.7273 ± 0.0000 | 0.7273 ± 0.0000 | 0.7273 ± 0.0000 | 0.7273 ± 0.0000 |
| 10 | 0.0909 ± 0.0000 | 0.9091 ± 0.0000 | 0.9091 ± 0.0000 | 0.9091 ± 0.0000 | 0.9091 ± 0.0000 |
| 11 | 0.0909 ± 0.0000 | 1.0000 ± 0.0000 | 1.0000 ± 0.0000 | 1.0000 ± 0.0000 | 1.0000 ± 0.0000 |
| 12 | 0.0909 ± 0.0000 | 1.0000 ± 0.0000 | 1.0000 ± 0.0000 | 1.0000 ± 0.0000 | 1.0000 ± 0.0000 |
| 16 | 0.0909 ± 0.0000 | 1.0000 ± 0.0000 | 1.0000 ± 0.0000 | 1.0000 ± 0.0000 | 1.0000 ± 0.0000 |
| 24 | 0.0909 ± 0.0000 | 1.0000 ± 0.0000 | 1.0000 ± 0.0000 | 1.0000 ± 0.0000 | 1.0000 ± 0.0000 |
| 32 | 0.0909 ± 0.0000 | 1.0000 ± 0.0000 | 1.0000 ± 0.0000 | 1.0000 ± 0.0000 | 1.0000 ± 0.0000 |
| 48 | 0.0909 ± 0.0000 | 1.0000 ± 0.0000 | 1.0000 ± 0.0000 | 1.0000 ± 0.0000 | 1.0000 ± 0.0000 |
| 64 | 0.0909 ± 0.0000 | 1.0000 ± 0.0000 | 1.0000 ± 0.0000 | 1.0000 ± 0.0000 | 1.0000 ± 0.0000 |

![Figure 1. Experiment 2: efficiency. Source: current results/runs.csv.gz and summary.csv [2].](figures/exp2_efficiency.png)

Figure 1. Experiment 2: efficiency. Source: current results/runs.csv.gz and summary.csv [2].


## 6. Experiment 3(a): packet-error probability and theoretical limits

At Ws=64, pd=0.1 and pa=0, efficiencies are 0.3754 for GBN, 0.4768 for SR Wr=4, 0.8208 for SR Wr=16, and 0.9000 for full-buffer SR. S&W achieves 0.0790. All return to the no-error values at pd=0.

Full-buffer SR approaches 1-pd and the minimum attempts 1/(1-pd), because it retains followers behind a gap and selectively confirms them. The finite send window can still close after repeated losses, especially near pd=0.5. Therefore a shortfall below 1-pd is not automatically a simulator defect. Narrower receive windows discard or proactively replay more followers, placing their performance between GBN and full SR.

The revised GBN results agree closely with the per-frame recovery comparison (1-pd)/(1+14pd). Our previous ~0.2656 result at pd=0.1 came from a different ACK-restarted oldest timer, not from the same model producing a different random realization. The matched policy experiment in Section 11 separates that effect from send-window size. The old plot's round-trip-only recovery line has been replaced by the timeout-based expression under its explicit assumptions.

S&W matches q/[11q+15(1-q)], with q=1-pd. It has low absolute efficiency even at pd=0 because it cannot overlap packets. A moderate percentage loss in its already-small efficiency is not evidence that it outperforms a pipelined protocol.

Table 5. Experiment 3a: efficiency (mean ± pointwise 95% CI).

| pd | S&W | GBN | SR Wr=4 | SR Wr=16 | SR Wr=64 |
| --- | --- | --- | --- | --- | --- |
| 0 | 0.0909 ± 0.0000 | 1.0000 ± 0.0000 | 1.0000 ± 0.0000 | 1.0000 ± 0.0000 | 1.0000 ± 0.0000 |
| 0.01 | 0.0897 ± 0.0000 | 0.8685 ± 0.0014 | 0.8943 ± 0.0011 | 0.9887 ± 0.0002 | 0.9900 ± 0.0001 |
| 0.025 | 0.0878 ± 0.0000 | 0.7224 ± 0.0018 | 0.7752 ± 0.0014 | 0.9674 ± 0.0004 | 0.9750 ± 0.0001 |
| 0.05 | 0.0849 ± 0.0001 | 0.5594 ± 0.0021 | 0.6390 ± 0.0017 | 0.9236 ± 0.0005 | 0.9501 ± 0.0002 |
| 0.1 | 0.0790 ± 0.0001 | 0.3754 ± 0.0015 | 0.4768 ± 0.0015 | 0.8208 ± 0.0014 | 0.9000 ± 0.0004 |
| 0.2 | 0.0678 ± 0.0001 | 0.2103 ± 0.0007 | 0.3127 ± 0.0008 | 0.6296 ± 0.0005 | 0.7990 ± 0.0003 |
| 0.3 | 0.0573 ± 0.0002 | 0.1347 ± 0.0003 | 0.2235 ± 0.0005 | 0.4853 ± 0.0009 | 0.6971 ± 0.0005 |
| 0.4 | 0.0475 ± 0.0002 | 0.0909 ± 0.0004 | 0.1637 ± 0.0006 | 0.3739 ± 0.0005 | 0.5942 ± 0.0005 |
| 0.5 | 0.0384 ± 0.0002 | 0.0628 ± 0.0006 | 0.1203 ± 0.0005 | 0.2837 ± 0.0005 | 0.4910 ± 0.0002 |

![Figure 2. Experiment 3a: efficiency. Source: current results/runs.csv.gz and summary.csv [2].](figures/exp3a_efficiency.png)

Figure 2. Experiment 3a: efficiency. Source: current results/runs.csv.gz and summary.csv [2].


## 7. Experiment 3(b): window size, useful throughput and repeated work

At pd=0.1, SR Wr=64 efficiency rises from 0.5298 at Ws=11 to 0.8669 at Ws=32 and 0.9000 at Ws=64. Its attempts per delivery at Ws=64 are 1.111, near 1/0.9. Extra sender capacity covers the time while an early missing packet is retried and acknowledged; the error-free threshold alone is insufficient.

GBN efficiency at Ws=11 and 64 is 0.3749 and 0.3754 respectively. Its attempts per delivery rise from 2.223 to 2.664. Once the link remains busy during recovery, additional send-window space cannot recover the correctly received followers that its Wr=1 receiver has discarded.

For intermediate SR windows, sender concurrency and receiver storage are separate constraints. A wider send window initially overlaps useful traffic, but a narrow receive window still rejects distant followers after a gap. Our conservative replay rule also replays followers outside the presumed gap span; the independent-retry alternative in Section 11 demonstrates how that policy affects performance. Increasing Ws without considering Wr and timeout recovery is therefore not a universal improvement.

For a continuously busy forward link, the counts give η·A≈1. If there is idle time, the product is below one; A is not generally equal to 1/η. This distinction explains why a small sender window can have similar attempts per useful packet but lower throughput.

Table 6. Experiment 3b: efficiency (mean ± pointwise 95% CI).

| ws | S&W | GBN | SR Wr=4 | SR Wr=16 | SR Wr=64 |
| --- | --- | --- | --- | --- | --- |
| 1 | 0.0790 ± 0.0001 | 0.0790 ± 0.0001 | 0.0790 ± 0.0001 | 0.0790 ± 0.0001 | 0.0790 ± 0.0001 |
| 2 | 0.0790 ± 0.0001 | 0.1443 ± 0.0003 | 0.1460 ± 0.0004 | 0.1460 ± 0.0004 | 0.1460 ± 0.0004 |
| 4 | 0.0790 ± 0.0001 | 0.2409 ± 0.0006 | 0.2565 ± 0.0006 | 0.2565 ± 0.0006 | 0.2565 ± 0.0006 |
| 6 | 0.0790 ± 0.0001 | 0.3034 ± 0.0011 | 0.3380 ± 0.0008 | 0.3471 ± 0.0009 | 0.3471 ± 0.0009 |
| 8 | 0.0790 ± 0.0001 | 0.3426 ± 0.0011 | 0.3977 ± 0.0010 | 0.4258 ± 0.0011 | 0.4258 ± 0.0011 |
| 10 | 0.0790 ± 0.0001 | 0.3663 ± 0.0011 | 0.4382 ± 0.0008 | 0.4964 ± 0.0009 | 0.4964 ± 0.0009 |
| 11 | 0.0790 ± 0.0001 | 0.3749 ± 0.0015 | 0.4536 ± 0.0013 | 0.5298 ± 0.0011 | 0.5298 ± 0.0011 |
| 12 | 0.0790 ± 0.0001 | 0.3750 ± 0.0008 | 0.4629 ± 0.0010 | 0.5534 ± 0.0010 | 0.5534 ± 0.0010 |
| 16 | 0.0790 ± 0.0001 | 0.3754 ± 0.0015 | 0.4767 ± 0.0016 | 0.6467 ± 0.0012 | 0.6467 ± 0.0012 |
| 24 | 0.0790 ± 0.0001 | 0.3754 ± 0.0015 | 0.4768 ± 0.0015 | 0.8067 ± 0.0011 | 0.8140 ± 0.0009 |
| 32 | 0.0790 ± 0.0001 | 0.3754 ± 0.0015 | 0.4768 ± 0.0015 | 0.8208 ± 0.0014 | 0.8669 ± 0.0011 |
| 48 | 0.0790 ± 0.0001 | 0.3754 ± 0.0015 | 0.4768 ± 0.0015 | 0.8208 ± 0.0014 | 0.8984 ± 0.0004 |
| 64 | 0.0790 ± 0.0001 | 0.3754 ± 0.0015 | 0.4768 ± 0.0015 | 0.8208 ± 0.0014 | 0.9000 ± 0.0004 |

Table 7. Experiment 3b: attempts per delivery (mean ± pointwise 95% CI).

| ws | S&W | GBN | SR Wr=4 | SR Wr=16 | SR Wr=64 |
| --- | --- | --- | --- | --- | --- |
| 1 | 1.111 ± 0.001 | 1.111 ± 0.001 | 1.111 ± 0.001 | 1.111 ± 0.001 | 1.111 ± 0.001 |
| 2 | 1.111 ± 0.001 | 1.222 ± 0.003 | 1.111 ± 0.001 | 1.111 ± 0.001 | 1.111 ± 0.001 |
| 4 | 1.111 ± 0.001 | 1.445 ± 0.003 | 1.111 ± 0.001 | 1.111 ± 0.001 | 1.111 ± 0.001 |
| 6 | 1.111 ± 0.001 | 1.666 ± 0.006 | 1.286 ± 0.002 | 1.111 ± 0.001 | 1.111 ± 0.001 |
| 8 | 1.111 ± 0.001 | 1.889 ± 0.006 | 1.468 ± 0.003 | 1.111 ± 0.001 | 1.111 ± 0.001 |
| 10 | 1.111 ± 0.001 | 2.114 ± 0.006 | 1.644 ± 0.003 | 1.111 ± 0.001 | 1.111 ± 0.001 |
| 11 | 1.111 ± 0.001 | 2.223 ± 0.008 | 1.728 ± 0.004 | 1.111 ± 0.001 | 1.111 ± 0.001 |
| 12 | 1.111 ± 0.001 | 2.333 ± 0.005 | 1.813 ± 0.003 | 1.111 ± 0.001 | 1.111 ± 0.001 |
| 16 | 1.111 ± 0.001 | 2.664 ± 0.011 | 2.081 ± 0.007 | 1.111 ± 0.000 | 1.111 ± 0.000 |
| 24 | 1.111 ± 0.001 | 2.664 ± 0.011 | 2.097 ± 0.006 | 1.190 ± 0.001 | 1.111 ± 0.000 |
| 32 | 1.111 ± 0.001 | 2.664 ± 0.011 | 2.097 ± 0.006 | 1.218 ± 0.002 | 1.111 ± 0.000 |
| 48 | 1.111 ± 0.001 | 2.664 ± 0.011 | 2.097 ± 0.006 | 1.218 ± 0.002 | 1.111 ± 0.000 |
| 64 | 1.111 ± 0.001 | 2.664 ± 0.011 | 2.097 ± 0.006 | 1.218 ± 0.002 | 1.111 ± 0.000 |

![Figure 3. Experiment 3b: efficiency. Source: current results/runs.csv.gz and summary.csv [2].](figures/exp3b_efficiency.png)

Figure 3. Experiment 3b: efficiency. Source: current results/runs.csv.gz and summary.csv [2].

![Figure 4. Experiment 3b: attempts per delivery. Source: current results/runs.csv.gz and summary.csv [2].](figures/exp3b_attempts_per_delivery.png)

Figure 4. Experiment 3b: attempts per delivery. Source: current results/runs.csv.gz and summary.csv [2].


## 8. Experiment 4: data loss versus ACK loss

With pd=0.1 and pa increasing from 0 to 0.9, S&W efficiency falls from 0.0790 to 0.0061, while attempts per delivery increase from 1.111 to 11.204. Its q=(1-pd)(1-pa) controls the renewal result for T≥11: either loss can prevent confirmation of the single outstanding packet.

GBN falls from 0.3754 to 0.3333. A lost ACK is often covered by a later cumulative prefix; it does not remove a packet already delivered by the receiver. Moderate ACK loss is consequently much less harmful than a data gap. At very high pa, long runs of missing feedback finally close the window or cause unnecessary recovery.

SR Wr=64 falls from 0.9000 to 0.4477. A packet buffered behind an unfilled gap is not yet covered by the cumulative prefix, so loss of its selective ACK can require a redundant retry. Smaller receive windows have a different balance between retransmission and buffering costs. Apparent tiny improvements at some points should be read with their confidence intervals, not generalized into a benefit from ACK loss.

The comparison uses Ws=64 consistently with Part 3(a). Our window-size experiment and the matched Ws=32/64 diagnostics separately show why spare sender capacity matters: a larger window can keep producing later cumulative evidence after an ACK is lost. The supplied reference additionally compares Ws=11 and 64; those particular two-panel curves are not claimed to have been reproduced as a complete separate sweep here.

ACK-format assumptions matter. These results use a cumulative prefix plus a selective ID in one ACK. Pure cumulative SR loses information about buffered followers; pure individual-ACK schemes would recover lost feedback differently. Section 11 quantifies the cumulative-only variant rather than silently treating every ACK design as equivalent.

Table 8. Experiment 4: efficiency (mean ± pointwise 95% CI).

| pa | S&W | GBN | SR Wr=4 | SR Wr=16 | SR Wr=64 |
| --- | --- | --- | --- | --- | --- |
| 0 | 0.0790 ± 0.0001 | 0.3754 ± 0.0015 | 0.4768 ± 0.0015 | 0.8208 ± 0.0014 | 0.9000 ± 0.0004 |
| 0.01 | 0.0779 ± 0.0001 | 0.3754 ± 0.0015 | 0.4764 ± 0.0014 | 0.8179 ± 0.0014 | 0.8950 ± 0.0003 |
| 0.025 | 0.0764 ± 0.0001 | 0.3754 ± 0.0015 | 0.4758 ± 0.0014 | 0.8136 ± 0.0013 | 0.8877 ± 0.0003 |
| 0.05 | 0.0739 ± 0.0001 | 0.3754 ± 0.0015 | 0.4748 ± 0.0016 | 0.8066 ± 0.0013 | 0.8758 ± 0.0004 |
| 0.1 | 0.0689 ± 0.0002 | 0.3754 ± 0.0015 | 0.4728 ± 0.0017 | 0.7927 ± 0.0011 | 0.8531 ± 0.0006 |
| 0.2 | 0.0594 ± 0.0002 | 0.3755 ± 0.0014 | 0.4689 ± 0.0017 | 0.7658 ± 0.0012 | 0.8117 ± 0.0006 |
| 0.3 | 0.0505 ± 0.0002 | 0.3756 ± 0.0014 | 0.4647 ± 0.0020 | 0.7389 ± 0.0011 | 0.7736 ± 0.0007 |
| 0.4 | 0.0420 ± 0.0002 | 0.3759 ± 0.0015 | 0.4600 ± 0.0021 | 0.7111 ± 0.0013 | 0.7373 ± 0.0008 |
| 0.5 | 0.0341 ± 0.0002 | 0.3758 ± 0.0016 | 0.4543 ± 0.0022 | 0.6814 ± 0.0009 | 0.7010 ± 0.0006 |
| 0.7 | 0.0194 ± 0.0002 | 0.3707 ± 0.0009 | 0.4371 ± 0.0008 | 0.6060 ± 0.0009 | 0.6154 ± 0.0007 |
| 0.9 | 0.0061 ± 0.0001 | 0.3333 ± 0.0008 | 0.3748 ± 0.0004 | 0.4468 ± 0.0007 | 0.4477 ± 0.0007 |

Table 9. Experiment 4: attempts per delivery (mean ± pointwise 95% CI).

| pa | S&W | GBN | SR Wr=4 | SR Wr=16 | SR Wr=64 |
| --- | --- | --- | --- | --- | --- |
| 0 | 1.111 ± 0.001 | 2.664 ± 0.011 | 2.097 ± 0.006 | 1.218 ± 0.002 | 1.111 ± 0.000 |
| 0.01 | 1.122 ± 0.001 | 2.664 ± 0.011 | 2.099 ± 0.006 | 1.223 ± 0.002 | 1.117 ± 0.000 |
| 0.025 | 1.139 ± 0.001 | 2.664 ± 0.011 | 2.102 ± 0.006 | 1.229 ± 0.002 | 1.126 ± 0.000 |
| 0.05 | 1.169 ± 0.001 | 2.664 ± 0.011 | 2.106 ± 0.007 | 1.240 ± 0.002 | 1.142 ± 0.001 |
| 0.1 | 1.234 ± 0.002 | 2.664 ± 0.011 | 2.115 ± 0.008 | 1.261 ± 0.002 | 1.172 ± 0.001 |
| 0.2 | 1.389 ± 0.005 | 2.663 ± 0.010 | 2.133 ± 0.008 | 1.306 ± 0.002 | 1.232 ± 0.001 |
| 0.3 | 1.587 ± 0.006 | 2.662 ± 0.010 | 2.152 ± 0.009 | 1.353 ± 0.002 | 1.293 ± 0.001 |
| 0.4 | 1.855 ± 0.008 | 2.660 ± 0.011 | 2.174 ± 0.010 | 1.406 ± 0.002 | 1.356 ± 0.002 |
| 0.5 | 2.223 ± 0.011 | 2.661 ± 0.012 | 2.201 ± 0.011 | 1.467 ± 0.002 | 1.426 ± 0.001 |
| 0.7 | 3.709 ± 0.031 | 2.697 ± 0.006 | 2.288 ± 0.004 | 1.650 ± 0.002 | 1.625 ± 0.002 |
| 0.9 | 11.204 ± 0.189 | 3.000 ± 0.007 | 2.668 ± 0.003 | 2.238 ± 0.003 | 2.234 ± 0.003 |

![Figure 5. Experiment 4: efficiency. Source: current results/runs.csv.gz and summary.csv [2].](figures/exp4_efficiency.png)

Figure 5. Experiment 4: efficiency. Source: current results/runs.csv.gz and summary.csv [2].

![Figure 6. Experiment 4: attempts per delivery. Source: current results/runs.csv.gz and summary.csv [2].](figures/exp4_attempts_per_delivery.png)

Figure 6. Experiment 4: attempts per delivery. Source: current results/runs.csv.gz and summary.csv [2].


## 9. Experiment 5: timeout costs and the 11 ms boundary

The sweep spans 2 to 100 ms and resolves the boundary at 10.99,11,11.01 and 11.5 ms. For SR Wr=64, efficiency is 0.3213 with 3.112 attempts per delivery at T=5, versus 0.8487 with 1.178 at T=12. Timers below the full ACK cycle resend packets whose evidence is still in flight. Receiver buffering cannot turn those extra copies into new deliveries.

At T=100, SR Wr=64 efficiency is 0.4299 and its attempts per delivery are 1.179. Long timers can therefore waste elapsed time while requiring relatively few extra attempts. GBN loses more work because it discards followers after a data gap and must replay them; a large SR receive window protects that work until the sender window eventually fills.

S&W is an essential counterexample to an unqualified “best timeout equals RTT” conclusion. At T=2 it achieves 0.0872 with 6.234 attempts per delivery, while T=11 achieves 0.0737 with 1.234. Sending redundant copies into otherwise idle time can recover a failed packet or ACK sooner. This increases goodput at substantial transmission cost. T=11 is the shortest non-spurious timeout under our tie rule, not the unconstrained maximum-goodput optimum across every allowed timeout.

Fractional timeouts are meaningful. At T=11.01 and 11.5, measured S&W efficiencies are 0.0737 and 0.0730. The renewal expression varies continuously with T even when physical propagation and serialization delays are integers. The reference's claim that results depend only on which side of an integer the timeout lies is not generally true; its own S&W table also changes within that interval. The exact T=11 test confirms that ACKs win ties without an artificial added delay.

A timeout near the ACK cycle balances prompt recovery against spurious transmissions in the fixed-delay model. The best value depends on the metric, buffer sizes and loss process. We do not import a universal optimum or a claim of smooth integer-step behavior from the reference.

Table 10. Experiment 5: efficiency (mean ± pointwise 95% CI).

| tout | S&W | GBN | SR Wr=4 | SR Wr=16 | SR Wr=64 |
| --- | --- | --- | --- | --- | --- |
| 2 | 0.0872 ± 0.0000 | 0.1626 ± 0.0000 | 0.1631 ± 0.0000 | 0.1631 ± 0.0000 | 0.1631 ± 0.0000 |
| 5 | 0.0822 ± 0.0001 | 0.3052 ± 0.0003 | 0.3204 ± 0.0001 | 0.3213 ± 0.0001 | 0.3213 ± 0.0001 |
| 8 | 0.0777 ± 0.0001 | 0.3907 ± 0.0005 | 0.4430 ± 0.0003 | 0.4710 ± 0.0002 | 0.4710 ± 0.0002 |
| 10 | 0.0750 ± 0.0001 | 0.3696 ± 0.0010 | 0.4295 ± 0.0002 | 0.4726 ± 0.0001 | 0.4726 ± 0.0001 |
| 10.99 | 0.0687 ± 0.0001 | 0.3793 ± 0.0014 | 0.4733 ± 0.0009 | 0.7400 ± 0.0008 | 0.8244 ± 0.0003 |
| 11 | 0.0737 ± 0.0001 | 0.4152 ± 0.0010 | 0.5184 ± 0.0005 | 0.7971 ± 0.0004 | 0.8244 ± 0.0003 |
| 11.01 | 0.0737 ± 0.0001 | 0.4070 ± 0.0009 | 0.5090 ± 0.0006 | 0.8027 ± 0.0009 | 0.8487 ± 0.0005 |
| 11.5 | 0.0730 ± 0.0001 | 0.4070 ± 0.0009 | 0.5090 ± 0.0006 | 0.8027 ± 0.0009 | 0.8487 ± 0.0005 |
| 12 | 0.0724 ± 0.0001 | 0.4253 ± 0.0011 | 0.5318 ± 0.0010 | 0.8162 ± 0.0006 | 0.8487 ± 0.0005 |
| 15 | 0.0689 ± 0.0002 | 0.3754 ± 0.0015 | 0.4728 ± 0.0017 | 0.7927 ± 0.0011 | 0.8531 ± 0.0006 |
| 20 | 0.0638 ± 0.0002 | 0.3098 ± 0.0021 | 0.3912 ± 0.0016 | 0.6924 ± 0.0014 | 0.8514 ± 0.0007 |
| 30 | 0.0555 ± 0.0002 | 0.2310 ± 0.0023 | 0.2920 ± 0.0023 | 0.5195 ± 0.0015 | 0.8353 ± 0.0008 |
| 50 | 0.0442 ± 0.0002 | 0.1537 ± 0.0008 | 0.1940 ± 0.0009 | 0.3461 ± 0.0023 | 0.7057 ± 0.0030 |
| 75 | 0.0352 ± 0.0003 | 0.1073 ± 0.0007 | 0.1362 ± 0.0009 | 0.2433 ± 0.0011 | 0.5423 ± 0.0025 |
| 100 | 0.0292 ± 0.0004 | 0.0828 ± 0.0005 | 0.1050 ± 0.0008 | 0.1879 ± 0.0007 | 0.4299 ± 0.0026 |

Table 11. Experiment 5: attempts per delivery (mean ± pointwise 95% CI).

| tout | S&W | GBN | SR Wr=4 | SR Wr=16 | SR Wr=64 |
| --- | --- | --- | --- | --- | --- |
| 2 | 6.234 ± 0.002 | 6.151 ± 0.001 | 6.130 ± 0.001 | 6.130 ± 0.001 | 6.130 ± 0.001 |
| 5 | 3.234 ± 0.004 | 3.277 ± 0.003 | 3.121 ± 0.001 | 3.112 ± 0.001 | 3.112 ± 0.001 |
| 8 | 2.234 ± 0.002 | 2.559 ± 0.004 | 2.257 ± 0.001 | 2.123 ± 0.001 | 2.123 ± 0.001 |
| 10 | 2.234 ± 0.002 | 2.706 ± 0.007 | 2.328 ± 0.001 | 2.116 ± 0.000 | 2.116 ± 0.000 |
| 10.99 | 2.234 ± 0.003 | 2.637 ± 0.009 | 2.113 ± 0.004 | 1.351 ± 0.001 | 1.213 ± 0.001 |
| 11 | 1.234 ± 0.002 | 2.409 ± 0.006 | 1.929 ± 0.002 | 1.255 ± 0.001 | 1.213 ± 0.001 |
| 11.01 | 1.234 ± 0.002 | 2.457 ± 0.006 | 1.965 ± 0.002 | 1.246 ± 0.001 | 1.178 ± 0.001 |
| 11.5 | 1.234 ± 0.002 | 2.457 ± 0.006 | 1.965 ± 0.002 | 1.246 ± 0.001 | 1.178 ± 0.001 |
| 12 | 1.234 ± 0.002 | 2.351 ± 0.006 | 1.880 ± 0.004 | 1.225 ± 0.001 | 1.178 ± 0.001 |
| 15 | 1.234 ± 0.002 | 2.664 ± 0.011 | 2.115 ± 0.008 | 1.261 ± 0.002 | 1.172 ± 0.001 |
| 20 | 1.234 ± 0.003 | 3.228 ± 0.022 | 2.556 ± 0.011 | 1.444 ± 0.003 | 1.174 ± 0.001 |
| 30 | 1.234 ± 0.002 | 4.329 ± 0.043 | 3.424 ± 0.026 | 1.925 ± 0.006 | 1.176 ± 0.001 |
| 50 | 1.233 ± 0.002 | 6.508 ± 0.035 | 5.154 ± 0.025 | 2.889 ± 0.019 | 1.179 ± 0.001 |
| 75 | 1.232 ± 0.003 | 8.098 ± 0.050 | 6.364 ± 0.043 | 3.513 ± 0.013 | 1.179 ± 0.001 |
| 100 | 1.232 ± 0.004 | 8.092 ± 0.047 | 6.367 ± 0.048 | 3.514 ± 0.010 | 1.179 ± 0.001 |

![Figure 7. Experiment 5: efficiency. Source: current results/runs.csv.gz and summary.csv [2].](figures/exp5_efficiency.png)

Figure 7. Experiment 5: efficiency. Source: current results/runs.csv.gz and summary.csv [2].

![Figure 8. Experiment 5: attempts per delivery. Source: current results/runs.csv.gz and summary.csv [2].](figures/exp5_attempts_per_delivery.png)

Figure 8. Experiment 5: attempts per delivery. Source: current results/runs.csv.gz and summary.csv [2].


## 10. Experiments 6 and 7: finite files and transfer-size effects

For N=100 with no errors, all windowed profiles reach exactly 110 ms at Ws≥11; S&W takes 1100 ms. With pd=0.05 and no ACK errors at Ws=64, GBN takes 190.25 ms and SR Wr=64 takes 119.51 ms. With pd=pa=0.05 these become 191.15 and 121.52 ms. The corresponding S&W value is 1260.05 ms.

Intermediate receive windows reduce completion time by preserving some followers while a gap recovers. Larger send windows improve finite transfers until serialization, recovery time or the number of available packets becomes the limit. Unlike the error-free threshold, an error-recovery plateau depends on buffering and timeout policy. The file's final packet is special: loss of the final ACK cannot be repaired by an ACK from a later new file packet, so completion must include a tail retry when needed.

Experiment 7 repeats all three error cases for N=10 and 1000. The no-error lower bounds are 20 and 1010 ms, compared with S&W's 110 and 11000 ms. A ten-packet file cannot exploit a window larger than ten; the sweep first reaches full no-error concurrency at Ws=11 because ten is absent from that subset's grid. SR Wr=16 and Wr=64 have enough capacity for all followers of that small file and coincide.

At pd=pa=0.05, Ws=32, N=10, mean GBN and full-buffer SR times are 28.70 and 25.81 ms; for N=1000 they are 1793.90 and 1094.34 ms. Initial propagation and the last recovery dominate short files. Large files amortize fixed propagation and accumulate repeated recovery costs, making sustained throughput and receive buffering more consequential.

N/η gives a useful long-file scale but is not an exact completion-time formula. Mean completion is averaged directly over completed independent transfers; taking an inverse of an averaged finite-transfer efficiency would be a different statistic. Each curve uses 100 replications with pointwise intervals, not the reference's thousands of within-seed transfers; our uncertainty is stated rather than claiming its narrower intervals.

Table 12. Experiment 6_pd0_pa0: completion ms (mean ± pointwise 95% CI).

| ws | S&W | GBN | SR Wr=4 | SR Wr=16 | SR Wr=64 |
| --- | --- | --- | --- | --- | --- |
| 1 | 1100.00 ± 0.00 | 1100.00 ± 0.00 | 1100.00 ± 0.00 | 1100.00 ± 0.00 | 1100.00 ± 0.00 |
| 2 | 1100.00 ± 0.00 | 551.00 ± 0.00 | 551.00 ± 0.00 | 551.00 ± 0.00 | 551.00 ± 0.00 |
| 4 | 1100.00 ± 0.00 | 278.00 ± 0.00 | 278.00 ± 0.00 | 278.00 ± 0.00 | 278.00 ± 0.00 |
| 6 | 1100.00 ± 0.00 | 190.00 ± 0.00 | 190.00 ± 0.00 | 190.00 ± 0.00 | 190.00 ± 0.00 |
| 8 | 1100.00 ± 0.00 | 146.00 ± 0.00 | 146.00 ± 0.00 | 146.00 ± 0.00 | 146.00 ± 0.00 |
| 10 | 1100.00 ± 0.00 | 119.00 ± 0.00 | 119.00 ± 0.00 | 119.00 ± 0.00 | 119.00 ± 0.00 |
| 11 | 1100.00 ± 0.00 | 110.00 ± 0.00 | 110.00 ± 0.00 | 110.00 ± 0.00 | 110.00 ± 0.00 |
| 12 | 1100.00 ± 0.00 | 110.00 ± 0.00 | 110.00 ± 0.00 | 110.00 ± 0.00 | 110.00 ± 0.00 |
| 16 | 1100.00 ± 0.00 | 110.00 ± 0.00 | 110.00 ± 0.00 | 110.00 ± 0.00 | 110.00 ± 0.00 |
| 24 | 1100.00 ± 0.00 | 110.00 ± 0.00 | 110.00 ± 0.00 | 110.00 ± 0.00 | 110.00 ± 0.00 |
| 32 | 1100.00 ± 0.00 | 110.00 ± 0.00 | 110.00 ± 0.00 | 110.00 ± 0.00 | 110.00 ± 0.00 |
| 48 | 1100.00 ± 0.00 | 110.00 ± 0.00 | 110.00 ± 0.00 | 110.00 ± 0.00 | 110.00 ± 0.00 |
| 64 | 1100.00 ± 0.00 | 110.00 ± 0.00 | 110.00 ± 0.00 | 110.00 ± 0.00 | 110.00 ± 0.00 |

![Figure 9. Experiment 6_pd0_pa0: completion ms. Source: current results/runs.csv.gz and summary.csv [2].](figures/exp6_pd0_pa0_completion_ms.png)

Figure 9. Experiment 6_pd0_pa0: completion ms. Source: current results/runs.csv.gz and summary.csv [2].

Table 13. Experiment 6_pd0.05_pa0: completion ms (mean ± pointwise 95% CI).

| ws | S&W | GBN | SR Wr=4 | SR Wr=16 | SR Wr=64 |
| --- | --- | --- | --- | --- | --- |
| 1 | 1180.55 ± 6.70 | 1180.55 ± 6.70 | 1180.55 ± 6.70 | 1180.55 ± 6.70 | 1180.55 ± 6.70 |
| 2 | 1180.55 ± 6.70 | 622.49 ± 6.10 | 620.46 ± 5.99 | 620.46 ± 5.99 | 620.46 ± 5.99 |
| 4 | 1180.55 ± 6.70 | 348.00 ± 5.90 | 340.43 ± 4.89 | 340.43 ± 4.89 | 340.43 ± 4.89 |
| 6 | 1180.55 ± 6.70 | 260.35 ± 6.44 | 251.86 ± 5.11 | 248.74 ± 4.96 | 248.74 ± 4.96 |
| 8 | 1180.55 ± 6.70 | 218.57 ± 6.70 | 206.86 ± 5.01 | 201.68 ± 4.29 | 201.68 ± 4.29 |
| 10 | 1180.55 ± 6.70 | 196.66 ± 7.46 | 183.77 ± 5.51 | 173.41 ± 4.14 | 173.41 ± 4.14 |
| 11 | 1180.55 ± 6.70 | 189.35 ± 7.99 | 174.92 ± 5.82 | 162.83 ± 4.12 | 162.83 ± 4.12 |
| 12 | 1180.55 ± 6.70 | 189.95 ± 7.84 | 172.07 ± 5.53 | 158.38 ± 3.65 | 158.38 ± 3.65 |
| 16 | 1180.55 ± 6.70 | 190.25 ± 7.72 | 167.93 ± 5.41 | 143.83 ± 2.69 | 143.83 ± 2.69 |
| 24 | 1180.55 ± 6.70 | 190.25 ± 7.72 | 168.03 ± 5.30 | 124.29 ± 2.08 | 123.47 ± 1.86 |
| 32 | 1180.55 ± 6.70 | 190.25 ± 7.72 | 168.03 ± 5.30 | 122.81 ± 1.98 | 120.59 ± 1.35 |
| 48 | 1180.55 ± 6.70 | 190.25 ± 7.72 | 168.03 ± 5.30 | 122.81 ± 1.98 | 119.54 ± 1.17 |
| 64 | 1180.55 ± 6.70 | 190.25 ± 7.72 | 168.03 ± 5.30 | 122.81 ± 1.98 | 119.51 ± 1.17 |

![Figure 10. Experiment 6_pd0.05_pa0: completion ms. Source: current results/runs.csv.gz and summary.csv [2].](figures/exp6_pd0.05_pa0_completion_ms.png)

Figure 10. Experiment 6_pd0.05_pa0: completion ms. Source: current results/runs.csv.gz and summary.csv [2].

Table 14. Experiment 6_pd0.05_pa0.05: completion ms (mean ± pointwise 95% CI).

| ws | S&W | GBN | SR Wr=4 | SR Wr=16 | SR Wr=64 |
| --- | --- | --- | --- | --- | --- |
| 1 | 1260.05 ± 9.52 | 1260.05 ± 9.52 | 1260.05 ± 9.52 | 1260.05 ± 9.52 | 1260.05 ± 9.52 |
| 2 | 1260.05 ± 9.52 | 638.52 ± 6.03 | 641.07 ± 6.59 | 641.07 ± 6.59 | 641.07 ± 6.59 |
| 4 | 1260.05 ± 9.52 | 352.97 ± 5.89 | 350.00 ± 5.63 | 350.00 ± 5.63 | 350.00 ± 5.63 |
| 6 | 1260.05 ± 9.52 | 264.89 ± 6.27 | 255.24 ± 5.15 | 254.53 ± 5.10 | 254.53 ± 5.10 |
| 8 | 1260.05 ± 9.52 | 221.60 ± 6.56 | 209.41 ± 4.95 | 206.37 ± 4.63 | 206.37 ± 4.63 |
| 10 | 1260.05 ± 9.52 | 198.53 ± 7.36 | 185.47 ± 5.52 | 177.55 ± 4.39 | 177.55 ± 4.39 |
| 11 | 1260.05 ± 9.52 | 192.25 ± 7.92 | 177.01 ± 5.65 | 167.41 ± 4.55 | 167.41 ± 4.55 |
| 12 | 1260.05 ± 9.52 | 190.87 ± 7.89 | 173.62 ± 5.53 | 160.94 ± 4.21 | 160.94 ± 4.21 |
| 16 | 1260.05 ± 9.52 | 191.15 ± 7.85 | 168.25 ± 5.48 | 144.73 ± 3.02 | 144.73 ± 3.02 |
| 24 | 1260.05 ± 9.52 | 191.15 ± 7.85 | 168.34 ± 5.42 | 125.57 ± 2.39 | 124.94 ± 2.17 |
| 32 | 1260.05 ± 9.52 | 191.15 ± 7.85 | 168.34 ± 5.42 | 124.02 ± 2.06 | 122.25 ± 1.67 |
| 48 | 1260.05 ± 9.52 | 191.15 ± 7.85 | 168.34 ± 5.42 | 124.02 ± 2.06 | 121.53 ± 1.54 |
| 64 | 1260.05 ± 9.52 | 191.15 ± 7.85 | 168.34 ± 5.42 | 124.02 ± 2.06 | 121.52 ± 1.54 |

![Figure 11. Experiment 6_pd0.05_pa0.05: completion ms. Source: current results/runs.csv.gz and summary.csv [2].](figures/exp6_pd0.05_pa0.05_completion_ms.png)

Figure 11. Experiment 6_pd0.05_pa0.05: completion ms. Source: current results/runs.csv.gz and summary.csv [2].

Table 15. Experiment 7_N10_pd0_pa0: completion ms (mean ± pointwise 95% CI).

| ws | S&W | GBN | SR Wr=4 | SR Wr=16 | SR Wr=64 |
| --- | --- | --- | --- | --- | --- |
| 1 | 110.00 ± 0.00 | 110.00 ± 0.00 | 110.00 ± 0.00 | 110.00 ± 0.00 | 110.00 ± 0.00 |
| 11 | 110.00 ± 0.00 | 20.00 ± 0.00 | 20.00 ± 0.00 | 20.00 ± 0.00 | 20.00 ± 0.00 |
| 32 | 110.00 ± 0.00 | 20.00 ± 0.00 | 20.00 ± 0.00 | 20.00 ± 0.00 | 20.00 ± 0.00 |
| 64 | 110.00 ± 0.00 | 20.00 ± 0.00 | 20.00 ± 0.00 | 20.00 ± 0.00 | 20.00 ± 0.00 |

![Figure 12. Experiment 7_N10_pd0_pa0: completion ms. Source: current results/runs.csv.gz and summary.csv [2].](figures/exp7_N10_pd0_pa0_completion_ms.png)

Figure 12. Experiment 7_N10_pd0_pa0: completion ms. Source: current results/runs.csv.gz and summary.csv [2].

Table 16. Experiment 7_N10_pd0.05_pa0: completion ms (mean ± pointwise 95% CI).

| ws | S&W | GBN | SR Wr=4 | SR Wr=16 | SR Wr=64 |
| --- | --- | --- | --- | --- | --- |
| 1 | 118.40 ± 2.00 | 118.40 ± 2.00 | 118.40 ± 2.00 | 118.40 ± 2.00 | 118.40 ± 2.00 |
| 11 | 118.40 ± 2.00 | 28.10 ± 2.09 | 26.39 ± 1.48 | 25.02 ± 1.16 | 25.02 ± 1.16 |
| 32 | 118.40 ± 2.00 | 28.10 ± 2.09 | 26.39 ± 1.48 | 25.02 ± 1.16 | 25.02 ± 1.16 |
| 64 | 118.40 ± 2.00 | 28.10 ± 2.09 | 26.39 ± 1.48 | 25.02 ± 1.16 | 25.02 ± 1.16 |

![Figure 13. Experiment 7_N10_pd0.05_pa0: completion ms. Source: current results/runs.csv.gz and summary.csv [2].](figures/exp7_N10_pd0.05_pa0_completion_ms.png)

Figure 13. Experiment 7_N10_pd0.05_pa0: completion ms. Source: current results/runs.csv.gz and summary.csv [2].

Table 17. Experiment 7_N10_pd0.05_pa0.05: completion ms (mean ± pointwise 95% CI).

| ws | S&W | GBN | SR Wr=4 | SR Wr=16 | SR Wr=64 |
| --- | --- | --- | --- | --- | --- |
| 1 | 127.25 ± 2.94 | 127.25 ± 2.94 | 127.25 ± 2.94 | 127.25 ± 2.94 | 127.25 ± 2.94 |
| 11 | 127.25 ± 2.94 | 28.70 ± 2.12 | 27.01 ± 1.55 | 25.81 ± 1.32 | 25.81 ± 1.32 |
| 32 | 127.25 ± 2.94 | 28.70 ± 2.12 | 27.01 ± 1.55 | 25.81 ± 1.32 | 25.81 ± 1.32 |
| 64 | 127.25 ± 2.94 | 28.70 ± 2.12 | 27.01 ± 1.55 | 25.81 ± 1.32 | 25.81 ± 1.32 |

![Figure 14. Experiment 7_N10_pd0.05_pa0.05: completion ms. Source: current results/runs.csv.gz and summary.csv [2].](figures/exp7_N10_pd0.05_pa0.05_completion_ms.png)

Figure 14. Experiment 7_N10_pd0.05_pa0.05: completion ms. Source: current results/runs.csv.gz and summary.csv [2].

Table 18. Experiment 7_N1000_pd0_pa0: completion ms (mean ± pointwise 95% CI).

| ws | S&W | GBN | SR Wr=4 | SR Wr=16 | SR Wr=64 |
| --- | --- | --- | --- | --- | --- |
| 1 | 11000.00 ± 0.00 | 11000.00 ± 0.00 | 11000.00 ± 0.00 | 11000.00 ± 0.00 | 11000.00 ± 0.00 |
| 11 | 11000.00 ± 0.00 | 1010.00 ± 0.00 | 1010.00 ± 0.00 | 1010.00 ± 0.00 | 1010.00 ± 0.00 |
| 32 | 11000.00 ± 0.00 | 1010.00 ± 0.00 | 1010.00 ± 0.00 | 1010.00 ± 0.00 | 1010.00 ± 0.00 |
| 64 | 11000.00 ± 0.00 | 1010.00 ± 0.00 | 1010.00 ± 0.00 | 1010.00 ± 0.00 | 1010.00 ± 0.00 |

![Figure 15. Experiment 7_N1000_pd0_pa0: completion ms. Source: current results/runs.csv.gz and summary.csv [2].](figures/exp7_N1000_pd0_pa0_completion_ms.png)

Figure 15. Experiment 7_N1000_pd0_pa0: completion ms. Source: current results/runs.csv.gz and summary.csv [2].

Table 19. Experiment 7_N1000_pd0.05_pa0: completion ms (mean ± pointwise 95% CI).

| ws | S&W | GBN | SR Wr=4 | SR Wr=16 | SR Wr=64 |
| --- | --- | --- | --- | --- | --- |
| 1 | 11787.80 ± 23.15 | 11787.80 ± 23.15 | 11787.80 ± 23.15 | 11787.80 ± 23.15 | 11787.80 ± 23.15 |
| 11 | 11787.80 ± 23.15 | 1793.15 ± 24.71 | 1661.72 ± 17.58 | 1545.37 ± 13.05 | 1545.37 ± 13.05 |
| 32 | 11787.80 ± 23.15 | 1792.70 ± 23.30 | 1571.67 ± 16.47 | 1094.01 ± 4.38 | 1079.10 ± 2.88 |
| 64 | 11787.80 ± 23.15 | 1792.70 ± 23.30 | 1571.67 ± 16.47 | 1094.01 ± 4.38 | 1066.89 ± 1.84 |

![Figure 16. Experiment 7_N1000_pd0.05_pa0: completion ms. Source: current results/runs.csv.gz and summary.csv [2].](figures/exp7_N1000_pd0.05_pa0_completion_ms.png)

Figure 16. Experiment 7_N1000_pd0.05_pa0: completion ms. Source: current results/runs.csv.gz and summary.csv [2].

Table 20. Experiment 7_N1000_pd0.05_pa0.05: completion ms (mean ± pointwise 95% CI).

| ws | S&W | GBN | SR Wr=4 | SR Wr=16 | SR Wr=64 |
| --- | --- | --- | --- | --- | --- |
| 1 | 12608.30 ± 30.22 | 12608.30 ± 30.22 | 12608.30 ± 30.22 | 12608.30 ± 30.22 | 12608.30 ± 30.22 |
| 11 | 12608.30 ± 30.22 | 1817.74 ± 24.36 | 1680.74 ± 17.06 | 1581.28 ± 13.43 | 1581.28 ± 13.43 |
| 32 | 12608.30 ± 30.22 | 1793.90 ± 23.35 | 1579.34 ± 16.70 | 1109.46 ± 4.80 | 1094.34 ± 3.25 |
| 64 | 12608.30 ± 30.22 | 1793.90 ± 23.35 | 1579.34 ± 16.70 | 1109.46 ± 4.80 | 1085.16 ± 2.40 |

![Figure 17. Experiment 7_N1000_pd0.05_pa0.05: completion ms. Source: current results/runs.csv.gz and summary.csv [2].](figures/exp7_N1000_pd0.05_pa0.05_completion_ms.png)

Figure 17. Experiment 7_N1000_pd0.05_pa0.05: completion ms. Source: current results/runs.csv.gz and summary.csv [2].


## 11. Reconciliation with the supplied comparison report

COE4DK4_Lab 4_Report.docx is used as a secondary comparison source, not a rubric, a verified implementation or a replacement for the handout. We inspected its model descriptions, included code snippets, numerical tables, and timeout discussion. The complete reference implementation and raw data were not supplied, so its internal test counts and confidence intervals cannot be independently certified. We compare only explicitly reported configurations and rounded results. Different seeds and generators mean that exact decimal identity is neither required nor expected. [5]

The main adopted change is a unified per-frame timeout/replay rule that recovers standard S&W, GBN-like go-back behavior and full SR through window parameters. We also adopted more diagnostic boundary points, a larger fixed sender window, larger finite samples and longer measurement intervals. These are justified by independent tests and analytically predictable regimes, rather than selected to make every reported number match.

The table below contains matched cases using our five seeds and generator. Differences are measured minus the reference's rounded efficiency. Where the difference is smaller than our interval or the reference's reported precision, it is consistent with their model agreeing within simulation uncertainty; it is not proof that every untested configuration is identical.

Table 21. Matched checks against reported reference values; our intervals are separate from reference uncertainty.

| Ws/Wr | pd/pa | T ms | Reference η | Our η ± CI | Difference |
| --- | --- | --- | --- | --- | --- |
| 64/1 | 0.1/0 | 15 | 0.3750 | 0.37542 ± 0.00149 | +0.00042 |
| 64/8 | 0.1/0 | 15 | 0.6080 | 0.60772 ± 0.00145 | -0.00028 |
| 64/64 | 0.1/0 | 15 | 0.9000 | 0.89995 ± 0.00038 | -0.00005 |
| 64/1 | 0.1/0.1 | 15 | 0.3760 | 0.37543 ± 0.00148 | -0.00057 |
| 64/8 | 0.1/0.1 | 15 | 0.5970 | 0.59725 ± 0.00156 | +0.00025 |
| 11/1 | 0.1/0 | 11 | 0.4505 | 0.45000 ± 0.00153 | -0.00050 |
| 1/1 | 0.1/0.1 | 11.01 | 0.0736 | 0.07366 ± 0.00012 | +0.00006 |
| 1/1 | 0.1/0.1 | 11.5 | 0.0730 | 0.07304 ± 0.00011 | +0.00004 |
| 1/1 | 0.1/0.1 | 2 | 0.0872 | 0.08719 ± 0.00003 | -0.00001 |

At Ws=64, pd=0.1 and pa=0, the revised GBN efficiency is 0.37542, versus 0.26456 with the legacy ACK-restarted oldest-timer policy. This is a direct matched comparison; the earlier branch's ~0.2656 outcome was a model-policy difference, not evidence that the reference's ~0.375 was wrong. The per-frame policy also matches the recovery formula near 0.375 at T=15 and 0.45 at T=11/Ws=11.

With SR Ws=Wr=64 and pd=0.1, removing selective ACK information reduces efficiency from 0.89995 to 0.59461. This independently reproduces the reference's qualitative ACK-format check: buffered followers need selective evidence if they are not yet covered by the prefix. At Wr=8 with pd=pa=0.1, conservative replay gives 0.59725, versus 0.50181 for individual-only retries. Thus recovery policy for intermediate Wr is a consequential design choice, not just a cosmetic implementation difference.

The revised SR Ws=32/Wr=64 packet-error result is 0.86694, versus 0.89995 at Ws=64. This isolates sender capacity from the receiver's nominal 64-packet capacity. The old report's larger shortfall from 1-pd at Ws=32 was partly a window effect, so a stronger matched comparison required using Ws=64.

Table 22. Policy diagnostics at pd=0.1, T=15 ms (our measured η).

| Configuration | Default | Alternative | Interpretation |
| --- | --- | --- | --- |
| GBN Ws=64, pa=0 | 0.37542 | 0.26456 | Legacy ACK-restarted oldest timer |
| GBN Ws=64, pa=.1 | 0.37543 | 0.21801 | Individual retries without go-back |
| SR Ws=Wr=64, pa=0 | 0.89995 | 0.59461 | Cumulative-only ACK |
| SR Ws=64 Wr=8, pa=.1 | 0.59725 | 0.50181 | Individual-only retries |

Claims not adopted uncritically:

A timeout does not prove a data packet is missing at the receiver: its ACK may have been lost. Therefore the reference's inference that every follower ≥k+Wr “must have been discarded” is too strong. The replay cutoff is retained as an explicit conservative policy, with alternative measurements, not as a theorem.

The reference concludes that the best S&W timeout is 11.01 ms, while its own table and discussion show higher unconstrained goodput at 1–2 ms using many more copies. We distinguish shortest non-spurious timeout from maximum goodput and from transmission efficiency.

The reference's statement that results depend only on the side of integer timeout boundaries is contradicted by the continuous S&W renewal expression and its own 11.01/11.5 ms values. Our fractional sweep checks the distinction directly.

A broad statement about whether burst errors help one protocol relative to others is not established by an independent-Bernoulli experiment. No burst channel is simulated here, so no ranking under burst errors is asserted.

The reference's claims of specific lecture slide numbers are secondary citations: the original slides were not supplied. We independently derive and test the formulas used here without claiming to have verified unseen slides. Different receive capacities, sampling designs and seed lists are identified rather than hidden in comparisons.


## 12. Reliability, reproducibility and limitations

Table 23. Representative run-length checks; all use five seeds and 10000 ms warmup.

| Ws/Wr | pd/pa | T | Measured ms | η ± 95% CI |
| --- | --- | --- | --- | --- |
| 1/1 | 0.5/0.5 | 15 | 100,000 | 0.017882 ± 0.000285 |
| 1/1 | 0.5/0.5 | 15 | 1,000,000 | 0.017775 ± 0.000104 |
| 1/1 | 0.5/0.5 | 15 | 3,000,000 | 0.017834 ± 0.000066 |
| 64/1 | 0.1/0 | 15 | 100,000 | 0.376676 ± 0.002803 |
| 64/1 | 0.1/0 | 15 | 1,000,000 | 0.375421 ± 0.001487 |
| 64/1 | 0.1/0 | 15 | 3,000,000 | 0.375122 ± 0.001148 |
| 64/16 | 0.1/0.1 | 15 | 100,000 | 0.793074 ± 0.001867 |
| 64/16 | 0.1/0.1 | 15 | 1,000,000 | 0.792720 ± 0.001125 |
| 64/16 | 0.1/0.1 | 15 | 3,000,000 | 0.792819 ± 0.000635 |
| 64/64 | 0.1/0.1 | 100 | 100,000 | 0.428980 ± 0.007959 |
| 64/64 | 0.1/0.1 | 100 | 1,000,000 | 0.429891 ± 0.002600 |
| 64/64 | 0.1/0.1 | 100 | 3,000,000 | 0.429809 ± 0.000748 |

The reliability sweep compares 100000,1000000 and 3000000 measured ms at four representative configurations, including heavy-error S&W and long-timeout SR. The table exposes variation instead of asserting that one chosen horizon proves convergence everywhere. Compare interval widths with the operating differences discussed above; nearby points can remain unresolved even when broad protocol gaps are clear.

The error generator is portable and separate for data and ACKs, but deterministic PRNG streams are a modeling approximation. Errors are independent, with no burst correlation. The model omits variable processing, queuing of ACKs, congestion, finite sequence-space wrap and adaptive timers. Memory grows with configured horizon/file size. Measurements are specific to the stated replay, ACK and event-tie policies. Results at extremely high errors or tails not represented by the finite sample should not be extrapolated as guarantees.

Reproduce on native Windows with setup.ps1 then run_all.ps1, or use Python with GCC on Linux/macOS. The workflow compiles, validates no-error and S&W cases, runs all seven experiments, generates lossless-compressed raw evidence and plots, checks reliability and reference scenarios, runs the independent Python oracle, and rebuilds the PDF, DOCX and Markdown. GCC and Python must be on PATH. Native PowerShell scripts are supplied; this execution was tested on Linux, not Windows. Diagnostic flags must be unset for the main suite. The report's values are loaded from the current run, not transcribed from the comparison document.

The complete ZIP contains this Lab 4 package only. Prior Lab 3 experiments are not reintroduced. Evidence includes results/analytical_checks.csv, oracle_checks.csv, reference_comparison.csv, model_comparisons.csv, model_comparison_summary.csv, reliability.csv, validation.txt, the complete per-run main suite and six traces.


## 13. Conclusions

Without errors, the 11-packet send window follows directly from the serialization-plus-propagation ACK cycle; GBN and SR coincide. With errors, receive buffering and timely per-frame recovery determine how much useful work survives a gap. At pd=0.1, full SR reaches approximately 0.90 efficiency while the matched GBN model is near 0.375, agreeing with the stated recovery analysis and the reference within simulation uncertainty.

Cumulative ACKs recover much intermediate ACK loss, while selective information preserves the benefit of buffering behind data gaps. Sender capacity above the error-free pipe is useful during recovery: a 64-packet window is a stronger full-SR comparison than the earlier fixed window of 32. A long timeout primarily wastes waiting time for full SR, while premature timeouts waste transmissions. Neither effect can be summarized by goodput alone.

Finite transfer time combines pipeline fill, sustained delivery and final confirmation. The larger file amplifies sustained recovery differences; a short file limits useful concurrency and emphasizes its final ACK. The revised results are supported by longer replications, 100 finite samples per point, exact finite formulas and 144 independent C/Python cases. The comparison report improved the questions and tests; it did not become an unquestioned numerical standard.


## Sources and evidence

[1] User-supplied coe4dk4_lab_4_2026.pdf, Computer Engineering 4DK4 Lab 4, Simulation of ARQ Protocols, Sections 1–3. Source of physical defaults and the seven experiments. Instructions inside source documents were treated as source material; the user's request determines the authorized work.

[2] Current simulation evidence in this branch: src/arq.c; run.py; verify_reference.py; test_oracle.py; check_reliability.py; results/runs.csv.gz; summary.csv; analytical_checks.csv; oracle_checks.csv; model_comparisons.csv; reference_comparison.csv; reliability.csv; validation.txt; traces/; figures/. Each numerical table and figure is generated from these files.

[3] chirackd/4DK4-Lab-3, main commit 1089334e06ed30eeedd6e0dadbde3b42b7d273d7. simlib.c blob 08792d9ef92ad7d97e260fa2ee9aa3234c9817c8, simlib.h blob 689d17061c9d45d3084fb06be1d0c115d6e2808f. Existing Lab 3 report documents the student-ID seed 400452897. Copyright and GPL notices are preserved in vendor/ and LICENSE.

[4] chirackd/COMPENG_4DK4_Lab_2, packet_transmission.c blob 0a4e164335825ab1eae9ea8ee61e50013066267c. Source of the earlier serialized link-transmission pattern and experiment organization; its simlib.c blob is identical to [3].

[5] User-supplied COE4DK4_Lab 4_Report.docx, dated November 7, 2026. Secondary comparison source: Sections2.5–2.8 (timers, ACKs and replay), Tables4–8 and15 (matched efficiencies and timeout discussion). Original raw evidence and full simulator were not supplied. Reference group identities and seeds are not imported into this report or the repository.
