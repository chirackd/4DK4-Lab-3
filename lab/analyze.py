#!/usr/bin/env python3
"""Create reviewed summaries and export scientific plots (markers, no interpolation)."""
import os
os.environ.setdefault("MPLCONFIGDIR", "/tmp/lab3-matplotlib")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp/lab3-cache")
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
ROOT=Path(__file__).resolve().parent
COLORS=['#2367a1','#c77c13','#708238','#b34a79','#6f5aa5','#308c88']
MARKERS=['o','s','^','D','v','P']
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':12,'axes.spines.top':False,'axes.spines.right':False,'axes.titleweight':'bold','axes.grid':True,'grid.alpha':.18,'savefig.dpi':180})
KEY=['mode','stations','backoff','xr','persistent','rate']
METRICS=['throughput','load','delay','backlog_growth','backlog_end','collisions','data_work_rate']

def aggregate(x,keys=KEY,metrics=METRICS):
    rows=[]
    for key,g in x.groupby(keys):
        row=dict(zip(keys,key if isinstance(key,tuple) else [key]));row['replications']=len(g)
        for m in metrics:
            a=g[m].to_numpy(float);row[m]=a.mean();row[m+'_min']=a.min();row[m+'_max']=a.max();row[m+'_sd']=a.std(ddof=1) if len(a)>1 else 0
        # Descriptive flow check, deliberately not named a stability test.
        row['balanced']=bool((g['backlog_growth'].abs()<=.01*g['rate']).all())
        if row.get('mode')=='reservation' and row['rate']>=1:row['balanced']=False
        rows.append(row)
    return pd.DataFrame(rows)

def series(ax,g,x,y,label,c,marker='o'):
    g=g.sort_values('rate');xx=g[x];yy=g[y]
    lo=yy-g[y+'_min'];hi=g[y+'_max']-yy
    ax.errorbar(xx,yy,yerr=np.array([lo.clip(lower=0),hi.clip(lower=0)]),fmt='none',ecolor=c,alpha=.45,elinewidth=.8,capsize=1.7)
    for bal in [True,False]:
        q=g[g['balanced']==bal]
        ax.scatter(q[x],q[y],s=27,marker=marker,facecolors=c if bal else 'white',edgecolors=c,linewidths=.9,zorder=3)
    ax.plot([],[],color=c,marker=marker,linestyle='none',label=label)

def save(fig,name):
    fig.tight_layout();fig.savefig(ROOT/f'figures/{name}.png');fig.savefig(ROOT/f'figures/{name}.pdf');plt.close(fig)

def main():
    raw=pd.read_csv(ROOT/'results/runs.csv');a=aggregate(raw);a.to_csv(ROOT/'results/summary.csv',index=False)
    for y,x,name in [('delay','rate','fixed_delay_arrival'),('throughput','rate','fixed_throughput_arrival'),('delay','throughput','fixed_delay_throughput'),('throughput','load','fixed_throughput_load')]:
        fig,axes=plt.subplots(1,2,figsize=(11,4.1))
        for ax,n in zip(axes,[5,10]):
            for i,b in enumerate([3,5,7] if n==5 else [5,10,20]):
                g=a[(a['mode']=='fixed')&(a['stations']==n)&(a['backoff']==b)]
                series(ax,g,x,y,f'Mean backoff {b}',COLORS[i],MARKERS[i])
            if x=='load':
                t=np.linspace(0,max(1.5,g['load'].max()),400);ax.plot(t,t*np.exp(-2*t),'--',color='#333333',lw=1,label='Poisson: G exp(-2G)')
            ax.set(title=f'{n} stations',xlabel={'rate':'Arrival rate λ (packets / X)','throughput':'Throughput S (packets / X)','load':'Attempt load G (attempts / X)'}[x],ylabel='Mean completed-packet delay D / X' if y=='delay' else 'Throughput S (packets / X)')
            if y=='delay':ax.set_yscale('log')
            else:ax.set_ylim(bottom=0)
            ax.legend(fontsize=10)
        save(fig,name)
    fig,axes=plt.subplots(1,2,figsize=(11,4.1))
    for ax,n in zip(axes,[5,10]):
        for i,b in enumerate([3,5,7] if n==5 else [5,10,20]):
            series(ax,a[(a['mode']=='fixed')&(a['stations']==n)&(a['backoff']==b)],'throughput','delay',f'Fixed mean {b}',COLORS[i],MARKERS[i])
        series(ax,a[(a['mode']=='beb')&(a['stations']==n)&(a['persistent']==-1)],'throughput','delay','Binary exponential',COLORS[3],'D')
        ax.set(title=f'{n} stations',xlabel='Throughput S (packets / X)',ylabel='Mean completed-packet delay D / X',yscale='log');ax.legend(fontsize=10)
    save(fig,'beb_comparison')
    station=pd.read_csv(ROOT/'results/stations.csv'); station=station[(station['mode']=='beb')&(station['persistent']==0)]
    sr=[]
    for key,g in station.groupby(['stations','rate','seed']):
        for typ,q in [('Persistent station 0',g[g['station_station']==0]),('Other stations',g[g['station_station']!=0])]:
            count=q['station_successes'].sum();sr.append(dict(zip(['stations','rate','seed'],key))|{'group':typ,'throughput':q['station_throughput'].mean(),'delay':(q['station_successes']*q['station_delay']).sum()/count,'backlog_growth':g['backlog_growth'].iloc[0]})
    sr=pd.DataFrame(sr);sa=aggregate(sr,['stations','rate','group'],['throughput','delay']);sa.to_csv(ROOT/'results/fairness.csv',index=False)
    for y in ['delay','throughput']:
        fig,axes=plt.subplots(1,2,figsize=(11,4.1))
        for ax,n in zip(axes,[5,10]):
            for i,typ in enumerate(['Persistent station 0','Other stations']):
                series(ax,sa[(sa['stations']==n)&(sa['group']==typ)],'rate',y,typ+(' (per-station S)' if y=='throughput' else ' (pooled D)'),COLORS[i],MARKERS[i])
            if y=='throughput':
                t=np.array([0,.8]);ax.plot(t,t/n,'--',c='#333333',lw=1,label='Equal offered rate λ/N');ax.set_ylim(bottom=0)
            else:ax.set_yscale('log')
            ax.set(title=f'{n} stations',xlabel='Total arrival rate λ (packets / X)',ylabel='Mean completed-packet delay D / X' if y=='delay' else 'Per-station throughput (packets / X)');ax.legend(fontsize=10)
        save(fig,'persistent_'+y)
    for x,y,name in [('throughput','delay','slotted_delay_throughput'),('rate','throughput','slotted_throughput_arrival'),('load','throughput','slotted_throughput_load')]:
        fig,axes=plt.subplots(1,2,figsize=(11,4.1))
        for ax,n in zip(axes,[5,10]):
            for i,mode in enumerate(['beb','slotted']):
                series(ax,a[(a['mode']==mode)&(a['stations']==n)&(a['persistent']==-1)],x,y,'Unslotted BEB' if mode=='beb' else 'Slotted BEB',COLORS[i],MARKERS[i])
            if x=='load':
                t=np.linspace(0,2.5,400);ax.plot(t,t*np.exp(-2*t),'--',color='#555555',lw=1,label='G exp(-2G)');ax.plot(t,t*np.exp(-t),':',color='#222222',lw=1.5,label='G exp(-G)')
            if y=='delay':ax.set_yscale('log')
            else:ax.set_ylim(bottom=0)
            ax.set(title=f'{n} stations',xlabel={'rate':'Arrival rate λ (packets / X)','load':'Attempt load G (attempts / X)','throughput':'Throughput S (packets / X)'}[x],ylabel='Mean completed-packet delay D / X' if y=='delay' else 'Throughput S (packets / X)');ax.legend(fontsize=10)
        save(fig,name)
    for y in ['delay','throughput']:
        fig,ax=plt.subplots(figsize=(9,4.5))
        for i,ratio in enumerate([1,2,5,10,20,50]):
            g=a[(a['mode']=='reservation')&np.isclose(a['xr'],1/ratio)];series(ax,g,'rate',y,f'X/Xr = {ratio}',COLORS[i],MARKERS[i])
        if y=='delay':
            t=np.linspace(.02,.95,300);ax.plot(t,1/(1-t),'--',color='#333333',lw=1,label='M/M/1 reference (Xr → 0)');ax.set_yscale('log')
        else:ax.axhline(1,c='#333333',ls='--',lw=1,label='Data service ceiling 1/X');ax.set_ylim(bottom=0)
        ax.set(xlabel='Arrival rate λ (packets / X)',ylabel='Mean completed-packet delay D / X' if y=='delay' else 'Throughput S (packets / X)',title='Reservation channel with 10 stations; exponential data lengths');ax.legend(fontsize=10,ncol=2)
        save(fig,'reservation_'+y)
    cap=[]
    for ratio in [1,2,5,10,20,50]:
        g=a[(a['mode']=='reservation')&np.isclose(a['xr'],1/ratio)]
        bal=g[g['balanced']];peak=g.loc[g['throughput'].idxmax()]
        cap.append({'ratio':ratio,'poisson_benchmark':min(1,ratio/np.e),'observed_service_ceiling':peak['throughput'],'peak_at_rate':peak['rate'],'largest_flow_balanced_rate':bal['rate'].max(),'delay_at_balanced_edge':bal.sort_values('rate')['delay'].iloc[-1]})
    cap=pd.DataFrame(cap);cap.to_csv(ROOT/'results/capacity.csv',index=False)
    fig,ax=plt.subplots(figsize=(9,4.3));t=cap['ratio']
    for i,(k,l) in enumerate([('observed_service_ceiling','Largest measured mean S'),('largest_flow_balanced_rate','Largest flow-balanced tested λ'),('poisson_benchmark','Poisson reservation benchmark min(1, X/(e Xr))')]):
        ax.scatter(t,cap[k],marker=MARKERS[i],color=COLORS[i],label=l,s=45)
    ax.axhline(1,c='#333333',ls='--',lw=1,label='Data channel upper bound');ax.set(xscale='log',xlabel='Mean data length / minislot length, X/Xr',ylabel='Packets / X',ylim=(0,1.08));ax.set_xticks(t,labels=[str(v) for v in t]);ax.legend(fontsize=10);save(fig,'reservation_capacity')
    sens=pd.read_csv(ROOT/'results/sensitivity.csv');ss=aggregate(sens,KEY+['time']);ss.to_csv(ROOT/'results/sensitivity_summary.csv',index=False)
    fig,axes=plt.subplots(1,2,figsize=(11,4.1))
    for ax,mode in zip(axes,['beb','reservation']):
        q=ss[ss['mode']==mode]
        for i,((rate,xr),g) in enumerate(q.groupby(['rate','xr'])):
            series(ax,g,'time','delay',f'λ={rate:g}'+(f', X/Xr={1/xr:g}' if mode=='reservation' else ''),COLORS[i],MARKERS[i])
        ax.set(xscale='log',yscale='log',xlabel='Total simulated time / X',ylabel='Mean completed-packet delay D / X',title='Unslotted BEB' if mode=='beb' else 'Reservation');ax.legend(fontsize=10)
    save(fig,'accuracy_runlength')
    assert len(raw)==len(raw.drop_duplicates(KEY+['seed']))
    assert np.isfinite(raw[METRICS].to_numpy()).all()
    assert (raw['arrivals']-raw['successes']==raw['backlog_end']-raw['backlog_warm']).all()
    print(f'Validated {len(raw)} main replications, {len(sens)} sensitivity replications; exported {len(list((ROOT/"figures").glob("*.png")))} figures')
if __name__=='__main__':main()
