#!/usr/bin/env python3
"""Build PDF, DOCX and Markdown from one reviewed set of simulation evidence."""
import os,json,math,html
from pathlib import Path
R=Path(__file__).resolve().parent
os.environ.setdefault('MPLCONFIGDIR',str(R/'.mplcache'))
import pandas as pd
S=pd.read_csv(R/'results/summary.csv');RAW=pd.read_csv(R/'results/runs.csv.gz')
D=pd.read_csv(R/'results/model_comparison_summary.csv');REF=pd.read_csv(R/'results/reference_comparison.csv')
REL=pd.read_csv(R/'results/reliability.csv');CHECKS=pd.read_csv(R/'results/analytical_checks.csv')
manifest=json.loads((R/'results/figures.json').read_text())
PROFILES=['S&W','GBN','SR Wr=4','SR Wr=16','SR Wr=64'];blocks=[]
def heading(text):blocks.append(('heading',text))
def prose(text):
 for p in text.strip().split('\n\n'):blocks.append(('p',p.strip()))
def table(caption,headers,rows):blocks.append(('table',(caption,headers,rows)))
def figures(exps):
 for f in manifest:
  if f['exp'] in exps:blocks.append(('figure',f))
def get(exp,x,profile,metric='efficiency'):
 return S[(S.exp==exp)&(S.x==x)&(S.profile==profile)][metric].iloc[0]
def v(exp,x,profile,metric='efficiency',digits=4):return f'{get(exp,x,profile,metric):.{digits}f}'
def measured_table(exp,metric='efficiency',xs=None):
 g=S[S.exp==exp];xs=sorted(g.x.unique()) if xs is None else xs
 digits=2 if metric=='completion_ms' else 4 if metric=='efficiency' else 3
 rows=[]
 for x in xs:
  row=[f'{x:g}']
  for profile in PROFILES:
   q=g[(g.x==x)&(g.profile==profile)].iloc[0]
   row.append(f'{q[metric]:.{digits}f} ± {q[metric+"_ci95"]:.{digits}f}')
  rows.append(row)
 table(f'Experiment {exp}: {metric.replace("_"," ")} (mean ± pointwise 95% CI).',[g.xname.iloc[0],*PROFILES],rows)
def diag(ws,wr,pd_,pa=0,t=15,variant='default',metric='efficiency'):
 return D[(D.ws==ws)&(D.wr==wr)&(D.pd==pd_)&(D.pa==pa)&(D.tout==t)&(D.variant==variant)][metric].iloc[0]
heading('Executive summary')
prose(f'''The link becomes fully utilized without errors when the send window reaches 11 packets. With data errors, preserving correctly received packets behind a missing packet is the decisive advantage of Selective Repeat (SR). At Ws=64, pd=0.1, pa=0 and timeout 15 ms, measured efficiencies are {v('3a',.1,'S&W')} for Stop-and-Wait (S&W), {v('3a',.1,'GBN')} for Go-Back-N (GBN), and {v('3a',.1,'SR Wr=64')} for SR with Wr=64. These are simulation results, not hardware measurements. [1, 2]

For a 100-packet file, no-error completion falls from 1100 ms with S&W to 110 ms at Ws≥11. With pd=pa=0.05 and Ws=64, the new mean acknowledged completion times are {v('6_pd0.05_pa0.05',64,'S&W','completion_ms',2)} ms, {v('6_pd0.05_pa0.05',64,'GBN','completion_ms',2)} ms, and {v('6_pd0.05_pa0.05',64,'SR Wr=64','completion_ms',2)} ms for S&W, GBN, and full-buffer SR respectively.

Review against the supplied comparison report identified a timer-policy mismatch in our earlier GBN model and a less general recovery rule for intermediate receive windows. The revised implementation uses one per-frame timer engine and an explicitly stated replay rule. ACK fields are now processed atomically; all events at a timestamp are processed before another transmission starts. Matched comparisons reproduce the reference's main results without using its code or fitting the random seeds to its numbers. Some statements in that report are qualified or rejected where they exceed its own evidence. [5]

The new run length is ten times the earlier measurement interval, and finite transfers use 100 independent replications instead of 30. This report adds an independent Python simulation oracle, analytical and boundary checks, matched-model experiments, numerical tables with confidence intervals, and a record of retained differences. Results should be interpreted with the documented ACK and recovery policies, not as universal values for every implementation called GBN or SR.''')
heading('1. Model, definitions and analytical expectations')
prose('''The source sends fixed 1000-bit packets over one 1 Mbps data link. Serialization takes Tf=1 ms. Propagation takes 5 ms each way, and ACK serialization and processing are zero. Therefore the propagation round trip is 10 ms while the full transmission-start-to-ACK cycle is t0=11 ms. The default retransmission timeout T=15 ms is measured from transmission start. A failed data transmission generates no ACK. Each generated ACK is independently lost with probability pa; each data attempt is independently lost with probability pd. [1]

Backlogged efficiency is unique in-order delivered bits divided by link bitrate times the measurement interval. In these units, η = delivered packets / elapsed milliseconds. Attempts per delivery A is the number of data transmission starts divided by unique in-order deliveries in the same interval. It counts redundant copies. Finite-transfer completion ends when the sender has acknowledgement evidence for all N initially available packets, including final ACK recovery; it does not stop at the last receiver arrival. Warmup-crossing packets can cause a small count-boundary discrepancy in a long-run ratio.

Without errors, Ws packets can occupy the pipe during an 11 ms ACK cycle, giving η=min(Ws/11,1). Thus Ws=11 is the smallest full-utilization window and S&W efficiency is 1/11. The receive window has no effect when arrivals stay in order.

For S&W when T≥11 ms, let q=(1-pd)(1-pa). There are (1-q)/q failed attempts on average before one success. A failure costs T ms and a successful cycle costs 11 ms. Therefore E[time per delivered packet]=11+T(1-q)/q, η=q/[11q+T(1-q)], and A=1/q. This formula is not applied below 11 ms, where attempts overlap ACKs still in flight.

For a sufficiently large, continuously transmitting GBN window with per-frame timeout recovery and pa=0, the packet-error recovery comparison is η≈(1-pd)/[1+(T/Tf-1)pd]. At T=15 ms this is (1-pd)/(1+14pd). It represents one useful serialization time plus the error recovery penalty per delivered packet; at Ws=T/Tf=11 it gives (1-pd)/(1+10pd). Its assumptions exclude an ACK-restarted oldest-packet timer, small-window idle time, and premature timeouts. Agreement is a check of this specific regime, not a definition of correctness for all GBN implementations.

For SR with enough sender and receiver capacity, no premature timeouts and pa=0, only lost data need retry: η approaches 1-pd and A approaches 1/(1-pd). These are useful limits, not an assurance that any window which fills the error-free pipe also covers multiple losses and their recovery delays.

For finite no-error files, if Ws≥11, completion is N+10 ms. For Ws<11, the exact value is 11 floor((N-1)/Ws) + ((N-1) mod Ws) + 11 ms. Equivalently, N milliseconds of serialization plus a final 10 ms propagation term and a window-limited idle penalty. This formula includes the start and tail, unlike N/η used as a long-file approximation.''')
table('Fixed parameters and measurement definitions.',['Quantity','Value / interpretation'],[['Data packet / bitrate','1000 bits / 1 Mbps'],['Serialization / one-way propagation','1 ms / 5 ms'],['ACK cycle / default timer','11 ms / 15 ms from transmission start'],['Data / ACK error model','Independent Bernoulli per attempt / generated ACK'],['Steady useful efficiency','Unique in-order deliveries × 1 ms / measured time'],['Finite completion','First transmission start to sender confirmation of all N'],['Identifier space','Absolute increasing integers; no modulo ambiguity']])
heading('2. Simulator architecture and recovery policy')
prose('''src/arq.c implements the new ARQ model. vendor/simlib.c, simlib.h and trace.h remain the earlier labs' event-list and clock library, with their original license notices. Lab 2's serialized start/end transmission pattern and both labs' experiment-directory and PowerShell conventions are retained. ALOHA or queueing arrival logic is not reused because the present source and link differ. [3, 4]

One parameterized receiver buffers an accepted packet inside [recv, recv+Wr), then delivers the largest contiguous prefix. With Wr=1 it discards out-of-order packets, giving GBN reception. With Ws=Wr=1 only one packet can be outstanding, giving S&W. Sender state stores base, next new ID, ACK flags, retry flags, timer generations and busy state. Receiver state stores the next expected ID and buffered IDs. Assertions enforce 0≤next-base≤Ws. Arrays are sized for the configured horizon or finite file; this version does not claim a constant-memory ring buffer.

Every outstanding attempt has its own timer, started at transmission start. On timeout of k, queue k and every unacknowledged outstanding packet j≥k+Wr for replay. Invalidate timers for newly queued packets; restart each timer when its next attempt starts. A timer never directly transmits onto a busy link. Retries take priority over new packets and are selected in increasing ID order. ACKed retry entries are skipped. A transmission already in progress is allowed to finish.

This replay policy is deliberately explicit. When Wr=1, the oldest missing packet causes a go-back burst. When Wr≥Ws, no higher packet satisfies the cutoff, so recovery is selective. Intermediate Wr proactively replays distant followers. It is NOT logically guaranteed that they were discarded: k might have arrived and only its ACK was lost, or later attempts may have changed receiver state. This is a conservative sender policy, not access to hidden receiver knowledge. The alternative that retransmits only the timed-out packet remains available through ARQ_INDIVIDUAL=1 and is quantified in the design checks.

Each successful data reception generates one atomic ACK containing the highest contiguous received ID plus a selective ID if the answered packet remains buffered beyond that prefix. Outside-window arrivals return only the prefix; old duplicates are reacknowledged without another unique delivery. A single ACK-error draw governs the whole ACK. Sender processing applies both fields before sliding the window or starting a transmission. This removes the earlier implementation's split internal ACK events.

Events use absolute millisecond times. All events at a timestamp finish before a new transmission is chosen. A valid ACK at exactly its timeout timestamp wins; the timer handler defers to an ACK already scheduled at that time. There is no added epsilon delay in the default timer. This matters because exact integer delays can make premature new transmissions at a tied timestamp consume a serialization slot before an already-due retry. Simlib's underlying implementation remains unchanged.

Data errors are drawn on data-arrival processing; an unsuccessful transmission is discarded and no ACK is generated. The error outcome becomes known to the model at that event rather than at serialization end; because the sender receives no error feedback and the two channels have separate independent streams, this does not grant the sender additional information. SplitMix64 uses separate data and ACK states derived from the supplied seed. Reusing seeds across protocols matches replications, not every packet's loss outcome: changed retransmission histories consume draws differently.

ARQ_LEGACY=1 retains the old ACK-restarted oldest timer for Wr=1 (and the old individual retry approach for larger Wr) for policy comparisons. ARQ_CUMULATIVE_ONLY=1 removes selective ACK information. These environment switches are diagnostic alternatives, not silently mixed into production plots. No NAK, fast retransmit, finite sequence wrap, header overhead or adaptive timer is modeled. A nominal Wr>Ws is allowed but adds no useful buffer capacity; the largest outstanding span is bounded by Ws.''')
table('Events and state transitions.',['Event','Scheduled at','Effect'],[['Transmission end','Start + 1 ms','Release serialization; next start waits for tied events'],['Data arrival','Start + 6 ms','Draw data loss; buffer/deliver or discard; generate ACK'],['ACK arrival','Successful receive + 5 ms','Draw already determined ACK outcome; apply both fields; advance base'],['Timeout','Attempt start + T','If current and unACKed, queue k and followers ≥k+Wr']])
blocks.append(('code','''on timeout(k), if unacknowledged and timer is current:
    queue k
    for j in outstanding with j >= k + Wr:
        if not acknowledged and not already queued:
            queue j; invalidate its old timer
when all events at this timestamp are finished:
    if link idle:
        send oldest unacknowledged queued packet
        else send a new packet if next < base + Ws
        start timer; schedule transmission end and data arrival'''))
heading('3. Experimental setup and statistical reliability')
keys=['ws','wr','pd','pa','tout','n','seed'];unique=len(RAW.drop_duplicates(keys))
prose(f'''The main suite has {len(RAW):,} stored replication rows representing {unique:,} unique simulations after reusing identical S&W references and configurations shared between experiments. Repeated references are not independent extra evidence. Per-run counts, parameters and metrics are inspectable in results/runs.csv.gz; summary.csv contains means and confidence intervals. Compression is lossless and pandas reads it directly. [2]

Every backlogged replication measures 1,000,000 ms after 10,000 ms warmup, ten times the earlier measurement duration. The five seeds are 400452897, 333333, 2026, 104729 and 8675309. The first is the student-ID seed documented in the existing Lab 3 report. Finite transfers use 100 seeds 400452897+104729k, k=0,...,99, with no warmup. The group's own seed is retained; no identifiers from the comparison report are adopted.

Means have pointwise two-sided 95% Student-t intervals, mean ± t·s/√r, with t=2.776445105 for five backlogged seeds and t=1.984216952 for 100 finite transfers. These intervals estimate the mean, not the distribution of individual file times. Tables round intervals for readability; a displayed 0.0000 is below that rounding precision, not proof of no variation. Full precision is retained in summary.csv. Intervals are not adjusted for multiple comparisons.

S&W always has Ws=Wr=1. GBN has Wr=1. Three SR receiver capacities are 4,16,64 packets. Experiments 3(a), 4 and 5 use Ws=64, so a large full-buffer SR profile is included. This also allows a matched comparison with the supplied report. We keep the original small/intermediate capacities rather than copying its 2/8 choices; supplementary checks explicitly use Wr=8 when matching that report.

Window grids emphasize the threshold at 11 and extend to 64. The timeout grid now includes 10.99, 11, 11.01 and 11.5 ms, so exact ties and fractional timeout effects are visible. ACK errors extend to 0.9 rather than ending at 0.5. Plot markers denote simulated means; error bars denote the stated intervals. Simulation points are not connected by piecewise-linear interpolation. Only labeled analytical functions are drawn as lines.''')
table('Experiment-specific parameters.',['Part','Varied','Fixed beyond the physical defaults'],[['1','Protocols; pd=pa=0 or 0.5','N=12; Ws=1 or 12; Wr=1 or 16; ID seed'],['2','Ws=1,2,4,6,8,10,11,12,16,24,32,48,64','pd=pa=0; T=15; three SR capacities'],['3(a)','pd=0,.01,.025,.05,.1,.2,.3,.4,.5','pa=0; Ws=64; T=15'],['3(b)','Same Ws grid as Part 2','pd=.1; pa=0; T=15'],['4','pa=0,.01,.025,.05,.1,.2,.3,.4,.5,.7,.9','pd=.1; Ws=64; T=15'],['5','T=2,5,8,10,10.99,11,11.01,11.5,12,15,20,30,50,75,100','pd=pa=.1; Ws=64'],['6','Ws grid; three error cases','N=100; (pd,pa)=(0,0),(.05,0),(.05,.05)'],['7','Ws=1,4,8,11,16,32,64; three error cases','N=10 and 1000; otherwise Part 6']])
heading('4. Experiment 1: verification by traces and independent models')
prose(f'''All six traces in results/traces/ transfer N=12 packets: S&W, GBN Ws=12/Wr=1 and SR Ws=12/Wr=16, each with pd=pa=0 and 0.5, seed 400452897. They include time, event, packet ID, sender base, next new ID and receiver base. No-error traces contain no retransmissions. Packet 0 starts at 0, arrives at 6 and is ACKed at 11 ms; full-pipeline transmissions start one millisecond apart until the finite source is exhausted.

With data errors, the traces show a lost arrival without ACK generation. GBN discards subsequent out-of-order arrivals; SR buffers accepted followers and selectively acknowledges them. With ACK errors, successful receiver delivery is not undone. The sender retries if it lacks evidence, and duplicates are reACKed without increasing unique delivery. These behaviors are also checked against an independent implementation, rather than accepted only because one trace looks plausible.

The existing 260 analytical no-error comparisons remain: 52 throughput checks across send/receive windows plus 208 exact finite completion-time and transmission-count checks for N=1,10,100,1000. Four long-run S&W error scenarios are checked against the renewal formula. verify_reference.py adds {len(CHECKS)} analytical and exact-boundary checks, including a 100-packet zero-error transfer with T=11 that must have exactly 100 attempts. test_oracle.py independently implements a heap event list, receiver and sender in Python and compares 144 small finite simulations against C. It checks completion time, total attempts and unique deliveries across six window configurations, data-only and ACK-only errors, heavy combined errors, and six timeout values from 2 to 50 ms.

The oracle shares the specified error generator to expose identical loss realizations, but does not reuse the C event scheduler, timer implementation or state transition code. It is a cross-implementation check, not a claim that identical random-number draws alone prove protocol correctness. Sanitizer results and main-suite conservation checks are recorded in results/validation.txt. [2]''')
for name in ['SW_pd_pa_0.txt','GBN_pd_pa_0.txt','SR_pd_pa_0.txt','SW_pd_pa_0.5.txt','GBN_pd_pa_0.5.txt','SR_pd_pa_0.5.txt']:
 path=R/'results/traces'/name
 if not path.exists():continue
 lines=path.read_text().splitlines()
 selected=lines[:10] if '_0.txt' in name else [l for l in lines if any(s in l for s in ['lost','TIMEOUT','duplicate','ACK selective'])][:12]
 prose('Trace excerpt: '+name+' (full trace remains in the accompanying evidence).')
 blocks.append(('code','\n'.join(selected)))
heading('5. Experiment 2: error-free window-size dependence')
prose('''All measured GBN and SR profiles follow min(Ws/11,1). Before Ws=11 the source exhausts its send window and idles while ACKs propagate. At Ws=11 the first ACK returns as the pipeline can accept another useful packet, and efficiency reaches one. Increasing Ws above 11 offers no gain without errors.

The receive window is irrelevant here because no missing packet creates a gap. GBN needs no buffer to reproduce SR's behavior when arrivals are ordered. The curves coincide; overlapping markers are exact agreement, not missing series. The numerical table retains S&W as its own horizontal reference and shows the send-window effect on the other profiles.''')
measured_table('2');figures(['2'])
heading('6. Experiment 3(a): packet-error probability and theoretical limits')
prose(f'''At Ws=64, pd=0.1 and pa=0, efficiencies are {v('3a',.1,'GBN')} for GBN, {v('3a',.1,'SR Wr=4')} for SR Wr=4, {v('3a',.1,'SR Wr=16')} for SR Wr=16, and {v('3a',.1,'SR Wr=64')} for full-buffer SR. S&W achieves {v('3a',.1,'S&W')}. All return to the no-error values at pd=0.

Full-buffer SR approaches 1-pd and the minimum attempts 1/(1-pd), because it retains followers behind a gap and selectively confirms them. The finite send window can still close after repeated losses, especially near pd=0.5. Therefore a shortfall below 1-pd is not automatically a simulator defect. Narrower receive windows discard or proactively replay more followers, placing their performance between GBN and full SR.

The revised GBN results agree closely with the per-frame recovery comparison (1-pd)/(1+14pd). Our previous ~0.2656 result at pd=0.1 came from a different ACK-restarted oldest timer, not from the same model producing a different random realization. The matched policy experiment in Section 11 separates that effect from send-window size. The old plot's round-trip-only recovery line has been replaced by the timeout-based expression under its explicit assumptions.

S&W matches q/[11q+15(1-q)], with q=1-pd. It has low absolute efficiency even at pd=0 because it cannot overlap packets. A moderate percentage loss in its already-small efficiency is not evidence that it outperforms a pipelined protocol.''')
measured_table('3a');figures(['3a'])
heading('7. Experiment 3(b): window size, useful throughput and repeated work')
prose(f'''At pd=0.1, SR Wr=64 efficiency rises from {v('3b',11,'SR Wr=64')} at Ws=11 to {v('3b',32,'SR Wr=64')} at Ws=32 and {v('3b',64,'SR Wr=64')} at Ws=64. Its attempts per delivery at Ws=64 are {v('3b',64,'SR Wr=64','attempts_per_delivery',3)}, near 1/0.9. Extra sender capacity covers the time while an early missing packet is retried and acknowledged; the error-free threshold alone is insufficient.

GBN efficiency at Ws=11 and 64 is {v('3b',11,'GBN')} and {v('3b',64,'GBN')} respectively. Its attempts per delivery rise from {v('3b',11,'GBN','attempts_per_delivery',3)} to {v('3b',64,'GBN','attempts_per_delivery',3)}. Once the link remains busy during recovery, additional send-window space cannot recover the correctly received followers that its Wr=1 receiver has discarded.

For intermediate SR windows, sender concurrency and receiver storage are separate constraints. A wider send window initially overlaps useful traffic, but a narrow receive window still rejects distant followers after a gap. Our conservative replay rule also replays followers outside the presumed gap span; the independent-retry alternative in Section 11 demonstrates how that policy affects performance. Increasing Ws without considering Wr and timeout recovery is therefore not a universal improvement.

For a continuously busy forward link, the counts give η·A≈1. If there is idle time, the product is below one; A is not generally equal to 1/η. This distinction explains why a small sender window can have similar attempts per useful packet but lower throughput.''')
measured_table('3b');measured_table('3b','attempts_per_delivery');figures(['3b'])
heading('8. Experiment 4: data loss versus ACK loss')
prose(f'''With pd=0.1 and pa increasing from 0 to 0.9, S&W efficiency falls from {v('4',0,'S&W')} to {v('4',.9,'S&W')}, while attempts per delivery increase from {v('4',0,'S&W','attempts_per_delivery',3)} to {v('4',.9,'S&W','attempts_per_delivery',3)}. Its q=(1-pd)(1-pa) controls the renewal result for T≥11: either loss can prevent confirmation of the single outstanding packet.

GBN falls from {v('4',0,'GBN')} to {v('4',.9,'GBN')}. A lost ACK is often covered by a later cumulative prefix; it does not remove a packet already delivered by the receiver. Moderate ACK loss is consequently much less harmful than a data gap. At very high pa, long runs of missing feedback finally close the window or cause unnecessary recovery.

SR Wr=64 falls from {v('4',0,'SR Wr=64')} to {v('4',.9,'SR Wr=64')}. A packet buffered behind an unfilled gap is not yet covered by the cumulative prefix, so loss of its selective ACK can require a redundant retry. Smaller receive windows have a different balance between retransmission and buffering costs. Apparent tiny improvements at some points should be read with their confidence intervals, not generalized into a benefit from ACK loss.

The comparison uses Ws=64 consistently with Part 3(a). Our window-size experiment and the matched Ws=32/64 diagnostics separately show why spare sender capacity matters: a larger window can keep producing later cumulative evidence after an ACK is lost. The supplied reference additionally compares Ws=11 and 64; those particular two-panel curves are not claimed to have been reproduced as a complete separate sweep here.

ACK-format assumptions matter. These results use a cumulative prefix plus a selective ID in one ACK. Pure cumulative SR loses information about buffered followers; pure individual-ACK schemes would recover lost feedback differently. Section 11 quantifies the cumulative-only variant rather than silently treating every ACK design as equivalent.''')
measured_table('4');measured_table('4','attempts_per_delivery');figures(['4'])
heading('9. Experiment 5: timeout costs and the 11 ms boundary')
prose(f'''The sweep spans 2 to 100 ms and resolves the boundary at 10.99,11,11.01 and 11.5 ms. For SR Wr=64, efficiency is {v('5',5,'SR Wr=64')} with {v('5',5,'SR Wr=64','attempts_per_delivery',3)} attempts per delivery at T=5, versus {v('5',12,'SR Wr=64')} with {v('5',12,'SR Wr=64','attempts_per_delivery',3)} at T=12. Timers below the full ACK cycle resend packets whose evidence is still in flight. Receiver buffering cannot turn those extra copies into new deliveries.

At T=100, SR Wr=64 efficiency is {v('5',100,'SR Wr=64')} and its attempts per delivery are {v('5',100,'SR Wr=64','attempts_per_delivery',3)}. Long timers can therefore waste elapsed time while requiring relatively few extra attempts. GBN loses more work because it discards followers after a data gap and must replay them; a large SR receive window protects that work until the sender window eventually fills.

S&W is an essential counterexample to an unqualified “best timeout equals RTT” conclusion. At T=2 it achieves {v('5',2,'S&W')} with {v('5',2,'S&W','attempts_per_delivery',3)} attempts per delivery, while T=11 achieves {v('5',11,'S&W')} with {v('5',11,'S&W','attempts_per_delivery',3)}. Sending redundant copies into otherwise idle time can recover a failed packet or ACK sooner. This increases goodput at substantial transmission cost. T=11 is the shortest non-spurious timeout under our tie rule, not the unconstrained maximum-goodput optimum across every allowed timeout.

Fractional timeouts are meaningful. At T=11.01 and 11.5, measured S&W efficiencies are {v('5',11.01,'S&W')} and {v('5',11.5,'S&W')}. The renewal expression varies continuously with T even when physical propagation and serialization delays are integers. The reference's claim that results depend only on which side of an integer the timeout lies is not generally true; its own S&W table also changes within that interval. The exact T=11 test confirms that ACKs win ties without an artificial added delay.

A timeout near the ACK cycle balances prompt recovery against spurious transmissions in the fixed-delay model. The best value depends on the metric, buffer sizes and loss process. We do not import a universal optimum or a claim of smooth integer-step behavior from the reference.''')
measured_table('5');measured_table('5','attempts_per_delivery');figures(['5'])
heading('10. Experiments 6 and 7: finite files and transfer-size effects')
prose(f'''For N=100 with no errors, all windowed profiles reach exactly 110 ms at Ws≥11; S&W takes 1100 ms. With pd=0.05 and no ACK errors at Ws=64, GBN takes {v('6_pd0.05_pa0',64,'GBN','completion_ms',2)} ms and SR Wr=64 takes {v('6_pd0.05_pa0',64,'SR Wr=64','completion_ms',2)} ms. With pd=pa=0.05 these become {v('6_pd0.05_pa0.05',64,'GBN','completion_ms',2)} and {v('6_pd0.05_pa0.05',64,'SR Wr=64','completion_ms',2)} ms. The corresponding S&W value is {v('6_pd0.05_pa0.05',64,'S&W','completion_ms',2)} ms.

Intermediate receive windows reduce completion time by preserving some followers while a gap recovers. Larger send windows improve finite transfers until serialization, recovery time or the number of available packets becomes the limit. Unlike the error-free threshold, an error-recovery plateau depends on buffering and timeout policy. The file's final packet is special: loss of the final ACK cannot be repaired by an ACK from a later new file packet, so completion must include a tail retry when needed.

Experiment 7 repeats all three error cases for N=10 and 1000. The no-error lower bounds are 20 and 1010 ms, compared with S&W's 110 and 11000 ms. A ten-packet file cannot exploit a window larger than ten; the sweep first reaches full no-error concurrency at Ws=11 because ten is absent from that subset's grid. SR Wr=16 and Wr=64 have enough capacity for all followers of that small file and coincide.

At pd=pa=0.05, Ws=32, N=10, mean GBN and full-buffer SR times are {v('7_N10_pd0.05_pa0.05',32,'GBN','completion_ms',2)} and {v('7_N10_pd0.05_pa0.05',32,'SR Wr=64','completion_ms',2)} ms; for N=1000 they are {v('7_N1000_pd0.05_pa0.05',32,'GBN','completion_ms',2)} and {v('7_N1000_pd0.05_pa0.05',32,'SR Wr=64','completion_ms',2)} ms. Initial propagation and the last recovery dominate short files. Large files amortize fixed propagation and accumulate repeated recovery costs, making sustained throughput and receive buffering more consequential.

N/η gives a useful long-file scale but is not an exact completion-time formula. Mean completion is averaged directly over completed independent transfers; taking an inverse of an averaged finite-transfer efficiency would be a different statistic. Each curve uses 100 replications with pointwise intervals, not the reference's thousands of within-seed transfers; our uncertainty is stated rather than claiming its narrower intervals.''')
for exp in ['6_pd0_pa0','6_pd0.05_pa0','6_pd0.05_pa0.05']:measured_table(exp,'completion_ms');figures([exp])
for n in [10,1000]:
 for pd_,pa in [(0,0),(.05,0),(.05,.05)]:
  exp=f'7_N{n}_pd{pd_}_pa{pa}';measured_table(exp,'completion_ms',[1,11,32,64]);figures([exp])
heading('11. Reconciliation with the supplied comparison report')
prose('''COE4DK4_Lab 4_Report.docx is used as a secondary comparison source, not a rubric, a verified implementation or a replacement for the handout. We inspected its model descriptions, included code snippets, numerical tables, and timeout discussion. The complete reference implementation and raw data were not supplied, so its internal test counts and confidence intervals cannot be independently certified. We compare only explicitly reported configurations and rounded results. Different seeds and generators mean that exact decimal identity is neither required nor expected. [5]

The main adopted change is a unified per-frame timeout/replay rule that recovers standard S&W, GBN-like go-back behavior and full SR through window parameters. We also adopted more diagnostic boundary points, a larger fixed sender window, larger finite samples and longer measurement intervals. These are justified by independent tests and analytically predictable regimes, rather than selected to make every reported number match.

The table below contains matched cases using our five seeds and generator. Differences are measured minus the reference's rounded efficiency. Where the difference is smaller than our interval or the reference's reported precision, it is consistent with their model agreeing within simulation uncertainty; it is not proof that every untested configuration is identical.''')
table('Matched checks against reported reference values; our intervals are separate from reference uncertainty.',['Ws/Wr','pd/pa','T ms','Reference η','Our η ± CI','Difference'],[[f'{r.ws:g}/{r.wr:g}',f'{r.pd:g}/{r.pa:g}',f'{r.tout:g}',f'{r.reference_efficiency:.4f}',f'{r.measured_efficiency:.5f} ± {r.ci95:.5f}',f'{r.difference:+.5f}'] for r in REF.itertuples()])
prose(f'''At Ws=64, pd=0.1 and pa=0, the revised GBN efficiency is {diag(64,1,.1):.5f}, versus {diag(64,1,.1,variant='legacy'):.5f} with the legacy ACK-restarted oldest-timer policy. This is a direct matched comparison; the earlier branch's ~0.2656 outcome was a model-policy difference, not evidence that the reference's ~0.375 was wrong. The per-frame policy also matches the recovery formula near 0.375 at T=15 and 0.45 at T=11/Ws=11.

With SR Ws=Wr=64 and pd=0.1, removing selective ACK information reduces efficiency from {diag(64,64,.1):.5f} to {diag(64,64,.1,variant='cumulative'):.5f}. This independently reproduces the reference's qualitative ACK-format check: buffered followers need selective evidence if they are not yet covered by the prefix. At Wr=8 with pd=pa=0.1, conservative replay gives {diag(64,8,.1,.1):.5f}, versus {diag(64,8,.1,.1,variant='individual'):.5f} for individual-only retries. Thus recovery policy for intermediate Wr is a consequential design choice, not just a cosmetic implementation difference.

The revised SR Ws=32/Wr=64 packet-error result is {diag(32,64,.1):.5f}, versus {diag(64,64,.1):.5f} at Ws=64. This isolates sender capacity from the receiver's nominal 64-packet capacity. The old report's larger shortfall from 1-pd at Ws=32 was partly a window effect, so a stronger matched comparison required using Ws=64.''')
table('Policy diagnostics at pd=0.1, T=15 ms (our measured η).',['Configuration','Default','Alternative','Interpretation'],[['GBN Ws=64, pa=0',f'{diag(64,1,.1):.5f}',f'{diag(64,1,.1,variant="legacy"):.5f}','Legacy ACK-restarted oldest timer'],['GBN Ws=64, pa=.1',f'{diag(64,1,.1,.1):.5f}',f'{diag(64,1,.1,.1,variant="individual"):.5f}','Individual retries without go-back'],['SR Ws=Wr=64, pa=0',f'{diag(64,64,.1):.5f}',f'{diag(64,64,.1,variant="cumulative"):.5f}','Cumulative-only ACK'],['SR Ws=64 Wr=8, pa=.1',f'{diag(64,8,.1,.1):.5f}',f'{diag(64,8,.1,.1,variant="individual"):.5f}','Individual-only retries']])
prose('''Claims not adopted uncritically:

A timeout does not prove a data packet is missing at the receiver: its ACK may have been lost. Therefore the reference's inference that every follower ≥k+Wr “must have been discarded” is too strong. The replay cutoff is retained as an explicit conservative policy, with alternative measurements, not as a theorem.

The reference concludes that the best S&W timeout is 11.01 ms, while its own table and discussion show higher unconstrained goodput at 1–2 ms using many more copies. We distinguish shortest non-spurious timeout from maximum goodput and from transmission efficiency.

The reference's statement that results depend only on the side of integer timeout boundaries is contradicted by the continuous S&W renewal expression and its own 11.01/11.5 ms values. Our fractional sweep checks the distinction directly.

A broad statement about whether burst errors help one protocol relative to others is not established by an independent-Bernoulli experiment. No burst channel is simulated here, so no ranking under burst errors is asserted.

The reference's claims of specific lecture slide numbers are secondary citations: the original slides were not supplied. We independently derive and test the formulas used here without claiming to have verified unseen slides. Different receive capacities, sampling designs and seed lists are identified rather than hidden in comparisons.''')
heading('12. Reliability, reproducibility and limitations')
relrows=[]
for key,g in REL.groupby(['ws','wr','pd','pa','tout','duration']):
 ws,wr,pd_,pa,t,duration=key;mean=g.efficiency.mean();ci=2.776445105*g.efficiency.std(ddof=1)/math.sqrt(len(g))
 relrows.append([f'{ws}/{wr}',f'{pd_:g}/{pa:g}',f'{t:g}',f'{int(duration-10000):,}',f'{mean:.6f} ± {ci:.6f}'])
table('Representative run-length checks; all use five seeds and 10000 ms warmup.',['Ws/Wr','pd/pa','T','Measured ms','η ± 95% CI'],relrows)
prose('''The reliability sweep compares 100000,1000000 and 3000000 measured ms at four representative configurations, including heavy-error S&W and long-timeout SR. The table exposes variation instead of asserting that one chosen horizon proves convergence everywhere. Compare interval widths with the operating differences discussed above; nearby points can remain unresolved even when broad protocol gaps are clear.

The error generator is portable and separate for data and ACKs, but deterministic PRNG streams are a modeling approximation. Errors are independent, with no burst correlation. The model omits variable processing, queuing of ACKs, congestion, finite sequence-space wrap and adaptive timers. Memory grows with configured horizon/file size. Measurements are specific to the stated replay, ACK and event-tie policies. Results at extremely high errors or tails not represented by the finite sample should not be extrapolated as guarantees.

Reproduce on native Windows with setup.ps1 then run_all.ps1, or use Python with GCC on Linux/macOS. The workflow compiles, validates no-error and S&W cases, runs all seven experiments, generates lossless-compressed raw evidence and plots, checks reliability and reference scenarios, runs the independent Python oracle, and rebuilds the PDF, DOCX and Markdown. GCC and Python must be on PATH. Native PowerShell scripts are supplied; this execution was tested on Linux, not Windows. Diagnostic flags must be unset for the main suite. The report's values are loaded from the current run, not transcribed from the comparison document.

The complete ZIP contains this Lab 4 package only. Prior Lab 3 experiments are not reintroduced. Evidence includes results/analytical_checks.csv, oracle_checks.csv, reference_comparison.csv, model_comparisons.csv, model_comparison_summary.csv, reliability.csv, validation.txt, the complete per-run main suite and six traces.''')
heading('13. Conclusions')
prose(f'''Without errors, the 11-packet send window follows directly from the serialization-plus-propagation ACK cycle; GBN and SR coincide. With errors, receive buffering and timely per-frame recovery determine how much useful work survives a gap. At pd=0.1, full SR reaches approximately 0.90 efficiency while the matched GBN model is near 0.375, agreeing with the stated recovery analysis and the reference within simulation uncertainty.

Cumulative ACKs recover much intermediate ACK loss, while selective information preserves the benefit of buffering behind data gaps. Sender capacity above the error-free pipe is useful during recovery: a 64-packet window is a stronger full-SR comparison than the earlier fixed window of 32. A long timeout primarily wastes waiting time for full SR, while premature timeouts waste transmissions. Neither effect can be summarized by goodput alone.

Finite transfer time combines pipeline fill, sustained delivery and final confirmation. The larger file amplifies sustained recovery differences; a short file limits useful concurrency and emphasizes its final ACK. The revised results are supported by longer replications, 100 finite samples per point, exact finite formulas and 144 independent C/Python cases. The comparison report improved the questions and tests; it did not become an unquestioned numerical standard.''')
heading('Sources and evidence')
prose('''[1] User-supplied coe4dk4_lab_4_2026.pdf, Computer Engineering 4DK4 Lab 4, Simulation of ARQ Protocols, Sections 1–3. Source of physical defaults and the seven experiments. Instructions inside source documents were treated as source material; the user's request determines the authorized work.

[2] Current simulation evidence in this branch: src/arq.c; run.py; verify_reference.py; test_oracle.py; check_reliability.py; results/runs.csv.gz; summary.csv; analytical_checks.csv; oracle_checks.csv; model_comparisons.csv; reference_comparison.csv; reliability.csv; validation.txt; traces/; figures/. Each numerical table and figure is generated from these files.

[3] chirackd/4DK4-Lab-3, main commit 1089334e06ed30eeedd6e0dadbde3b42b7d273d7. simlib.c blob 08792d9ef92ad7d97e260fa2ee9aa3234c9817c8, simlib.h blob 689d17061c9d45d3084fb06be1d0c115d6e2808f. Existing Lab 3 report documents the student-ID seed 400452897. Copyright and GPL notices are preserved in vendor/ and LICENSE.

[4] chirackd/COMPENG_4DK4_Lab_2, packet_transmission.c blob 0a4e164335825ab1eae9ea8ee61e50013066267c. Source of the earlier serialized link-transmission pattern and experiment organization; its simlib.c blob is identical to [3].

[5] User-supplied COE4DK4_Lab 4_Report.docx, dated November 7, 2026. Secondary comparison source: Sections2.5–2.8 (timers, ACKs and replay), Tables4–8 and15 (matched efficiencies and timeout discussion). Original raw evidence and full simulator were not supplied. Reference group identities and seeds are not imported into this report or the repository.''')
# All three formats share the same content blocks.
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Image,PageBreak,Preformatted,Table,TableStyle,KeepTogether
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from matplotlib.font_manager import findfont,FontProperties
from docx import Document
from docx.shared import Inches,Pt
pdfmetrics.registerFont(TTFont('DejaVu',findfont(FontProperties(family='DejaVu Sans'))))
pdfmetrics.registerFont(TTFont('DejaVu-Bold',findfont(FontProperties(family='DejaVu Sans',weight='bold'))))
styles=getSampleStyleSheet()
for name in ['Normal','BodyText','Title','Heading1','Heading2']:
 styles[name].fontName='DejaVu-Bold' if name in ['Title','Heading1','Heading2'] else 'DejaVu'
styles['BodyText'].fontSize=9.5;styles['BodyText'].leading=13.2;styles['BodyText'].spaceAfter=9
styles['Heading1'].fontSize=16;styles['Heading1'].leading=21
styles.add(styles['BodyText'].clone('Small'));styles['Small'].fontSize=7;styles['Small'].leading=9
pdfmetrics.registerFont(TTFont('DejaVuMono',findfont(FontProperties(family='DejaVu Sans Mono'))))
styles['Code'].fontName='DejaVuMono';styles['Code'].fontSize=6.5;styles['Code'].leading=9
story=[Paragraph('Computer Engineering 4DK4<br/>Lab 4: Simulation of ARQ Protocols',styles['Title']),Paragraph('Revised after independent comparison • November 12, 2026',styles['BodyText'])]
md=['# Computer Engineering 4DK4 — Lab 4\n\nSimulation of ARQ Protocols\n\nRevised November 12, 2026.\n']
doc=Document();doc.add_heading('Computer Engineering 4DK4 — Lab 4',0);doc.add_paragraph('Simulation of ARQ Protocols | Revised November 12, 2026')
doc.styles['Normal'].font.size=Pt(10)
figindex=0;tableindex=0;first=True
for kind,value in blocks:
 if kind=='heading':
  if not first:story.append(PageBreak());doc.add_page_break()
  first=False;story.append(Paragraph(html.escape(value),styles['Heading1']));md.append('\n## '+value+'\n');doc.add_heading(value,1)
 elif kind=='p':
  story.append(Paragraph(html.escape(value),styles['BodyText']));md.append(value+'\n');doc.add_paragraph(value)
 elif kind=='code':
  story.append(Preformatted(value,styles['Code']));story.append(Spacer(1,10));md.append('```text\n'+value+'\n```\n');doc.add_paragraph(value,style='No Spacing')
 elif kind=='table':
  tableindex+=1;caption,headers,rows=value;label=f'Table {tableindex}. '+caption
  md.append(label+'\n');doc.add_paragraph(label)
  widths=([48]+[96]*5) if len(headers)==6 else [528/len(headers)]*len(headers)
  data=[[Paragraph(html.escape(str(x)),styles['Small']) for x in row] for row in [headers,*rows]]
  tb=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT');tb.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e8edf4')),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,0),.6,colors.HexColor('#7890a8')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f6f8fa')]),('BOTTOMPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),5)]));story.append(KeepTogether([Paragraph(html.escape(label),styles['BodyText']),tb,Spacer(1,14)]))
  md.append('| '+' | '.join(map(str,headers))+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+'\n'.join('| '+' | '.join(map(str,r))+' |' for r in rows)+'\n')
  t=doc.add_table(rows=1,cols=len(headers));t.style='Light Shading Accent 1'
  for cell,text in zip(t.rows[0].cells,headers):cell.text=str(text)
  for row in rows:
   for cell,text in zip(t.add_row().cells,row):cell.text=str(text)
 elif kind=='figure':
  figindex+=1;f=value;caption=f'Figure {figindex}. Experiment {f["exp"]}: {f["metric"].replace("_"," ")}. Source: current results/runs.csv.gz and summary.csv [2].'
  story.append(PageBreak());story.append(Paragraph(html.escape(caption),styles['Heading1']));story.append(Image(str(R/'figures'/f['file']),width=528,height=528*5.2/8.5));story.append(Paragraph('Markers are simulated means; bars are pointwise 95% intervals. No interpolation of simulation points. Fixed settings and units are identified on the plot; full setup is in Section 3.',styles['BodyText']))
  md.append(f'![{caption}](figures/{f["file"]})\n\n{caption}\n');doc.add_page_break();doc.add_picture(str(R/'figures'/f['file']),width=Inches(6.5));doc.add_paragraph(caption)
(R/'REPORT.md').write_text('\n'.join(md));doc.save(R/'Lab_4_Report.docx')
def footer(c,d):
 c.setFont('DejaVu',8);c.setFillColor(colors.HexColor('#555555'));c.drawString(42,27,'4DK4 Lab 4 | Independent comparison and reproducible simulation');c.drawRightString(570,27,str(d.page))
SimpleDocTemplate(str(R/'Lab_4_Report.pdf'),pagesize=(612,792),leftMargin=42,rightMargin=42,topMargin=40,bottomMargin=45,title='4DK4 Lab 4 — Simulation of ARQ Protocols').build(story,onFirstPage=footer,onLaterPages=footer)
print(f'Built Markdown, PDF and DOCX: {tableindex} tables, {figindex} figures.')
