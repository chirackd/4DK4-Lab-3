#!/usr/bin/env python3
"""Plot independently simulated measurements for the documented baseline profile."""
import argparse
import os
from pathlib import Path
import tempfile
os.environ.setdefault('MPLCONFIGDIR',str(Path(tempfile.gettempdir())/'lab3-matplotlib'))
os.environ.setdefault('XDG_CACHE_HOME',str(Path(tempfile.gettempdir())/'lab3-cache'))
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parent
COLORS=['#2367a1','#c77c13','#708238','#b34a79','#6f5aa5','#308c88']
MARKERS=['o','s','^','D','v','P']
KEY=['mode','stations','backoff','xr','persistent','rate','fixed_distribution','beb_cap','reservation_pipeline','guard']
METRICS=['throughput','load','delay','backlog_growth','backlog_end','collisions','repeat_fraction','data_utilization','max_data_queue']
# Exact two-sided 95% Student-t critical values for the usual 2..6 seeds.
# For more seeds the conservative df=5 value is retained, never a tighter invented CI.
T95={1:12.7062047364,2:4.30265272975,3:3.18244630528,4:2.7764451052,5:2.57058183564}
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,
                     'axes.spines.right':False,'axes.grid':True,'grid.alpha':.18,'savefig.dpi':180})


def aggregate(raw, keys=KEY, metrics=METRICS):
    rows=[]
    for key,g in raw.groupby(keys):
        row=dict(zip(keys,key if isinstance(key,tuple) else [key]));count=len(g);row['replications']=count
        for metric in metrics:
            values=g[metric].to_numpy(float);mean=values.mean()
            ci=T95.get(count-1,T95[5])*values.std(ddof=1)/np.sqrt(count) if count>1 else np.nan
            row.update({metric:mean,metric+'_min':values.min(),metric+'_max':values.max(),
                        metric+'_ci95':ci,metric+'_lower95':mean-ci,metric+'_upper95':mean+ci})
        carried=g['system_throughput'] if 'system_throughput' in g else g['throughput']
        row['balanced']=bool(((carried>=.97*g['rate']) & (g['backlog_growth']<=.03*g['rate'])).all())
        if row.get('mode')=='reservation' and row['rate']>=1:row['balanced']=False
        rows.append(row)
    return pd.DataFrame(rows)


def series(ax,g,x,y,label,color,marker='o',balanced_only=False):
    if balanced_only:g=g[g['balanced']]
    g=g.sort_values(x)
    valid=np.isfinite(g[x]) & np.isfinite(g[y]);g=g[valid]
    ci=g[y+'_ci95'];has_ci=np.isfinite(ci)
    ax.errorbar(g.loc[has_ci,x],g.loc[has_ci,y],yerr=ci[has_ci],fmt='none',
                ecolor=color,elinewidth=.8,capsize=2,alpha=.65)
    for balanced in [True,False]:
        q=g[g['balanced']==balanced]
        ax.scatter(q[x],q[y],s=26,marker=marker,facecolors=color if balanced else 'white',edgecolors=color,linewidths=.9,zorder=3)
    ax.plot([],[],marker=marker,linestyle='none',color=color,label=label)


def save(fig,name,figures):
    fig.tight_layout();fig.savefig(figures/f'{name}.png');fig.savefig(figures/f'{name}.pdf');plt.close(fig)


def axes_pair():return plt.subplots(1,2,figsize=(11,4.2))


def format_axes(ax,x,y,title):
    names={'rate':'Arrival rate λ (packets / X)','throughput':'Throughput S (packets / X)',
           'load':'Attempt load G (attempts / X)','delay':'Mean completed-packet delay D / X',
           'repeat_fraction':'Same-station successive-success fraction'}
    ax.set(title=title,xlabel=names.get(x,x),ylabel=names.get(y,y))
    if y=='delay':ax.set_yscale('log');ax.set_ylim(bottom=.8)
    else:ax.set_ylim(bottom=0)
    ax.legend(fontsize=9)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--results-dir',type=Path,default=ROOT.parent/'output/results')
    p.add_argument('--figures-dir',type=Path,default=ROOT.parent/'output/figures')
    args=p.parse_args();results=args.results_dir;figures=args.figures_dir
    for name in ['runs.csv','stations.csv','sensitivity.csv']:
        if not (results/name).is_file():p.error(f'Missing {name}; run all experiments and sensitivity first.')
    figures.mkdir(parents=True,exist_ok=True)
    raw=pd.read_csv(results/'runs.csv')
    missing=set(KEY+METRICS)-set(raw.columns)
    if missing:p.error('Old result schema; rerun experiments with current code. Missing '+', '.join(sorted(missing)))
    assert not raw.duplicated(KEY+['seed']).any()
    assert np.isfinite(raw[METRICS].to_numpy()).all()
    assert (raw['arrivals']-raw['successes']==raw['backlog_end']-raw['backlog_warm']).all()
    a=aggregate(raw);a.to_csv(results/'summary.csv',index=False)
    fixed=a[a['mode']=='fixed']
    for x,y,name in [('rate','delay','fixed_delay_arrival'),('rate','throughput','fixed_throughput_arrival'),
                     ('throughput','delay','fixed_delay_throughput'),('load','throughput','fixed_throughput_load')]:
        fig,axes=axes_pair()
        for ax,n in zip(axes,[10,5]):
            for i,b in enumerate([5,10,20] if n==10 else [3,5,7]):
                g=fixed[(fixed['stations']==n)&(fixed['backoff']==b)]
                series(ax,g,x,y,f'Mean backoff {b}',COLORS[i],MARKERS[i],balanced_only=x=='throughput')
            if x=='load':
                t=np.linspace(0,1.9,400);ax.plot(t,t*np.exp(-2*t),'--',color='#333333',lw=1,label='Poisson pure: G exp(-2G)')
                ax.plot(t,t*np.exp(-t),':',color='#555555',lw=1,label='Poisson slotted: G exp(-G)')
            format_axes(ax,x,y,f'{n} stations')
        save(fig,name,figures)
    fig,axes=axes_pair()
    for ax,n in zip(axes,[10,5]):
        for i,b in enumerate([5,10,20] if n==10 else [3,5,7]):
            series(ax,fixed[(fixed['stations']==n)&(fixed['backoff']==b)],'throughput','delay',f'Fixed mean {b}',COLORS[i],MARKERS[i],True)
        series(ax,a[(a['mode']=='beb')&(a['stations']==n)&(a['persistent']==-1)],'throughput','delay','Capped BEB',COLORS[3],'D',True)
        format_axes(ax,'throughput','delay',f'{n} stations; flow-balanced points only')
    save(fig,'beb_comparison',figures)
    stations=pd.read_csv(results/'stations.csv');fair=[]
    for (n,rate,seed,persistent),g in stations[stations['mode']=='beb'].groupby(['stations','rate','seed','persistent']):
        groups=[('Persistent station 0',g[g['station_station']==0]),('Others (persistent system)',g[g['station_station']!=0])] if persistent==0 else [('Others (all BEB baseline)',g[g['station_station']!=0])]
        for label,q in groups:
            count=q['station_successes'].sum()
            fair.append({'stations':n,'rate':rate,'seed':seed,'group':label,
                         'throughput':q['station_throughput'].mean(),
                         'delay':(q['station_successes']*q['station_delay']).sum()/count if count else np.nan,
                         'backlog_growth':g['backlog_growth'].iloc[0],'system_throughput':g['throughput'].iloc[0]})
    f=aggregate(pd.DataFrame(fair),['stations','rate','group'],['throughput','delay']);f.to_csv(results/'fairness.csv',index=False)
    labels=['Persistent station 0','Others (persistent system)','Others (all BEB baseline)']
    for y in ['delay','throughput']:
        fig,axes=axes_pair()
        for ax,n in zip(axes,[10,5]):
            for i,label in enumerate(labels):series(ax,f[(f['stations']==n)&(f['group']==label)],'rate',y,label,COLORS[i],MARKERS[i])
            format_axes(ax,'rate',y,f'{n} stations')
            if y=='throughput':ax.set_ylabel('Per-station throughput (packets / X)')
        save(fig,'persistent_'+y,figures)
    fig,axes=axes_pair()
    for ax,n in zip(axes,[10,5]):
        for i,persistent in enumerate([0,-1]):
            series(ax,a[(a['mode']=='beb')&(a['stations']==n)&(a['persistent']==persistent)],'rate','throughput','With persistent station' if persistent==0 else 'All stations BEB',COLORS[i],MARKERS[i])
        format_axes(ax,'rate','throughput',f'{n} stations')
    save(fig,'persistent_total_throughput',figures)
    for x,y,name in [('throughput','delay','slotted_delay_throughput'),('rate','throughput','slotted_throughput_arrival'),('load','throughput','slotted_throughput_load')]:
        fig,axes=axes_pair()
        for ax,n in zip(axes,[10,5]):
            for i,mode in enumerate(['beb','slotted']):
                series(ax,a[(a['mode']==mode)&(a['stations']==n)&(a['persistent']==-1)],x,y,'Unslotted BEB' if mode=='beb' else 'Slotted BEB',COLORS[i],MARKERS[i],balanced_only=x=='throughput')
            if x=='load':
                t=np.linspace(0,1.5,400);ax.plot(t,t*np.exp(-2*t),'--',color='#333333',lw=1,label='G exp(-2G)');ax.plot(t,t*np.exp(-t),':',color='#555555',lw=1,label='G exp(-G)')
            format_axes(ax,x,y,f'{n} stations')
        save(fig,name,figures)
    reservation=a[a['mode']=='reservation'];delay=reservation[reservation['rate']<2]
    fig,axes=axes_pair()
    for i,ratio in enumerate([1,2,5,10,20,50]):
        series(axes[0],delay[(delay['stations']==10)&np.isclose(delay['xr'],1/ratio)],'rate','delay',f'X/Xr = {ratio}',COLORS[i],MARKERS[i])
    for i,n in enumerate([5,10,20]):
        series(axes[1],delay[(delay['stations']==n)&np.isclose(delay['xr'],.1)],'rate','delay',f'{n} stations',COLORS[i],MARKERS[i])
    for ax,title in zip(axes,['10 stations; reservation length','X/Xr = 10; station count']):
        t=np.linspace(.02,.95,300);ax.plot(t,1/(1-t),'--',color='#333333',lw=1,label='M/M/1 reference')
        format_axes(ax,'rate','delay',title)
    save(fig,'reservation_delay',figures)
    fig,ax=plt.subplots(figsize=(9,4.3))
    for i,ratio in enumerate([1,2,5,10,20,50]):series(ax,delay[(delay['stations']==10)&np.isclose(delay['xr'],1/ratio)],'rate','throughput',f'X/Xr = {ratio}',COLORS[i],MARKERS[i])
    format_axes(ax,'rate','throughput','10 stations; reservation throughput')
    save(fig,'reservation_throughput',figures)
    cap=reservation[np.isclose(reservation['rate'],2)].copy();cap['ratio']=1/cap['xr']
    cap.to_csv(results/'capacity.csv',index=False)
    fig,ax=plt.subplots(figsize=(9,4.3))
    for i,n in enumerate([5,10,20]):
        g=cap[cap['stations']==n].sort_values('ratio');ci=g['data_utilization_ci95'];valid=np.isfinite(ci)
        ax.errorbar(g.loc[valid,'ratio'],g.loc[valid,'data_utilization'],yerr=ci[valid],fmt='none',ecolor=COLORS[i],capsize=2)
        ax.scatter(g['ratio'],g['data_utilization'],color=COLORS[i],marker=MARKERS[i],label=f'{n} stations',s=28)
    ax.axhline(1,c='#333333',ls='--',lw=1,label='Data-channel upper bound')
    ax.set(xscale='log',xlabel='Mean data duration / minislot duration, X/Xr',ylabel='Capacity (data-channel busy fraction)',title='Reservation capacity at λ = 2/X',ylim=(0,1.04));ax.legend(fontsize=9)
    save(fig,'reservation_capacity',figures)
    fig,ax=plt.subplots(figsize=(9,4.3))
    for i,(mode,b,label) in enumerate([('fixed',10,'Fixed mean 10'),('beb',10,'Unslotted BEB'),('slotted',10,'Slotted BEB')]):
        g=a[(a['mode']==mode)&(a['stations']==10)&(a['backoff']==b)&(a['persistent']==-1)]
        series(ax,g,'rate','repeat_fraction',label,COLORS[i],MARKERS[i])
    ax.axhline(.1,c='#333333',ls=':',lw=1,label='Independent successes: 1/N');ax.set_xscale('log');ax.set_ylim(0,1.04)
    format_axes(ax,'rate','repeat_fraction','10 stations; MAC capture diagnostic')
    save(fig,'capture_repeat_fraction',figures)
    sens=pd.read_csv(results/'sensitivity.csv');ss=aggregate(sens,KEY+['time']);ss.to_csv(results/'sensitivity_summary.csv',index=False)
    fig,axes=axes_pair()
    for ax,mode in zip(axes,['beb','reservation']):
        for i,((rate,xr),g) in enumerate(ss[ss['mode']==mode].groupby(['rate','xr'])):
            series(ax,g,'time','delay',f'λ={rate:g}'+(f', X/Xr={1/xr:g}' if mode=='reservation' else ''),COLORS[i],MARKERS[i])
        format_axes(ax,'time','delay',mode);ax.set_xlabel('Total simulated time / X');ax.set_xscale('log')
    save(fig,'accuracy_runlength',figures)
    print(f'Validated {len(raw)} main and {len(sens)} sensitivity replications; exported 16 figures.')

if __name__=='__main__':main()
