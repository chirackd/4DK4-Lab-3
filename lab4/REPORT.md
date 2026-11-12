# Computer Engineering 4DK4 — Lab 4

Simulation of ARQ Protocols

Prepared November 12, 2026.


## Executive Summary

This discrete-event simulation implements Stop-and-Wait (S&W), Go-Back-N (GBN), and Selective-Repeat (SR) on the lab's 1 Mbps link. All numerical results are generated simulation measurements, not physical-link observations. [1, 2]

The error-free bandwidth-delay threshold is Ws=11 packets: S&W efficiency is 1/11 = 0.09091, and both GBN and SR reach full utilization at Ws=11. With pd=0.1, pa=0, Ws=32, efficiency is 0.2656 for GBN, 0.8571 for SR with Wr=64, and 0.0792 for S&W. A large receive window preserves packets following a loss and avoids most unnecessary retransmissions.

For N=100, Ws=32 and pd=pa=0.05, mean completion times are 233.63 ms for GBN, 121.87 ms for SR Wr=64, and 1258.00 ms for S&W. These are means of completion times, not inverses of mean throughputs.

A timeout near the 11 ms acknowledgement-return time avoids premature retransmissions while recovering losses promptly. However, a shorter timeout can increase S&W goodput by sending redundant copies sooner. The measured timeout tradeoff therefore depends on both efficiency and transmission attempts; it is not a universal claim that shorter timeouts always reduce goodput.


## 1. Simulation design and reuse of earlier labs

The new ARQ logic is in src/arq.c. The event list, simulation clock, scheduling API, and allocation/cleanup functions are the unchanged simlib.c and simlib.h retrieved from chirackd/4DK4-Lab-3, commit 1089334e06ed30eeedd6e0dadbde3b42b7d273d7. Lab 2's simlib has the same blob SHA, 08792d9ef92ad7d97e260fa2ee9aa3234c9817c8. Lab 2's packet_transmission.c provided the start-transmission/end-transmission pattern: occupy one server, schedule its release, and immediately consider the next packet. The experiment folders and native PowerShell entry points follow Labs 2 and 3. The ALOHA and queueing traffic models are replaced because this lab requires a single-link ARQ model. [3, 4]

A single parameterized engine uses Ws and Wr. Wr=1 selects the discard-out-of-order receiver and GBN's single oldest-outstanding timer with go-back retransmission. Ws=Wr=1 consequently produces S&W. Wr>1 selects bounded receive buffering and individual packet timers. This timer-policy choice is explicit: changing Wr to 1 switches both the receiver and the retransmission policy. It is not an SR receiver with conventional GBN labels pasted onto its results.

Events are transmission end, data arrival, ACK arrival, and timeout. Transmission starts immediately when the link is idle and a retry or new packet is eligible. Transmission occupies 1 ms; the data arrives 6 ms after its start, and its ACK arrives 11 ms after the start. ACK serialization and processing are zero, and ACKs do not occupy the forward data link. Simultaneous ordinary events use simlib's insertion order. Timer expiry has a 0.00000001 ms tie offset so a valid ACK at the expiry time wins; this negligible numerical tie rule is not a modeled processing delay.

Sender state consists of the oldest unacknowledged ID (base), next new ID, selective-ACK flags, pending-retry flags, per-packet timer generation counters, GBN timer generation, and link busy state. Receiver state is the next in-order ID and a bounded buffer of accepted packets. Buffer entries release only when the missing prefix is complete. Packet identifiers are monotonically increasing absolute integers: no modulo wrap or sequence-space ambiguity is modeled. Memory is allocated for the configured horizon or finite file size, and state invariants enforce the send-window bound.

Every successful data reception returns an ACK, including duplicate or out-of-order receptions. Every ACK includes the highest contiguous received ID. For SR it additionally acknowledges the received packet if it is buffered beyond that prefix. An old duplicate can be reacknowledged; a packet above the receive window is discarded and returns only the cumulative prefix. This cumulative-plus-selective design permits a later ACK to recover earlier ACK loss, which materially affects the ACK-error results. GBN naturally uses cumulative ACKs only. An unsuccessful data attempt is discarded and generates no ACK.

A data-error draw occurs independently per transmission. A separate ACK-error draw occurs per generated ACK; one draw controls the entire cumulative-plus-selective ACK, even though its fields are scheduled as two internal events. SplitMix64 replaces simlib's legacy small-output random generator. Data and ACK streams have different initial states derived from the same supplied seed. Each protocol uses the same seed list, but retransmission histories consume draws differently; these are matched seed replications, not identical packet-by-packet error schedules.

SR starts a timer at the start of each attempt; expiry marks that unacknowledged packet for retry. Generation counters ignore stale timeouts. GBN starts its timer when the oldest outstanding packet is sent, restarts it on cumulative advancement while outstanding packets remain, and on expiry marks all outstanding packets for go-back transmission in increasing ID order. Pending retries have priority over new traffic. A packet already serializing is allowed to finish. If an ACK makes a queued retry obsolete, it is skipped. There are no NAKs or fast retransmit.

For continuously backlogged traffic, efficiency is the unique in-order delivered packet count times 1000 bits, divided by 1 Mbps times the measurement interval. Since one packet occupies 1 ms, this equals delivered packets divided by elapsed milliseconds. Retransmitted copies do not count as additional useful deliveries. Attempts per delivery is the number of forward transmission starts divided by the unique in-order delivery count in the same measurement interval. Warmup-crossing packets can cause a small boundary discrepancy in that ratio. Finite transfers stop only when the sender has ACK evidence covering every packet, rather than when the receiver first receives the file.


## 2. Experimental setup and reproducibility

The fixed packet size is 1000 bits, the forward bitrate is 1 Mbps, and one-way propagation is 5 ms. The default timeout is 15 ms measured from transmission start. The propagation round trip is 10 ms; the complete start-to-ACK cycle is 11 ms after including data serialization. [1]

Each backlogged run measures 100000 ms after 10000 ms warmup. Five seeds are used: 400452897, 333333, 2026, 104729, and 8675309. Seed 400452897 is explicitly identified as the required student-ID seed in Lab 3's lab/REPORT.md; it is reused here rather than inventing an ID. Finite-transfer scenarios use 30 seeds, 400452897 + 104729*k for k=0,...,29, with no warmup. All five protocol/window profiles use identical seeds within a comparison. [2, 3]

Profiles are S&W Ws=Wr=1, GBN Wr=1, and SR Wr=4,16,64. Where Ws varies, each GBN/SR profile takes the plotted Ws. Wr can exceed Ws; this is a stated receiver capacity, not an additional sender constraint. Effective buffering is then limited by how many packets the sender can have outstanding. The fixed send window for Experiments 3(a), 4, and 5 is 32, comfortably above the error-free threshold of 11.

The window grid in Experiments 2, 3(b), and 6 is 1,2,4,6,8,10,11,12,16,24,32,48,64. Experiment 3(a) varies pd over 0,0.01,0.025,0.05,0.1,0.2,0.3,0.4,0.5 with pa=0. Experiment 3(b) uses pd=0.1, pa=0. Experiment 4 fixes pd=0.1 and varies pa on the same probability grid. Experiment 5 fixes pd=pa=0.1 and varies timeout over 2,5,8,10,11,12,15,20,30,50,75,100 ms. Experiment 6 uses N=100 and (pd,pa)=(0,0),(0.05,0),(0.05,0.05). Experiment 7 repeats all three cases for N=10 and N=1000 with Ws=1,4,8,11,16,32,64.

Plot markers show means, with pointwise two-sided 95% Student-t confidence intervals across independent seeds. The critical values are 2.776445105 for five seeds and 2.045229642 for 30 seeds. No simulation points are connected by piecewise-linear interpolation. Lines shown only in the first two comparison plots are analytical reference functions, explicitly labeled. Repeated S&W references reuse the identical runs, so horizontal repetitions are not additional independent samples. Error-free finite outcomes are deterministic even though the same 30-seed grid is retained for consistency.

results/runs.csv contains 13550 rows, with parameters and per-run outcomes. Identical configurations shared between experiments were executed once and reused, for 10890 unique main-suite runs; the row count is not a count of independent configurations. results/summary.csv contains the corresponding means and confidence intervals. The complete plotting manifest lists 17 figures. Reproduce with setup.ps1 and run_all.ps1 in native PowerShell, or python -m pip install -r requirements.txt followed by python run.py, python check_reliability.py, and python build_report.py. GCC must be on PATH. Linux execution was tested; the Windows scripts are supplied but were not executed in this Linux environment.


## 3. Experiment 1: event-trace verification

Six complete short traces are saved in results/traces/: S&W, GBN, and SR each with pd=pa=0 and pd=pa=0.5. Each trace transfers 12 packets using seed 400452897; GBN and SR use Ws=12, with Wr=1 and Wr=16 respectively. Times are milliseconds and IDs start at zero. Each run ends with all 12 unique packets delivered and acknowledged.

In the error-free S&W trace, packet 0 starts at t=0, arrives at t=6, and its ACK returns at t=11. No timeout fires, and the next packet starts on ACK reception. In the error-free pipelined traces, packets start 1 ms apart, and ACKs return 11 ms after their respective starts. No retry occurs.

The SR error trace begins with packet 0 lost at t=6. Packet 1 is accepted at t=7 and selectively acknowledged at t=12, while the cumulative ACK remains -1 (no prefix yet delivered). Packet 4 is accepted at t=10 but its ACK is lost. At t=15, packet 0 times out and is retried; packet 1 does not time out because its selective ACK was received. This verifies buffering across a gap, selective timer suppression, data loss without ACK generation, and ACK loss after successful data reception.

GBN discards packets arriving beyond the missing next ID and returns the last contiguous prefix. Its oldest-packet timeout causes a go-back sequence. S&W shows retries of the same ID after both data loss and ACK loss; duplicate data causes another ACK without another unique delivery. Full traces expose the sequence, send base, next ID, and receive base needed to audit those transitions.

Automated verification compares 52 window/receiver combinations against the exact error-free efficiency and 208 finite-transfer cases against exact completion time and transmission count: 260 comparisons passed. Error-free finite tests cover N=1,10,100,1000. Four long-run S&W error combinations agree within 0.001 absolute efficiency with the exact renewal calculation. The source asserts the sender's window invariant at every event. Eight additional finite runs with pd=pa=0.5, four window profiles, and timeouts 2 and 15 ms passed AddressSanitizer and UndefinedBehaviorSanitizer without reported memory or undefined-behavior faults. [2]


## 4. Experiment 2: error-free link efficiency

A packet uses 1 ms of serialization plus 10 ms round-trip propagation before its ACK returns. With no errors and no premature timeout, efficiency is min(1, Ws/11). The minimum send window that completely fills the pipe is therefore ceil(11/1)=11 packets. S&W has efficiency 1/11, or about 9.09%.

The measured GBN and all three SR receiver-window profiles agree with this formula. A gap never occurs, so even Wr=1 accepts every packet in order; receive buffering is unnecessary. GBN and SR overlap under these error-free conditions. Increasing Ws above 11 adds no throughput because the forward link already sends one useful packet every millisecond. Some markers overlap exactly for this reason. [2]

![Figure 1. Experiment 2: efficiency. Source: results/runs.csv and results/summary.csv [2].](figures/exp2_efficiency.png)

Figure 1. Experiment 2: efficiency. Source: results/runs.csv and results/summary.csv [2].


## 5. Experiment 3(a): packet errors at a fixed send window

Ws=32 removes the error-free pipeline limitation, but it does not guarantee full utilization in the presence of recovery stalls. At pd=0.1, GBN efficiency is 0.2656, while SR with Wr=4,16,64 gives 0.3062, 0.7969, and 0.8571. S&W is 0.0792. All curves return to their error-free values at pd=0. [2]

For S&W with timeout T>=11, an attempt succeeds with probability q=(1-pd)(1-pa). A success occupies 11 ms and a failed attempt consumes T ms before the next attempt. Its exact renewal efficiency is q/[11*q+T*(1-q)]. This is the S&W analysis curve in the plot. The ideal fully buffered SR transmission limit with pa=0 is 1-pd; attempts per useful delivery approach 1/(1-pd). Finite send windows can prevent SR from reaching this limit even when the receive buffer is large.

An often-used idealized saturated GBN RTT-recovery reference is (1-pd)/(1+2*a*pd), with a=5 ms / 1 ms=5. It is plotted as an analytical comparison, not as an exact prediction for this timer-driven implementation. It assumes an idealized round-trip loss-recovery penalty. At pd=0.1 it predicts 0.45, above the observed GBN 0.2656. Here there is no NAK, timeout is 15 ms, and advancing cumulative ACKs restart the oldest timer, delaying a missing packet's recovery; queued in-flight and go-back attempts also cost capacity. Exact numerical agreement with this idealized formula should not be claimed. Lecture notes were not supplied, so this report uses explicitly stated standard reference assumptions rather than attributing an unseen formula to the course.

A small SR receive window discards more correctly received packets following a gap, increasing repeated work. A larger buffer preserves them, making the missing packet the main recovery burden. Wr=64 exceeds Ws=32 and can retain every out-of-order packet within the sender's outstanding span; nonetheless the send window can still block while waiting for the earliest missing packet.

![Figure 2. Experiment 3a: efficiency. Source: results/runs.csv and results/summary.csv [2].](figures/exp3a_efficiency.png)

Figure 2. Experiment 3a: efficiency. Source: results/runs.csv and results/summary.csv [2].


## 6. Experiment 3(b): send-window effects with packet errors

At pd=0.1 and pa=0, enlarging Ws initially improves both protocols by allowing more overlap. With a full receive buffer, SR approaches its useful-transmission limit as Ws grows: Wr=64 efficiency rises from 0.5279 at Ws=11 to 0.8571 at Ws=32 and 0.8999 at Ws=64. Its attempts per delivery stays near 1/(1-0.1)=1.1111. [2]

GBN gains much less. At Ws=11 it delivers with efficiency 0.2710, and at Ws=32 it gives 0.2656. Attempts per delivery increase from 2.235 to 3.765. More pipelining also places more packets behind a loss, so they are discarded or replayed. A larger send window is therefore not automatically better for GBN with errors.

For SR, enlarging Ws without enlarging Wr can likewise increase discarded out-of-order traffic. Sender flow control limits unacknowledged sequence span, while receiver buffering limits how much correctly received traffic survives a gap. The two windows solve different problems. At Ws=1 all profiles become stop-and-wait in operation, regardless of nominal receiver capacity.

![Figure 3. Experiment 3b: efficiency. Source: results/runs.csv and results/summary.csv [2].](figures/exp3b_efficiency.png)

Figure 3. Experiment 3b: efficiency. Source: results/runs.csv and results/summary.csv [2].

![Figure 4. Experiment 3b: attempts per delivery. Source: results/runs.csv and results/summary.csv [2].](figures/exp3b_attempts_per_delivery.png)

Figure 4. Experiment 3b: attempts per delivery. Source: results/runs.csv and results/summary.csv [2].


## 7. Experiment 4: ACK errors and cumulative recovery

With pd=0.1, Ws=32, and increasing pa from 0 to 0.5, S&W efficiency falls from 0.0792 to 0.0343; its attempts per delivery rise from 1.109 to 2.213. Since no later packet can be sent before the current ACK, an ACK loss generally requires a retry. For timeouts above 11 ms, replacing q with (1-pd)(1-pa) in the renewal formula explains why data and ACK loss have similar S&W effects. [2]

GBN efficiency changes much less, from 0.2656 to 0.2589. A lost cumulative ACK is often covered by the next cumulative ACK. This does not reverse the receiver's already completed deliveries and does not create the out-of-order data gap caused by a lost data packet. GBN already spends much of its time recovering data gaps in this scenario, so moderate ACK loss adds relatively little to that penalty.

SR Wr=64 efficiency declines from 0.8571 to 0.7027, while attempts rise from 1.111 to 1.421. Cumulative prefix information repairs many ACK losses, but a selective ACK for a packet beyond a persistent hole may not yet be covered by the prefix; losing it can trigger a redundant retry. A wider receive window still preserves useful data. Small changes or apparent improvements in the narrow-buffer SR curves should be judged against the confidence bars and the changed random histories, not interpreted as a general benefit from ACK errors.

These ACK-error results depend on the stated cumulative-plus-selective ACK format. A pure individual-ACK SR design would need a separate experiment and could suffer a larger ACK-loss penalty. This modeling difference is part of the interpretation, not a reason to substitute data-error probability for ACK-error probability in every protocol's formula.

![Figure 5. Experiment 4: efficiency. Source: results/runs.csv and results/summary.csv [2].](figures/exp4_efficiency.png)

Figure 5. Experiment 4: efficiency. Source: results/runs.csv and results/summary.csv [2].

![Figure 6. Experiment 4: attempts per delivery. Source: results/runs.csv and results/summary.csv [2].](figures/exp4_attempts_per_delivery.png)

Figure 6. Experiment 4: attempts per delivery. Source: results/runs.csv and results/summary.csv [2].


## 8. Experiment 5: retransmission timeout tradeoffs

The timeout sweep covers values below, near, and far above the 11 ms start-to-ACK cycle with pd=pa=0.1 and Ws=32. At 5 ms, SR Wr=64 has efficiency 0.4663 and 2.145 attempts per delivery; at 12 ms it gives 0.8465 and 1.173. Premature timers resend packets whose valid ACKs are still propagating, consuming link capacity without increasing unique delivery. At 100 ms, its efficiency is only 0.2680 even though attempts per delivery remains near 1.171: it wastes time waiting rather than sending extra copies. [2]

GBN exposes a broader retransmission burst when a timeout fires. Long timeouts hold the receiver behind a missing prefix and delay the entire go-back recovery. SR can continue buffering other packets, especially with a large Wr, but a finite sender window eventually fills behind the missing base packet. Small Wr loses this buffering advantage.

S&W requires a more careful interpretation: its efficiency at timeout 2 ms is 0.0872, higher than 0.0694 at 15 ms, but attempts per delivery increase from 1.228 to 6.231. Frequent duplicates can recover a lost attempt or ACK sooner while leaving little useful pipelining to disrupt. GBN also has a measured goodput peak at a sub-RTT timeout in this grid. This does not make premature timeout efficient in transmission cost; both requested metrics are necessary to evaluate it.

For the broad-buffer SR profile, a timeout just above 11 ms is a strong compromise in this fixed-delay model. The sweep is a finite grid and does not establish a universal optimum. Real links with variable delays or processing would need additional timeout margin; such variability is outside this lab's fixed-delay assumptions.

![Figure 7. Experiment 5: efficiency. Source: results/runs.csv and results/summary.csv [2].](figures/exp5_efficiency.png)

Figure 7. Experiment 5: efficiency. Source: results/runs.csv and results/summary.csv [2].

![Figure 8. Experiment 5: attempts per delivery. Source: results/runs.csv and results/summary.csv [2].](figures/exp5_attempts_per_delivery.png)

Figure 8. Experiment 5: attempts per delivery. Source: results/runs.csv and results/summary.csv [2].


## 9. Experiment 6: finite transfers of 100 packets

With no errors, the acknowledged completion time for Ws>=11 is N+10 ms, which is 110 ms for N=100. Before the pipeline fills, for Ws<11 the exact completion time is 11*floor((N-1)/Ws) + ((N-1) mod Ws) + 11 ms. S&W therefore takes 1100 ms. This accounts for both initial pipeline fill and the final ACK, rather than reporting the data serialization time alone. All error-free profiles agree. [2]

For pd=0.05, pa=0, and Ws=32, mean times are 232.27 ms for GBN, 186.43 ms for SR Wr=4, 119.83 ms for SR Wr=16, and 119.37 ms for SR Wr=64. Larger receive buffers recover the file with fewer discarded followers after a loss.

Adding pa=0.05 changes GBN's mean to 233.63 ms and SR Wr=64's to 121.87 ms, versus S&W at 1258.00 ms. Lost intermediate ACKs can be repaired cumulatively, but a lost final ACK cannot be covered by new file packets after the file is exhausted. Completion therefore includes any final recovery delay. The small GBN difference has overlapping confidence intervals and should not be overstated.

Increasing Ws initially reduces completion time, but beyond the error-free threshold there is no deterministic speedup. With errors, large SR windows provide extra recovery tolerance if Wr is also sufficiently large. GBN or narrow-buffer SR can spend more attempts on discarded followers, so the error-free threshold alone does not determine the best finite-transfer window. Each plot uses 30 replications per point and shows the uncertainty of the mean, not the spread of individual file times.

![Figure 9. Experiment 6_pd0_pa0: completion ms. Source: results/runs.csv and results/summary.csv [2].](figures/exp6_pd0_pa0_completion_ms.png)

Figure 9. Experiment 6_pd0_pa0: completion ms. Source: results/runs.csv and results/summary.csv [2].

![Figure 10. Experiment 6_pd0.05_pa0: completion ms. Source: results/runs.csv and results/summary.csv [2].](figures/exp6_pd0.05_pa0_completion_ms.png)

Figure 10. Experiment 6_pd0.05_pa0: completion ms. Source: results/runs.csv and results/summary.csv [2].

![Figure 11. Experiment 6_pd0.05_pa0.05: completion ms. Source: results/runs.csv and results/summary.csv [2].](figures/exp6_pd0.05_pa0.05_completion_ms.png)

Figure 11. Experiment 6_pd0.05_pa0.05: completion ms. Source: results/runs.csv and results/summary.csv [2].


## 10. Experiment 7: files of 10 and 1000 packets

All three error cases from Experiment 6 are repeated for N=10 and N=1000. For N=10 and no errors, Ws>=10 is enough to send the entire file continuously and complete in 20 ms; the listed grid first attains that at Ws=11. No window above the number of file packets can create additional concurrency. For N=1000, the no-error full-pipeline time is 1010 ms. S&W requires 110 ms and 11000 ms respectively. [2]

At pd=pa=0.05 and Ws=32, N=10 completion is 33.07 ms for GBN versus 26.87 ms for SR Wr=64. For N=1000 these means are 2337.17 ms and 1099.83 ms. SR Wr=16 and Wr=64 overlap for the ten-packet file because both exceed the entire possible out-of-order span.

Small files emphasize initial propagation and the final ACK or tail retry; a steady-state efficiency estimate alone is a poor completion-time predictor. Larger files amortize the fixed 10 ms propagation overhead and make repeated recovery costs and the gap between GBN and SR more consequential. For large N, N divided by long-run useful-packet rate gives a useful approximate scale, but tail loss and finite start/end effects still prevent it from being an exact finite-transfer formula. Receiver capacity above the file's possible outstanding span adds no benefit, while a long transfer can use the full buffer repeatedly.

![Figure 12. Experiment 7_N10_pd0_pa0: completion ms. Source: results/runs.csv and results/summary.csv [2].](figures/exp7_N10_pd0_pa0_completion_ms.png)

Figure 12. Experiment 7_N10_pd0_pa0: completion ms. Source: results/runs.csv and results/summary.csv [2].

![Figure 13. Experiment 7_N10_pd0.05_pa0: completion ms. Source: results/runs.csv and results/summary.csv [2].](figures/exp7_N10_pd0.05_pa0_completion_ms.png)

Figure 13. Experiment 7_N10_pd0.05_pa0: completion ms. Source: results/runs.csv and results/summary.csv [2].

![Figure 14. Experiment 7_N10_pd0.05_pa0.05: completion ms. Source: results/runs.csv and results/summary.csv [2].](figures/exp7_N10_pd0.05_pa0.05_completion_ms.png)

Figure 14. Experiment 7_N10_pd0.05_pa0.05: completion ms. Source: results/runs.csv and results/summary.csv [2].

![Figure 15. Experiment 7_N1000_pd0_pa0: completion ms. Source: results/runs.csv and results/summary.csv [2].](figures/exp7_N1000_pd0_pa0_completion_ms.png)

Figure 15. Experiment 7_N1000_pd0_pa0: completion ms. Source: results/runs.csv and results/summary.csv [2].

![Figure 16. Experiment 7_N1000_pd0.05_pa0: completion ms. Source: results/runs.csv and results/summary.csv [2].](figures/exp7_N1000_pd0.05_pa0_completion_ms.png)

Figure 16. Experiment 7_N1000_pd0.05_pa0: completion ms. Source: results/runs.csv and results/summary.csv [2].

![Figure 17. Experiment 7_N1000_pd0.05_pa0.05: completion ms. Source: results/runs.csv and results/summary.csv [2].](figures/exp7_N1000_pd0.05_pa0.05_completion_ms.png)

Figure 17. Experiment 7_N1000_pd0.05_pa0.05: completion ms. Source: results/runs.csv and results/summary.csv [2].


## 11. Reliability, limitations, and source record

The reliability sweep in results/reliability.csv compares 100000 ms against 1000000 ms measurement intervals, each with 10000 ms warmup and five seeds. GBN Ws=32, pd=0.1, pa=0 changes from efficiency 0.265608 to 0.264558. SR Wr=16 at pd=pa=0.1 changes from 0.769034 to 0.768869, and SR Wr=64 with timeout 100 ms changes from 0.267996 to 0.268236. Heavy-error S&W changes from 0.017884 to 0.017776. These differences are small relative to the protocol effects discussed above and are compatible with the short-run seed intervals. This is representative run-length evidence, not a convergence proof for every point. [2]

Intervals are pointwise and are not adjusted for simultaneously inspecting many plotted points. Five long replications can leave small differences unresolved; finite-transfer tail estimates from 30 samples are still uncertain. The model has constant serialization and propagation, independent Bernoulli errors, ideal ACK serialization, unlimited identifier space, no reordering by the physical link, and a fixed timer rather than adaptive RTT estimation. These results apply to that system and the documented ACK/timer policy. No external lecture notes or measured hardware results were available.

[1] User-supplied coe4dk4_lab_4_2026.pdf, Computer Engineering 4DK4 Lab 4, Simulation of ARQ Protocols, Sections 1-3. It defines the requested experiments and defaults; the user's request authorizes the implementation work.

[2] Accompanying generated evidence: src/arq.c, run.py, results/runs.csv, results/summary.csv, results/reliability.csv, results/validation.txt, results/traces/, and figures/. These are the sources of every simulated result in this writeup. build_report.py regenerates the report from the saved summaries and plot manifest.

[3] https://github.com/chirackd/4DK4-Lab-3, main commit 1089334e06ed30eeedd6e0dadbde3b42b7d273d7. simlib.c blob 08792d9ef92ad7d97e260fa2ee9aa3234c9817c8, simlib.h blob 689d17061c9d45d3084fb06be1d0c115d6e2808f. lab/REPORT.md supplies student-ID seed 400452897. Existing copyright/license notices are retained in vendor/.

[4] https://github.com/chirackd/COMPENG_4DK4_Lab_2, packet_transmission.c blob 0a4e164335825ab1eae9ea8ee61e50013066267c and simlib.c blob 08792d9ef92ad7d97e260fa2ee9aa3234c9817c8, retrieved from the connected repository. Its server-serialization design and experiment-folder conventions informed the new model. ARQ logic is newly implemented; the earlier labs did not contain this protocol model.
