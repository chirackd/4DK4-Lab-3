#!/usr/bin/env python3
"""Model checks against queueing theory and exact sample-path invariants."""
import csv, io, math, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def run(**kw):
    args=[str(ROOT/'simulator')]
    for k,v in kw.items(): args += ['--'+k.replace('_','-'),str(v)]
    s=subprocess.check_output(args,text=True).splitlines()
    r=next(csv.DictReader(s[:2])); stations=list(csv.DictReader(s[2:]))
    assert int(r['arrivals'])-int(r['successes'])==int(r['backlog_end'])-int(r['backlog_warm'])
    assert sum(int(x['successes']) for x in stations)==int(r['successes'])
    assert all(float(r[x])>=0 and math.isfinite(float(r[x])) for x in ['throughput','load','delay','collisions'])
    return r

def main():
    count=0
    for mode in ['fixed','beb','slotted','reservation']:
        for n in [1,5,10]:
            r=run(mode=mode,stations=n,rate=.2,time=300000,warmup=30000,seed=400452897)
            if n==1 and mode in ['fixed','beb','slotted']:
                expected=(1.5 if mode=='slotted' else 1)+.2/(2*(1-.2))
                assert abs(float(r['delay'])-expected)<.025,(mode,r['delay'],expected)
                assert abs(float(r['throughput'])-.2)<.005
                assert float(r['collisions'])==0
            count+=1
    a=run(mode='beb',stations=10,persistent=0,rate=.3,time=100000,warmup=10000,seed=1234)
    b=run(mode='beb',stations=10,persistent=0,rate=.3,time=100000,warmup=10000,seed=1234)
    assert a==b;count+=1
    # Tiny minislots approach an M/M/1 data queue, D=1/(1-lambda).
    r=run(mode='reservation',stations=10,xr=.0001,rate=.2,time=1000000,warmup=100000,seed=400452897)
    assert abs(float(r['delay'])-1.25)<.03,r['delay'];count+=1
    for mode in ['fixed','beb','slotted','reservation']:
        run(mode=mode,stations=10,rate=1.2,time=10000,warmup=1000,seed=1234);count+=1
    invalid=subprocess.run([str(ROOT/'simulator'),'--mode','invalid'],capture_output=True)
    assert invalid.returncode!=0;count+=1
    print(f'PASS: {count} model/reproducibility/overload/argument checks; exact flow conservation in every run')
if __name__=='__main__':main()
