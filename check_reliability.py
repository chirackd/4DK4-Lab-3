from run import simulate,SEEDS,ROOT
import pandas as pd
rows=[]
for ws,wr,pd_,pa,tout in [(64,1,.1,0,15),(64,16,.1,.1,15),(64,64,.1,.1,100),(1,1,.5,.5,15)]:
 for duration in [110000,1010000,3010000]:
  for seed in SEEDS:
   r,_=simulate(ws,wr,pd_,pa,tout,seed,duration,10000)
   rows.append(dict(ws=ws,wr=wr,pd=pd_,pa=pa,tout=tout,duration=duration,seed=seed,**r))
s=pd.DataFrame(rows);s.to_csv(ROOT/'results/reliability.csv',index=False)
print(s.groupby(['ws','wr','pd','pa','tout','duration']).efficiency.agg(['mean','std']).to_string())
