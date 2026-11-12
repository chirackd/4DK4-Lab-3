#!/usr/bin/env python3
"""Compile, validate, run the seven lab experiments, and plot measured points."""
import argparse, csv, itertools, json, math, os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
ROOT=Path(__file__).resolve().parent
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'.mplcache'))
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
SEEDS=[400452897,333333,2026,104729,8675309]
WS=[1,2,4,6,8,10,11,12,16,24,32,48,64]
PROFILES=[('S&W',1),('GBN',1),('SR Wr=4',4),('SR Wr=16',16),('SR Wr=64',64)]
EXE=ROOT/('arq.exe' if os.name=='nt' else 'arq')

def simulate(ws,wr,pd=0,pa=0,tout=15,seed=400452897,duration=1010000,warm=10000,n=0,trace=0):
    args=[ws,wr,pd,pa,tout,seed,duration,warm,n,trace]
    s=subprocess.check_output([str(EXE),*map(str,args)],text=True)
    vals=list(map(float,s.split('RESULT,')[-1].strip().split(',')))
    return dict(zip(['efficiency','attempts_per_delivery','completion_ms','attempts','delivered'],vals)),s

def validate():
    checks=[]
    for ws in WS:
        for wr in [1,4,16,64]:
            r,_=simulate(ws,wr)
            assert abs(r['efficiency']-min(1,ws/11))<2e-4,(ws,wr,r)
            for n in [1,10,100,1000]:
                r,_=simulate(ws,wr,n=n,warm=0,duration=1000000)
                expected=n+10 if ws>=11 else ((n-1)//ws)*11+(n-1)%ws+11
                assert abs(r['completion_ms']-expected)<1e-6,(ws,wr,n,r,expected)
                assert r['attempts']==r['delivered']==n
    checks.append('260 error-free throughput and finite-transfer analytical comparisons passed.')
    for pd_,pa in [(.2,0),(0,.2),(.2,.2),(.5,.5)]:
        vals=[simulate(1,1,pd_,pa,seed=s,duration=1010000)[0] for s in SEEDS]
        q=(1-pd_)*(1-pa);expected=q/(11*q+15*(1-q))
        mean=np.mean([r['efficiency'] for r in vals])
        assert abs(mean-expected)<.001,(mean,expected)
        checks.append(f'S&W pd={pd_}, pa={pa}: measured {mean:.6f}, renewal analysis {expected:.6f}.')
    traces=ROOT/'results'/'traces';traces.mkdir(parents=True,exist_ok=True)
    for label,ws,wr in [('SW',1,1),('GBN',12,1),('SR',12,16)]:
        for p in [0,.5]:
            _,s=simulate(ws,wr,p,p,n=12,warm=0,duration=1000000,trace=1)
            (traces/f'{label}_pd_pa_{p}.txt').write_text(s)
            if p: assert 'DATA lost' in s and 'ACK lost' in s and 'TIMEOUT' in s
    (ROOT/'results'/'validation.txt').write_text('\n'.join(checks)+'\n')
    return checks

def configs(exp):
    out=[]
    def add(part,xname,xs,pd=0,pa=0,tout=15,n=0,wsfixed=64):
        for x in xs:
            for label,wr in PROFILES:
                ws=1 if label=='S&W' else (int(x) if xname=='ws' else wsfixed)
                kw=dict(ws=ws,wr=wr,pd=pd,pa=pa,tout=tout,n=n)
                if xname!='ws':kw[xname]=x
                for seed in (SEEDS if not n else [400452897+i*104729 for i in range(100)]):
                    out.append(dict(exp=part,profile=label,xname=xname,x=x,seed=seed,**kw))
    if exp in [0,2]:add('2','ws',WS)
    if exp in [0,3]:
        add('3a','pd',[0,.01,.025,.05,.1,.2,.3,.4,.5])
        add('3b','ws',WS,pd=.1)
    if exp in [0,4]:add('4','pa',[0,.01,.025,.05,.1,.2,.3,.4,.5,.7,.9],pd=.1)
    if exp in [0,5]:add('5','tout',[2,5,8,10,10.99,11,11.01,11.5,12,15,20,30,50,75,100],pd=.1,pa=.1)
    if exp in [0,6]:
        for pd_,pa in [(0,0),(.05,0),(.05,.05)]: add(f'6_pd{pd_}_pa{pa}','ws',WS,pd=pd_,pa=pa,n=100)
    if exp in [0,7]:
        for n in [10,1000]:
            for pd_,pa in [(0,0),(.05,0),(.05,.05)]:add(f'7_N{n}_pd{pd_}_pa{pa}','ws',[1,4,8,11,16,32,64],pd=pd_,pa=pa,n=n)
    # Avoid rerunning identical S&W and deterministic finite runs, but expand rows afterward.
    return out

def run_one(c):
    kw={k:c[k] for k in ['ws','wr','pd','pa','tout','n','seed']}
    r,_=simulate(**kw,warm=0 if c['n'] else 10000,duration=10000000 if c['n'] else 1010000)
    if c['n']: assert r['delivered']==c['n'] and r['attempts']>=c['n']
    return {**c,**r}

def plots(raw):
    figdir=ROOT/'figures';figdir.mkdir(exist_ok=True)
    keys=['exp','profile','xname','x','ws','wr','pd','pa','tout','n']
    rows=[]
    for key,g in raw.groupby(keys,sort=False):
        d=dict(zip(keys,key));d['replications']=len(g)
        for metric in ['efficiency','attempts_per_delivery','completion_ms']:
            d[metric]=g[metric].mean()
            # t_4 for backlogged, t_99 for finite runs
            d[metric+'_ci95']=(2.776445105 if len(g)==5 else 1.984216952)*g[metric].std(ddof=1)/math.sqrt(len(g))
        rows.append(d)
    a=pd.DataFrame(rows);a.to_csv(ROOT/'results/summary.csv',index=False)
    plt.rcParams.update({'font.size':10,'axes.grid':True,'grid.alpha':.2,'axes.spines.top':False,'axes.spines.right':False})
    manifest=[]
    for exp,g in a.groupby('exp',sort=False):
        metrics=['completion_ms'] if exp.startswith(('6','7')) else ['efficiency'] if exp in ['2','3a'] else ['efficiency','attempts_per_delivery']
        for metric in metrics:
            fig,ax=plt.subplots(figsize=(8.5,5.2))
            for i,(profile,_) in enumerate(PROFILES):
                q=g[g.profile==profile].sort_values('x')
                # S&W is a reference at the same horizontal coordinates.
                ax.errorbar(q.x,q[metric],yerr=q[metric+'_ci95'],fmt=['o','s','^','D','v'][i],linestyle='none',capsize=2,markersize=4,label=profile)
            xn=g.xname.iloc[0]
            if exp=='2':
                xx=np.linspace(1,64,300);ax.plot(xx,np.minimum(1,xx/11),'k--',lw=1,label='Error-free analysis min(1, Ws/11)')
            if exp=='3a':
                xx=np.linspace(0,.5,200);q=1-xx
                ax.plot(xx,q/(11*q+15*xx),'k:',lw=1,label='S&W renewal analysis')
                ax.plot(xx,q,'k--',lw=1,label='Ideal full-window SR bound 1-pd')
                ax.plot(xx,q/(1+14*xx),color='gray',ls='-.',lw=1,label='GBN per-frame recovery reference (T=15 ms)')
            labels={'ws':'Send window Ws (packets)','pd':'Data error probability pd','pa':'ACK error probability pa','tout':'Retransmission timeout (ms)'}
            ylabels={'efficiency':'Link efficiency (unique delivered bits / link capacity)','attempts_per_delivery':'Data transmission attempts / delivered packet','completion_ms':'Mean acknowledged transfer completion time (ms)'}
            row=g.iloc[0];fixed=[]
            if xn!='pd':fixed.append(f'pd={row.pd:g}')
            if xn!='pa':fixed.append(f'pa={row.pa:g}')
            suffix=', '.join(fixed)
            if xn!='tout':suffix+=f', timeout={row.tout:g} ms'
            if xn!='ws':suffix+=', GBN/SR Ws=64'
            if row.n:suffix+=f', N={row.n}'
            ax.set(xlabel=labels[xn],ylabel=ylabels[metric],title=f'Experiment {exp.split("_")[0]}: {suffix}')
            ax.set_ylim(bottom=0);ax.legend(fontsize=8,loc='best')
            fig.text(.5,.01,'Markers: simulation means; bars: 95% Student-t intervals across seeds. No interpolated simulation curves.',ha='center',fontsize=8)
            fig.tight_layout(rect=[0,.035,1,1]);name=f'exp{exp}_{metric}'
            fig.savefig(figdir/(name+'.png'),dpi=170);fig.savefig(figdir/(name+'.pdf'));plt.close(fig)
            manifest.append({'exp':exp,'metric':metric,'file':name+'.png'})
    (ROOT/'results/figures.json').write_text(json.dumps(manifest,indent=2))
    print(f'Wrote {len(manifest)} figures from {len(raw)} replications',flush=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--exp',type=int,default=0,choices=range(8));ap.add_argument('--workers',type=int,default=4);ap.add_argument('--plots-only',action='store_true');args=ap.parse_args()
    (ROOT/'results').mkdir(exist_ok=True)
    if args.plots_only:
        plots(pd.read_csv(ROOT/'results/runs.csv.gz'));return
    subprocess.run(['gcc','-O2','-std=c11','-Wall','-Wextra','-I',str(ROOT/'vendor'),str(ROOT/'src/arq.c'),str(ROOT/'vendor/simlib.c'),'-lm','-o',str(EXE)],check=True)
    print('\n'.join(validate()),flush=True)
    if args.exp==1:return
    cs=configs(args.exp)
    # Cache exact configurations so repeated S&W references are identical.
    def key(c):return tuple(c[k] for k in ['ws','wr','pd','pa','tout','n','seed'])
    unique={key(c):c for c in cs}
    cache={}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for i,r in enumerate(pool.map(run_one,unique.values())):
            cache[key(r)]={k:r[k] for k in ['efficiency','attempts_per_delivery','completion_ms','attempts','delivered']}
            if i%200==0: print(f'Completed {i+1}/{len(unique)} unique runs',flush=True)
    raw=pd.DataFrame([{**c,**cache[key(c)]} for c in cs]);path=ROOT/'results/runs.csv.gz'
    if args.exp and path.exists():
        old=pd.read_csv(path);old=old[~old.exp.astype(str).isin(raw.exp.astype(str))];raw=pd.concat([old,raw],ignore_index=True)
    raw.to_csv(path,index=False);plots(raw)
if __name__=='__main__':main()
