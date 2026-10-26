#!/usr/bin/env python3
from run_experiments import ROOT,run
import csv
from concurrent.futures import ThreadPoolExecutor
CASES=[('fixed',10,5,.08,.1),('fixed',10,10,.18,.1),('fixed',10,20,.25,.1),
       ('beb',10,10,.1,.1),('beb',10,10,.2,.1),('beb',10,10,.4,.1),
       ('slotted',10,10,.2,.1),('slotted',10,10,.4,.1),
       ('reservation',10,10,.3,1),('reservation',10,10,.6,.5),
       ('reservation',10,10,.9,.1),('reservation',10,10,1.,.1)]
jobs=[dict(mode=m,stations=n,backoff=b,rate=r,xr=x,seed=s,time=t,warmup=t*.1)
      for m,n,b,r,x in CASES for t in [300000,1000000,5000000]
      for s in [400452897,333333,222222,44444,987654321]]
if __name__=='__main__':
    with (ROOT/'results/sensitivity.csv').open('w') as f:
        w=None
        with ThreadPoolExecutor(max_workers=4) as pool:
            for i,(row,_) in enumerate(pool.map(run,jobs),1):
                if w is None:w=csv.DictWriter(f,fieldnames=list(row));w.writeheader()
                w.writerow(row)
                if i%30==0: f.flush();print(f'{i}/{len(jobs)}',flush=True)
