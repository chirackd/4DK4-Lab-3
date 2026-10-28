#!/usr/bin/env python3
"""Check broad conceptual trends, never exact reference-report coordinates."""
import argparse
import json
from pathlib import Path
import pandas as pd


def validate(results):
    a=pd.read_csv(results/'summary.csv');f=pd.read_csv(results/'fairness.csv');cap=pd.read_csv(results/'capacity.csv')
    def point(mode,rate,n=10,persistent=-1,backoff=10):
        q=a[(a['mode']==mode)&(a['stations']==n)&(a['persistent']==persistent)&(a['backoff']==backoff)&((a['rate']-rate).abs()<1e-8)]
        if len(q)!=1:raise ValueError(f'Missing or ambiguous configuration: {mode}, {rate}, {n}')
        return q.iloc[0]
    checks=[]
    def record(name,condition,observed):checks.append({'check':name,'passed':bool(condition),'observed':observed})
    fixed=[float(point('fixed',.5,backoff=b)['throughput']) for b in [5,10,20]]
    record('Longer fixed backoff raises the congested-state throughput',fixed[0]<fixed[1]<fixed[2],dict(zip(['b5','b10','b20'],fixed)))
    beb=point('beb',.5)
    record('Capped BEB carries moderate load beyond the fixed-backoff ceiling',beb['throughput']>.45 and beb['throughput']>fixed[-1],{'beb_S':float(beb['throughput']),'lambda':.5})
    low=point('beb',.1)
    record('BEB same-station success bursts increase with offered traffic',beb['repeat_fraction']>low['repeat_fraction'],{'low':float(low['repeat_fraction']),'high':float(beb['repeat_fraction'])})
    unfair=point('beb',1.5,persistent=0);fair=point('beb',1.5)
    record('Immediate persistent retries reduce total high-load throughput',unfair['throughput']<fair['throughput'],{'persistent':float(unfair['throughput']),'all_beb':float(fair['throughput'])})
    groups=f[(f['stations']==10)&((f['rate']-.3).abs()<1e-8)].set_index('group')
    pd0=float(groups.loc['Persistent station 0','delay']);other=float(groups.loc['Others (persistent system)','delay'])
    record('Persistent station has lower delay than competing stations',pd0<other,{'persistent_D':pd0,'others_D':other})
    u=point('beb',.2);s=point('slotted',.2)
    record('Slot alignment reduces moderate-load BEB delay',s['delay']<u['delay'],{'slotted_D':float(s['delay']),'unslotted_D':float(u['delay'])})
    c=cap[cap['stations']==10].set_index('ratio')
    values=[float(c.loc[r,'data_utilization']) for r in [.25,1,5,10]]
    record('Reservation capacity rises and approaches the data-channel ceiling',values[0]<values[1]<values[2] and values[-1]>.97,dict(zip(['ratio_.25','ratio_1','ratio_5','ratio_10'],values)))
    result={'method':'Broad qualitative comparisons on independently simulated data; not fitted to supplied report values','checks':checks,'passed':all(c['passed'] for c in checks)}
    (results/'trend_validation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    for check in checks:print(('PASS' if check['passed'] else 'FAIL')+': '+check['check'])
    if not result['passed']:raise AssertionError('A conceptual trend check failed; inspect trend_validation.json rather than altering plotted data.')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--results-dir',type=Path,default=Path(__file__).resolve().parents[1]/'output/results')
    validate(p.parse_args().results_dir)
