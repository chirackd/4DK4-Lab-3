#!/usr/bin/env python3
"""Generate a source-backed report from the current run's CSVs and figures."""
import argparse
from pathlib import Path
import json, textwrap, html
import numpy as np
import pandas as pd
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, Preformatted, PageBreak, KeepTogether
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
ROOT=Path(__file__).resolve().parent
BLOCKS=[]
def h(t,level=1):BLOCKS.append(('heading',(t,level)))
def p(t):BLOCKS.append(('paragraph',t))
def table(headers,rows):BLOCKS.append(('table',(headers,rows)))
def figure(name,caption):BLOCKS.append(('figure',(name,caption)))
def code(s):BLOCKS.append(('code',s))


def compose():
    raw=pd.read_csv(RESULTS/'runs.csv');a=pd.read_csv(RESULTS/'summary.csv')
    fair=pd.read_csv(RESULTS/'fairness.csv');cap=pd.read_csv(RESULTS/'capacity.csv')
    sens=pd.read_csv(RESULTS/'sensitivity_summary.csv')
    manifest=json.loads((RESULTS/'manifest.json').read_text(encoding='utf-8'))
    def point(mode,rate,n=10,persistent=-1,backoff=10):
        q=a[(a['mode']==mode)&(a['stations']==n)&(a['persistent']==persistent)&(a['backoff']==backoff)&np.isclose(a['rate'],rate)]
        if len(q)!=1:raise ValueError(f'Missing or ambiguous report point: {mode}, {rate}, {n}')
        return q.iloc[0]
    def fmt(value):return f'{value:.4g}'
    def estimate(row,metric):
        value=fmt(row[metric]);ci=row[metric+'_ci95']
        return value+(f' ± {fmt(ci)}' if np.isfinite(ci) else ' (one seed; CI unavailable)')
    def fig(name,text):
        nonlocal number
        number+=1;figure(name,f'Figure {number}. '+text)
    number=0
    h('Computer Engineering 4DK4 — Lab 3')
    h('ALOHA Medium Access Control and Packet Reservation',2)
    p('Group members: Daniel Chirackal and Ryan Phiby Mathew. Required student-ID seed: 400452897. All measurements below come from the accompanying current-run CSVs, not from the supplied comparison report.')
    if len(raw['seed'].unique())<2 or manifest['duration']<1000000:
        p('EXPLORATORY / SHORT RUN: these outputs are useful for checking the pipeline, but do not establish reliable long-run lab conclusions. A one-seed run cannot provide a confidence interval.')
    h('1. Baseline interpretation and experimental setup')
    p('COE4DK4_Lab3_Report.docx was parsed as a conceptual model and graph reference. Its fixed-backoff distribution, BEB cap, persistent retry rule, guard-time convention, single-outstanding reservation rule, and treatment of saturation informed the configuration below. Its authors, student seeds, numerical data, plots, and prose are not substituted for this group’s results. Exact numerical agreement is not expected or required.')
    table(['Setting','Current run'],[
        ['Arrivals and buffers','Aggregate Poisson arrivals λ; uniformly selected station; infinite FIFO per station'],
        ['Packet durations','X = 1 for Parts 1–5; independent exponential data durations with mean X = 1 in Part 6'],
        ['Random seeds',', '.join(map(str,sorted(raw['seed'].unique())))],
        ['Main runs',f'{len(raw)} replications, {len(a)} parameter configurations'],
        ['Measurement window',f'Total horizon {manifest["duration"]:g} X; initial {manifest["warmup"]:g} X excluded'],
        ['Fixed backoff','Uniform on [0, 2B), mean B; original supplied C behavior'],
        ['BEB',f'Uniform on [0, 2^min(Nc, cap)); cap = {manifest.get("beb_cap",10)} (0 means uncapped)'],
        ['Persistent station','Station 0 retries immediately after failure; other stations retain unslotted BEB'],
        ['Slotted ALOHA','Payload duration 1; slot duration 1 + 2ε, ε = 0.001; continuous BEB wait then alignment'],
        ['Reservation','One outstanding reservation/data packet per station; integer-minislot BEB; shared FCFS data server'],
        ['Reservation numerical guard','10⁻⁹ X around minislot boundaries; negligible occupancy cost, separate from ε'],
        ['Model profile','report-aligned-v2; no physical-layer capture, losses, propagation delay or retry limit']])
    p('The handout specifies an uncapped BEB range and describes exponential fixed backoff in its introduction. The comparison report deliberately uses the supplied uniform backoff and an Ethernet-like exponent cap of 10. This baseline profile makes that choice explicit; --beb-cap 0 restores uncapped BEB, and --fixed-distribution exponential selects the alternate fixed model. These changes are modeling choices, not graphical corrections.')
    p('The reference report stops runs after a target number of completed packets and discards no warmup. This workflow defaults to fixed simulated time with a 10% warmup. Therefore overload delays and variability will differ numerically. Completion-count stopping is supported by --packets, with --time retained as a hard horizon. No dataset is tuned to the reference coordinates.')
    h('1.1 Measurements and statistical treatment',2)
    p('For measurement time Tm, throughput S = completed data packets / Tm, and direct-ALOHA attempt load G = all transmission starts / Tm. G counts retransmissions and may exceed 1; it is not the union of occupied time. A reservation attempt has duration Xr, so reservation attempted airtime is its attempt rate multiplied by Xr. End-to-end mean delay D averages arrival-to-data-completion times of packets departing in the measurement window. Unfinished packets remain in the backlog and are not counted as completed.')
    p('Reservation capacity is measured separately at λ = 2/X as the exact data-channel busy time intersected with the measurement window, divided by Tm. This utilization is bounded by 1 even when finite-window exponential-service packet counts fluctuate above 1 packet/X. The CSV also retains packet throughput and completed payload-work rate; these quantities are not silently interchanged.')
    p('All runs check arrivals − completions = backlog_end − backlog_warm. Filled markers pass a descriptive per-seed screen: S ≥ 0.97λ and backlog growth ≤ 0.03λ in every seed. Critical or overloaded reservation λ ≥ 1 is excluded. Hollow points fail the screen. Flow balance is not a proof of stationarity or finite mean delay. Delay-versus-throughput comparisons omit nonbalanced points; delay-versus-arrival plots retain them as finite-window overload measurements.')
    p('Points are seed means with two-sided 95% Student-t intervals where at least two independent seeds are available. The default five-seed runs use t(4) = 2.77645. For more than six seeds the implementation conservatively retains the df = 5 critical value rather than inventing narrower intervals. Untruncated numeric interval bounds are saved in the summary CSV. Logarithmic delay plots clip interval portions below the positive axis domain. No piecewise-linear interpolation or fitted smoothing is applied to simulated observations; continuous lines are analytical references only.')
    h('2. Parts 1–2: fixed mean backoff')
    fig('fixed_delay_arrival','Mean delay versus arrival rate, uniform fixed backoff, 10 and 5 stations. Hollow markers indicate flow imbalance and run-length-dependent delay.')
    fig('fixed_throughput_arrival','Throughput versus arrival rate for all six requested fixed means. The operating knee and saturated service plateau depend on N and B.')
    table(['N','Mean backoff B','S at λ = 0.5','D at λ = 0.1'],[[str(n),str(b),estimate(point('fixed',.5,n,backoff=b),'throughput'),estimate(point('fixed',.1,n,backoff=b),'delay')] for n in [10,5] for b in ([5,10,20] if n==10 else [3,5,7])])
    p('At light load packets usually succeed on their first attempt and D approaches one packet time. Collisions and FIFO waiting increase delay with λ. A long retry interval adds latency after a rare collision, but reduces synchronized contention among backlogged stations and supports more delivered traffic before congestion. Short backoff can collapse into a low-service state. Saturated delays depend on the observation horizon and must not be described as finite equilibrium delays.')
    fig('fixed_delay_throughput','Delay versus carried throughput for flow-balanced configurations only. Shorter backoff can give lower delay while longer backoff can support a higher carried load.')
    fig('fixed_throughput_load','Throughput versus aggregate attempt load. Dashed/dotted lines are Poisson-attempt pure/slotted ALOHA benchmarks, not fitted data.')
    p('For independent Poisson attempts the pure-ALOHA vulnerable interval is 2X, giving S = G exp(−2G), maximum 1/(2e). With slot alignment it is X, giving S = G exp(−G), maximum 1/e. Neither peak is a universal bound for these buffered finite-source models. A successful station can immediately send its next queued packet while others back off, making attempt starts correlated. At high load this MAC capture raises S above the conventional Poisson benchmark without physical reception of overlapping packets.')
    h('3. Part 3: capped binary exponential backoff')
    fig('beb_comparison','Capped BEB against all fixed means, flow-balanced points only. The cap is an explicit reference-profile assumption; uncapped behavior remains available separately.')
    u=point('beb',.2);high=point('beb',.5)
    p(f'For N = 10 at λ = 0.2, capped BEB gives D = {estimate(u,"delay")} X and S = {estimate(u,"throughput")}. At λ = 0.5 it gives D = {estimate(high,"delay")} X and S = {estimate(high,"throughput")}. The cap prevents a repeatedly collided packet from waiting for arbitrarily expanding windows. It does not remove contention or guarantee low latency; a well-chosen fixed mean can still have lower delay at moderate carried load.')
    fig('capture_repeat_fraction','Same-station successive-success fraction for fixed mean 10, unslotted BEB and slotted BEB, N = 10. The 1/N line is the independent-success reference.')
    p('Success bursts grow as traffic increases: a station that has succeeded resets its next packet’s collision history, while unsuccessful competitors keep larger windows. This explains high carried throughput together with long delay and short-term unfairness. The measured repeat fraction supplies evidence for capture rather than attributing every departure from the Poisson curve to a coding error.')
    h('4. Part 4: immediate persistent retries')
    fig('persistent_delay','Persistent station delay, other-station delay, and the all-BEB comparison system. Other-station delay pools completed packets within each seed.')
    fig('persistent_throughput','Persistent station and other stations’ per-station throughputs, with the all-BEB baseline.')
    q=fair[(fair['stations']==10)&np.isclose(fair['rate'],.3)].set_index('group')
    p(f'At N = 10 and λ = 0.3, persistent station 0 has D = {estimate(q.loc["Persistent station 0"],"delay")} X, whereas its competitors have pooled D = {estimate(q.loc["Others (persistent system)"],"delay")} X. The station retries at the instant its failed transmission ends, without imposing an extra integer-boundary wait. At low load its sustained throughput remains limited by its own arrival rate λ/N; its advantage is mainly delay.')
    fig('persistent_total_throughput','Total system throughput with and without persistence. Immediate retries help one station but reduce high-load total service.')
    p('The persistent station disrupts competitors’ attempts and pushes them into larger retry windows. Under high offered traffic they fall below their fair offered share, and total throughput can decline even as offered traffic grows. Comparing only station 0 would conceal this system cost, so the plots retain both per-station and aggregate comparisons.')
    h('5. Part 5: slotted ALOHA')
    fig('slotted_delay_throughput','Slotted and unslotted capped BEB, flow-balanced delay points only. The payload remains X = 1; guard time extends the slot to 1.002 X.')
    fig('slotted_throughput_arrival','Slotted and unslotted BEB delivered traffic versus new offered traffic.')
    slot=point('slotted',.2)
    p(f'For N = 10 at λ = 0.2, slot alignment gives D = {estimate(slot,"delay")} X, compared with {estimate(u,"delay")} X without slots. Alignment removes partial overlaps between adjacent slots, reducing the vulnerable period. At extremely light load there is an alignment wait of about half a slot. Guard time is actual overhead: the fully backlogged one-station service ceiling is 1/(1 + 2ε), not 1 obtained by shortening the payload.')
    fig('slotted_throughput_load','Attempt-load comparison with the pure and slotted Poisson analytical curves. Finite-source BEB capture can exceed their conventional peaks.')
    h('6. Part 6: reservation and collision-free FCFS data')
    fig('reservation_delay','End-to-end delay versus offered rate. Left: N = 10 and six X/Xr ratios. Right: X/Xr = 10 for N = 5, 10, 20. The dashed M/M/1 curve is a limiting reference.')
    p('The station’s FIFO head remains there through reservation and data completion; its successor cannot reserve early. A second, independent link is used for the shared FCFS data queue so retaining the station head cannot corrupt either queue. This bounds the total number of reserved/in-service packets by N. Reservation and data channels still operate concurrently across different stations.')
    p('Small X/Xr makes the reservation channel the bottleneck, so delay increases sharply at a comparatively low λ. Large X/Xr makes reservations cheap and the exponential data server dominates. As Xr tends to zero, D approaches the M/M/1 expression X/(1 − λX) under the stated traffic model. At light load the reservation adds approximately Xr/2 for boundary alignment plus Xr for the successful minislot.')
    fig('reservation_throughput','Delivered data packet rate versus λ for N = 10. Reservation-limited configurations plateau earlier.')
    fig('reservation_capacity','Data-channel busy fraction under overload λ = 2/X, for 5, 10 and 20 stations across a broad ratio range. The upper bound is 1.')
    table(['X/Xr','Capacity N = 5','Capacity N = 10','Capacity N = 20'],[[fmt(r)]+[estimate(cap[(cap['stations']==n)&np.isclose(cap['ratio'],r)].iloc[0],'data_utilization') for n in [5,10,20]] for r in [.25,.5,1,2,3,4,5,10,100]])
    p('Capacity increases with packet/minislot ratio and approaches a fully busy data server. For long minislots, additional stations create more reservation contention; when minislots are short, more outstanding stations can keep the data server supplied. The Poisson minislot benchmark 1/e is not a universal finite-source BEB bound. Capacity here is measured at a specified overload rate, not inferred by taking the largest throughput from an arbitrary delay sweep.')
    h('7. Reliability, validation and limitations')
    fig('accuracy_runlength','Seed intervals and run-length sensitivity for selected BEB and reservation points. A short run can miss rare contention or critical-load backlog behavior.')
    table(['Mode','λ','X/Xr','Horizon / X','Mean delay / X'],[[row['mode'],fmt(row['rate']),fmt(1/row['xr']),fmt(row['time']),estimate(row,'delay')] for _,row in sens[(sens['mode']=='reservation')&np.isclose(sens['rate'],1)].iterrows()])
    p('The critical data load λ = 1 is not a stable finite-delay operating point, even if its packet completion rate looks close to one. Queues can grow while completed-packet means exclude the oldest unfinished packets. Statistical intervals across independent seeds characterize this finite-window estimator; they do not prove equilibrium. Near the fixed-backoff knee, occasional collapse can widen seed variability considerably.')
    p('The simulator test suite exercises queueing-theory limits, deterministic reruns, exact packet conservation, the capped and uncapped paths, immediate persistent waiting, slot overhead, the N-packet reservation bound, capacity ordering, and completion-count stopping. Integration tests cover native builds in paths with spaces, per-part exports, and missing compilers. Seven broad trend checks compare relative behavior rather than exact coordinates; they do not alter observations. Windows random-number sequences may differ because Simlib uses libc rand().')
    if (RESULTS/'trend_validation.json').exists():
        trends=json.loads((RESULTS/'trend_validation.json').read_text(encoding='utf-8'))
        table(['Conceptual check','Outcome'],[[check['check'],'PASS' if check['passed'] else 'FAIL'] for check in trends['checks']])
    p('Remaining model limitations are ideal zero propagation/feedback delay, infinite buffers, no PHY errors, and the explicit exponent-cap design choice. The comparison report used a different run-stopping rule and different seeds. Its numerical values should not be treated as golden test outputs. The current default reproduces its conceptual trends, while alternative assumptions are selectable and labeled.')
    h('8. Reproduce the current graphs and report')
    code('.\\setup.ps1\n.\\run_all.ps1\n# One experiment:\n.\\exp3\\run_exp3.ps1')
    p('The full native PowerShell workflow runs all experiments, sensitivity, plot generation, conceptual checks, and this data-driven report. Fresh artifacts are under output/. A short --quick / -Quick run is explicitly exploratory. Use a separate output directory to preserve earlier runs. --packets is available on the C CLI and Python experiment runner for completion-target experiments; --time always remains a safety horizon.')
    table(['Artifact','Evidence'],[['results/runs.csv; stations.csv','Independent raw replications and station outcomes'],['results/summary.csv; fairness.csv; capacity.csv','Every plotted mean and untruncated confidence interval'],['results/sensitivity.csv; sensitivity_summary.csv','Run-length variation'],['results/trend_validation.json','Broad conceptual trend observations'],['figures/','16 figures, PNG and vector PDF'],['docs/reference_alignment.md','Source interpretation, changes and differences from the comparison report']])
    h('Appendix. Current simulation driver')
    p('The full added driver follows; the supplied Simlib source is unchanged. The source file, not typographic line wrapping, is authoritative.')
    code((ROOT/'simulator.c').read_text(encoding='utf-8'))


def render():
    md=[]
    for kind,v in BLOCKS:
        if kind=='heading':md.append('#'*v[1]+' '+v[0])
        elif kind=='paragraph':md.append(v)
        elif kind=='figure':md.append(f'![{v[1]}](figures/{v[0]}.png)\n\n{v[1]}')
        elif kind=='code':md.append('```\n'+v.rstrip()+'\n```')
        elif kind=='table':
            heads,rows=v;md.append('| '+' | '.join(heads)+' |\n| '+' | '.join(['---']*len(heads))+' |\n'+'\n'.join('| '+' | '.join(map(str,row))+' |' for row in rows))
    (DEST/'REPORT.md').write_text('\n\n'.join(md)+'\n', encoding='utf-8')
    import os, tempfile
    os.environ.setdefault("MPLCONFIGDIR", os.path.join(tempfile.gettempdir(), "lab3-matplotlib"))
    from matplotlib import get_data_path
    fontdir=Path(get_data_path())/'fonts'/'ttf'
    for name,fn in [('DejaVu','DejaVuSans.ttf'),('DejaVu-Bold','DejaVuSans-Bold.ttf'),('DejaVuMono','DejaVuSansMono.ttf')]:
        pdfmetrics.registerFont(TTFont(name,str(fontdir/fn)))
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='BodyLab',fontName='DejaVu',fontSize=9.5,leading=14,spaceAfter=8))
    styles.add(ParagraphStyle(name='H1Lab',fontName='DejaVu-Bold',fontSize=15,leading=20,spaceBefore=14,spaceAfter=9,keepWithNext=True))
    styles.add(ParagraphStyle(name='H2Lab',fontName='DejaVu-Bold',fontSize=11,leading=15,spaceBefore=10,spaceAfter=7,keepWithNext=True))
    styles.add(ParagraphStyle(name='CaptionLab',fontName='DejaVu',fontSize=8,leading=11,spaceAfter=12))
    styles.add(ParagraphStyle(name='CellLab',fontName='DejaVu',fontSize=7.7,leading=10))
    styles.add(ParagraphStyle(name='CodeLab',fontName='DejaVuMono',fontSize=7,leading=9,spaceAfter=0))
    width=A4[0]-80
    doc=SimpleDocTemplate(str(DEST/'Lab_3_Report.pdf'),pagesize=A4,rightMargin=40,leftMargin=40,topMargin=40,bottomMargin=42,title='4DK4 Lab 3 — ALOHA and Packet Reservation',author='Daniel Chirackal; Ryan Phiby Mathew')
    story=[]
    for kind,v in BLOCKS:
        if kind=='heading':story.append(Paragraph(html.escape(v[0]),styles['H1Lab' if v[1]==1 else 'H2Lab']))
        elif kind=='paragraph':story.append(Paragraph(html.escape(v),styles['BodyLab']))
        elif kind=='figure':
            img=Image(str(FIGURES/f'{v[0]}.png'));img.drawHeight=width*img.imageHeight/img.imageWidth;img.drawWidth=width
            items=[img,Paragraph(html.escape(v[1]),styles['CaptionLab'])]
            if story and isinstance(story[-1],Paragraph) and story[-1].style.name in ['H1Lab','H2Lab']:
                items.insert(0,story.pop())
            story.append(KeepTogether(items))
        elif kind=='table':
            heads,rows=v;n=len(heads)
            if n==2:widths=[width*.28,width*.72]
            else:widths=[width/n]*n
            data=[[Paragraph(html.escape(str(c)),styles['CellLab']) for c in row] for row in [heads]+rows]
            t=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT')
            t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e9eef3')),('LINEBELOW',(0,0),(-1,0),.7,colors.HexColor('#516579')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),('LINEBELOW',(0,1),(-1,-1),.25,colors.HexColor('#d7dce0'))]))
            story.extend([t,Spacer(1,10)])
        elif kind=='code':
            for line in v.splitlines():
                # Individual line flowables allow appendix to paginate cleanly.
                wrapped=textwrap.wrap(line,width=118,replace_whitespace=False,drop_whitespace=False,subsequent_indent='    ') or ['']
                story.append(Preformatted('\n'.join(wrapped),styles['CodeLab'],dedent=0))
        elif kind=='page':story.append(PageBreak())
    def footer(c,d):
        c.setFont('DejaVu',7);c.setFillColor(colors.HexColor('#5c6770'));c.drawString(40,24,'4DK4 Lab 3 | Simulation results and reproducible implementation');c.drawRightString(A4[0]-40,24,str(d.page))
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    print('Built REPORT.md and Lab_3_Report.pdf')
def main():
    global RESULTS, FIGURES, DEST
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results-dir',type=Path,default=ROOT.parent/'output/results')
    parser.add_argument('--figures-dir',type=Path,default=ROOT.parent/'output/figures')
    parser.add_argument('--output-dir',type=Path,default=ROOT.parent/'output')
    args=parser.parse_args();RESULTS=args.results_dir;FIGURES=args.figures_dir;DEST=args.output_dir
    DEST.mkdir(parents=True,exist_ok=True)
    compose();render()

if __name__=='__main__':main()
