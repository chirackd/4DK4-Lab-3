#!/usr/bin/env python3
"""Run the twelve run-length sensitivity cases using the native simulator."""
import argparse
import csv
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from run_experiments import ROOT, run
from runtime import build

CASES=[('fixed',10,5,.08,.1),('fixed',10,10,.18,.1),('fixed',10,20,.25,.1),
       ('beb',10,10,.1,.1),('beb',10,10,.2,.1),('beb',10,10,.4,.1),
       ('slotted',10,10,.2,.1),('slotted',10,10,.4,.1),
       ('reservation',10,10,.3,1),('reservation',10,10,.6,.5),
       ('reservation',10,10,.9,.1),('reservation',10,10,1.,.1)]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, default=ROOT.parent/'output')
    p.add_argument('--times', type=float, nargs='+', default=[300000,1000000,5000000])
    p.add_argument('--seeds', type=int, nargs='+', default=[400452897,333333,222222,44444,987654321])
    p.add_argument('--workers', type=int, default=4)
    a=p.parse_args()
    if any(t<=0 for t in a.times) or a.workers<1:p.error('times and workers must be positive')
    build()
    jobs=[dict(mode=m,stations=n,backoff=b,rate=r,xr=x,seed=s,time=t,warmup=t*.1)
          for m,n,b,r,x in CASES for t in a.times for s in a.seeds]
    folder=a.output/'results';folder.mkdir(parents=True, exist_ok=True)
    with (folder/'sensitivity.csv').open('w', newline='', encoding='utf-8') as f:
        w=None
        with ThreadPoolExecutor(max_workers=a.workers) as pool:
            for i,(row,_) in enumerate(pool.map(run,jobs),1):
                if w is None:w=csv.DictWriter(f,fieldnames=list(row));w.writeheader()
                w.writerow(row)
                if i%30==0 or i==len(jobs): f.flush();print(f'{i}/{len(jobs)} sensitivity replications',flush=True)

if __name__=='__main__': main()
