#!/usr/bin/env python3
"""Reproducible independent replications; raw per-run and per-station CSVs."""
import argparse, csv, io, json, os, subprocess, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
ROOT=Path(__file__).resolve().parent

def run(job):
    args=[str(ROOT/'simulator')]
    for k,v in job.items(): args.extend(['--'+k,str(v)])
    out=subprocess.run(args,check=True,text=True,capture_output=True).stdout.splitlines()
    row=next(csv.DictReader(out[:2]))
    stations=[dict(row,**{'station_'+k:v for k,v in x.items()}) for x in csv.DictReader(out[2:])]
    # Exact sample-path accounting over the measurement interval.
    assert int(row['arrivals'])-int(row['successes']) == int(row['backlog_end'])-int(row['backlog_warm']),row
    assert sum(int(x['station_successes']) for x in stations)==int(row['successes'])
    assert float(row['throughput']) <= float(row['load'])+1e-4
    return row,stations

def jobs(seeds,duration):
    base={'time':duration,'warmup':duration*.1}
    rates=[.02,.05,.08,.10,.12,.14,.16,.18,.20,.22,.25,.28,.32,.36,.40,.50,.65,.80]
    for n,backs in [(10,[5,10,20]),(5,[3,5,7])]:
        for b in backs:
            for r in rates:
                for seed in seeds: yield dict(base,mode='fixed',stations=n,backoff=b,rate=r,seed=seed)
    for mode in ['beb','slotted']:
        for n in [5,10]:
            for r in rates:
                for seed in seeds: yield dict(base,mode=mode,stations=n,rate=r,seed=seed)
    for n in [5,10]:
        for r in [.05,.10,.15,.20,.25,.30,.40,.50,.65,.80]:
            for seed in seeds: yield dict(base,mode='beb',stations=n,rate=r,seed=seed,persistent=0)
    for ratio in [1,2,5,10,20,50]:
        for r in sorted(set([.05,.10,.20,.30,.40,.50,.60,.70,.80,.90,1.,1.1,1.25] + ([.24,.26,.28,.32,.34,.36,.38] if ratio==1 else [.52,.54,.56,.58,.62,.64,.66,.68] if ratio==2 else [.94,.98,1.02]))):
            for seed in seeds: yield dict(base,mode='reservation',stations=10,xr=1/ratio,rate=r,seed=seed)

def main():
    p=argparse.ArgumentParser();p.add_argument('--time',type=float,default=1000000)
    p.add_argument('--seeds',nargs='+',type=int,default=[400452897,333333,222222,44444,987654321]);p.add_argument('--workers',type=int,default=4)
    a=p.parse_args();subprocess.run(['make','-C',str(ROOT)],check=True)
    todo=list(jobs(a.seeds,a.time)); start=time.time(); ROOT.joinpath('results').mkdir(exist_ok=True)
    with (ROOT/'results/runs.csv').open('w') as f,(ROOT/'results/stations.csv').open('w') as sf:
        rw=sw=None
        with ThreadPoolExecutor(max_workers=a.workers) as pool:
            for i,(row,stations) in enumerate(pool.map(run,todo),1):
                if rw is None:
                    rw=csv.DictWriter(f,fieldnames=list(row));rw.writeheader()
                    sw=csv.DictWriter(sf,fieldnames=list(stations[0]));sw.writeheader()
                rw.writerow(row);sw.writerows(stations)
                if i%100==0: f.flush();sf.flush();print(f'{i}/{len(todo)} replications; {time.time()-start:.1f}s',flush=True)
    (ROOT/'results/manifest.json').write_text(json.dumps({'seeds':a.seeds,'duration':a.time,'warmup':a.time*.1,'replications':len(todo),'elapsed_seconds':time.time()-start},indent=2))
if __name__=='__main__': main()
