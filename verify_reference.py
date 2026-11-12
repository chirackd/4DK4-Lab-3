#!/usr/bin/env python3
"""Matched model comparisons and independent analytical checks; no reference code imported."""
import os,json,math,subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import pandas as pd
from run import ROOT,EXE,SEEDS,simulate
rows=[]
def call(ws,wr,pd_,pa=0,tout=15,variant='default',duration=1010000):
 env=os.environ.copy()
 for name in ['ARQ_LEGACY','ARQ_INDIVIDUAL','ARQ_CUMULATIVE_ONLY']:env.pop(name,None)
 flag={'legacy':'ARQ_LEGACY','individual':'ARQ_INDIVIDUAL','cumulative':'ARQ_CUMULATIVE_ONLY'}.get(variant)
 if flag:env[flag]='1'
 result=[]
 for seed in SEEDS:
  out=subprocess.check_output([str(EXE),*map(str,[ws,wr,pd_,pa,tout,seed,duration,10000,0,0])],env=env,text=True)
  v=list(map(float,out.split('RESULT,')[-1].split(',')))
  row=dict(ws=ws,wr=wr,pd=pd_,pa=pa,tout=tout,variant=variant,duration=duration,seed=seed,efficiency=v[0],attempts_per_delivery=v[1])
  result.append(row)
 return result
jobs=[(64,1,.1,0,15,v) for v in ['default','legacy','individual']]
jobs += [(64,1,.1,p,15,v) for p in [.1,.9] for v in ['default','legacy','individual']]
jobs += [(64,64,.1,0,15,v) for v in ['default','cumulative']]
jobs += [(64,8,.1,.1,15,v) for v in ['default','individual']]
jobs += [(64,8,.1,0,15,'default'),(32,64,.1,0,15,'default')]
jobs += [(1,1,.1,.1,t,'default') for t in [2,10.99,11,11.01,11.5,12]]
jobs += [(11,1,.1,0,11,'default')]
with ThreadPoolExecutor(max_workers=6) as p:
 for result in p.map(lambda args:call(*args),jobs):rows.extend(result)
a=pd.DataFrame(rows);a.to_csv(ROOT/'results/model_comparisons.csv',index=False)
keys=['ws','wr','pd','pa','tout','variant','duration']
def summarize(a,keys):
 out=[]
 for key,g in a.groupby(keys):
  d=dict(zip(keys,key))
  for m in ['efficiency','attempts_per_delivery']:
   d[m]=g[m].mean();d[m+'_ci95']=2.776445105*g[m].std(ddof=1)/math.sqrt(len(g))
  out.append(d)
 return pd.DataFrame(out)
b=summarize(a,keys);b.to_csv(ROOT/'results/model_comparison_summary.csv',index=False)
# Reproduce source claims at their stated parameters; values are reported, rounded,
# and not treated as ground truth or as tests our code must be fitted to pass.
reference=[(64,1,.1,0,15,.375),(64,8,.1,0,15,.608),(64,64,.1,0,15,.900),(64,1,.1,.1,15,.376),(64,8,.1,.1,15,.597),(64,64,.1,0,15,.900),(11,1,.1,0,11,.4505),(1,1,.1,.1,11.01,.0736),(1,1,.1,.1,11.5,.0730),(1,1,.1,.1,2,.0872)]
refs=[]
for ws,wr,pd_,pa,tout,reported in reference:
 g=b[(b.ws==ws)&(b.wr==wr)&(b.pd==pd_)&(b.pa==pa)&(b.tout==tout)&(b.variant=='default')].iloc[0]
 refs.append(dict(ws=ws,wr=wr,pd=pd_,pa=pa,tout=tout,reference_efficiency=reported,measured_efficiency=g.efficiency,ci95=g.efficiency_ci95,difference=g.efficiency-reported))
pd.DataFrame(refs).drop_duplicates().to_csv(ROOT/'results/reference_comparison.csv',index=False)
checks=[]
def check(name,observed,expected,tolerance):
 assert abs(observed-expected)<=tolerance,(name,observed,expected,tolerance)
 checks.append(dict(check=name,observed=observed,expected=expected,tolerance=tolerance))
for ws,wr,pd_,pa,tout in [(64,1,.1,0,15),(11,1,.1,0,11),(64,64,.1,0,15)]:
 g=b[(b.ws==ws)&(b.wr==wr)&(b.pd==pd_)&(b.pa==pa)&(b.tout==tout)&(b.variant=='default')].iloc[0]
 expected=(1-pd_)/(1+(tout-1)*pd_) if wr==1 else 1-pd_
 check(f'Analytical packet-error reference Ws={ws} Wr={wr} T={tout}',g.efficiency,expected,max(.003,g.efficiency_ci95*2))
for t in [11,11.01,11.5,12]:
 g=b[(b.ws==1)&(b.tout==t)].iloc[0];q=.81;check(f'SW renewal T={t}',g.efficiency,q/(11*q+t*(1-q)),max(.0005,g.efficiency_ci95*2))
# Exact time-boundary regression with zero errors: T=11 must not retry.
for ws,wr in [(1,1),(11,1),(11,16)]:
 r,_=simulate(ws,wr,tout=11,n=100,warm=0,duration=100000)
 check(f'ACK wins exact timeout tie Ws={ws} Wr={wr}',r['attempts'],100,0)
 check(f'Exact finite time at T=11 Ws={ws} Wr={wr}',r['completion_ms'],1100 if ws==1 else 110,1e-8)
# Original report's claim of integer-only dependence is false for S&W:
# expected renewal time varies continuously for all T>=11.
r11=b[(b.ws==1)&(b.tout==11.01)].efficiency.iloc[0];r15=b[(b.ws==1)&(b.tout==11.5)].efficiency.iloc[0]
assert r11>r15
pd.DataFrame(checks).to_csv(ROOT/'results/analytical_checks.csv',index=False)
print(b.to_string(index=False));print('Passed',len(checks),'additional analytical/boundary checks.')
