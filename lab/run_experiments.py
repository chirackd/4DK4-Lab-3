#!/usr/bin/env python3
"""Reproducible independent replications; raw per-run and per-station CSVs."""
import argparse, csv, json, subprocess, time
from contextlib import ExitStack
from runtime import build, executable_path
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
ROOT=Path(__file__).resolve().parent

def run(job):
    args=[str(executable_path())]
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

def experiments_for(row):
    if row['mode'] == 'fixed': return (1, 2)
    if row['mode'] == 'reservation': return (6,)
    if row['mode'] == 'slotted': return (5,)
    return (4,) if int(row.get('persistent', -1)) == 0 else (3,)


def write_results(todo, output, workers, experiment=None):
    """Each requested experiment gets its own CSV and Lab-2-style text output."""
    output = Path(output).resolve()
    with ExitStack() as stack:
        writers = {}
        def emit(folder, row, stations, text=False):
            if folder not in writers:
                folder.mkdir(parents=True, exist_ok=True)
                f = stack.enter_context((folder / 'runs.csv').open('w', newline='', encoding='utf-8'))
                sf = stack.enter_context((folder / 'stations.csv').open('w', newline='', encoding='utf-8'))
                rw = csv.DictWriter(f, fieldnames=list(row)); rw.writeheader()
                sw = csv.DictWriter(sf, fieldnames=list(stations[0])); sw.writeheader()
                tf = stack.enter_context((folder / f'{folder.name}_results.txt').open('w', encoding='utf-8')) if text else None
                writers[folder] = rw, sw, tf
            rw, sw, tf = writers[folder]
            rw.writerow(row); sw.writerows(stations)
            if tf:
                tf.write(' '.join(f'{k}={v}' for k,v in row.items()) + '\n')
        start = time.time()
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for i,(row,stations) in enumerate(pool.map(run,todo),1):
                if experiment is None: emit(output / 'results', row, stations)
                for number in experiments_for(row):
                    if experiment is None or number == experiment:
                        emit(output / f'exp{number}', row, stations, text=True)
                if i % 100 == 0 or i == len(todo):
                    print(f'{i}/{len(todo)} replications; {time.time()-start:.1f}s', flush=True)
    return time.time() - start


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--time', type=float, default=1000000)
    p.add_argument('--seeds', nargs='+', type=int, default=[400452897,333333,222222,44444,987654321])
    p.add_argument('--workers', type=int, default=4)
    p.add_argument('--experiment', type=int, choices=range(1,7))
    p.add_argument('--output', type=Path, default=ROOT.parent/'output')
    a=p.parse_args()
    if a.time <= 0 or a.workers < 1: p.error('--time and --workers must be positive')
    build()
    todo=list(jobs(a.seeds,a.time))
    if a.experiment is not None:
        todo=[j for j in todo if a.experiment in experiments_for(j)]
    elapsed=write_results(todo,a.output,a.workers,a.experiment)
    metadata={
        'seeds':a.seeds,'duration':a.time,'warmup':a.time*.1,
        'replications':len(todo),'experiment':a.experiment,'elapsed_seconds':elapsed,
        'rng':'Simlib libc rand(); sequences can differ across platforms'
    }
    folders=[(a.output/'results', None)] if a.experiment is None else []
    folders += [(a.output/f'exp{n}', n) for n in (range(1,7) if a.experiment is None else [a.experiment])]
    for folder, number in folders:
        count=len(todo) if number is None else sum(number in experiments_for(j) for j in todo)
        (folder/'manifest.json').write_text(json.dumps(
            dict(metadata, experiment=number, replications=count), indent=2), encoding='utf-8')
    print(f'Results saved to {a.output.resolve()}')

if __name__=='__main__': main()
