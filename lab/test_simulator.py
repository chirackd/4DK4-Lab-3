#!/usr/bin/env python3
"""Model checks against queueing theory and exact sample-path invariants."""
import csv, math, subprocess
from runtime import build, executable_path
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def run(**kw):
    args=[str(executable_path())]
    for k,v in kw.items(): args += ['--'+k.replace('_','-'),str(v)]
    s=subprocess.check_output(args,text=True).splitlines()
    r=next(csv.DictReader(s[:2])); stations=list(csv.DictReader(s[2:]))
    assert int(r['arrivals'])-int(r['successes'])==int(r['backlog_end'])-int(r['backlog_warm'])
    assert sum(int(x['successes']) for x in stations)==int(r['successes'])
    assert all(float(r[x])>=0 and math.isfinite(float(r[x])) for x in ['throughput','load','delay','collisions'])
    r['_stations']=stations
    return r

def main():
    build()
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
    # These checks exercise the reference report's actual model choices.
    r=run(mode='beb',stations=10,rate=.5,time=300000,warmup=30000,seed=400452897)
    assert int(r['max_beb_exponent'])==10
    assert .47<float(r['throughput'])<.53 and float(r['repeat_fraction'])>.75
    count+=1
    r=run(mode='beb',stations=10,rate=.3,persistent=0,time=300000,warmup=30000,seed=400452897)
    assert float(r['persistent_wait'])==0 and float(r['collisions'])>0
    persistent=r['_stations'][0];others=r['_stations'][1:]
    assert float(persistent['delay'])<10
    assert sum(float(q['delay']) for q in others)/len(others)>100
    count+=1
    # Guard time must reduce the one-station service ceiling, not shorten packets.
    r=run(mode='slotted',stations=1,rate=2,guard=.05,time=100000,warmup=10000,seed=400452897)
    assert abs(float(r['throughput'])-1/1.1)<.0001
    count+=1
    # One outstanding reservation/data packet means at most N in the data stage.
    capacities=[]
    for ratio in [.25,1,5,10]:
        r=run(mode='reservation',stations=10,rate=2,xr=1/ratio,time=200000,warmup=20000,seed=400452897)
        assert int(r['max_data_queue'])<=10
        assert 0<=float(r['data_utilization'])<=1+1e-10
        capacities.append(float(r['data_utilization']));count+=1
    assert all(x<y for x,y in zip(capacities[:2],capacities[1:3])) and capacities[-1]>.99
    # Completion-count stopping has a real denominator and an explicit hard horizon.
    r=run(mode='fixed',stations=1,rate=.2,packets=1000,time=100000,warmup=0,seed=400452897)
    assert int(r['successes'])==1000 and float(r['time'])<100000
    assert abs(float(r['throughput'])-1000/float(r['time']))<1e-9
    count+=1
    # Both the handout's uncapped BEB and prior exponential fixed model remain selectable.
    r=run(mode='beb',stations=10,rate=.4,beb_cap=0,time=100000,warmup=10000,seed=400452897)
    assert int(r['max_beb_exponent'])>10;count+=1
    run(mode='fixed',stations=5,rate=.1,fixed_distribution='exponential',time=10000,warmup=1000,seed=400452897);count+=1
    invalid=subprocess.run([str(executable_path()),'--mode','invalid'],capture_output=True)
    assert invalid.returncode!=0;count+=1
    print(f'PASS: {count} model/reproducibility/overload/argument checks; exact flow conservation in every run')
if __name__=='__main__':main()
