#!/usr/bin/env python3
"""Independent heap-based Python oracle for finite C simulation regression checks."""
import heapq
from run import simulate,ROOT
MASK=(1<<64)-1
class Stream:
 def __init__(self,s):self.s=s
 def draw(self):
  self.s=(self.s+0x9e3779b97f4a7c15)&MASK;z=self.s
  z=((z^(z>>30))*0xbf58476d1ce4e5b9)&MASK;z=((z^(z>>27))*0x94d049bb133111eb)&MASK
  return (z^(z>>31))/(1<<64)
def oracle(ws,wr,pd,pa,tout,seed,n):
 heap=[];serial=0;now=0.;base=next_id=rn=0;busy=False;attempts=0
 acked=set();received=set();pending=set();version={};rd=Stream(seed);ra=Stream(seed^0xd1b54a32d192ed03)
 priorities={'ack':0,'data':1,'timer':2,'end':3}
 def put(t,kind,p,payload=None):
  nonlocal serial
  serial+=1;heapq.heappush(heap,(t,priorities[kind],serial,kind,p,payload))
 def start():
  nonlocal next_id,busy,attempts
  if busy:return
  choices=pending-acked
  if choices:p=min(choices);pending.discard(p)
  elif next_id<min(base+ws,n):p=next_id;next_id+=1
  else:return
  busy=True;attempts+=1;version[p]=version.get(p,0)+1
  put(now+1,'end',p);put(now+6,'data',p);put(now+tout,'timer',p,version[p])
 start()
 while base<n:
  assert heap
  now=heap[0][0]
  while heap and heap[0][0]==now:
   _,_,_,kind,p,payload=heapq.heappop(heap)
   if kind=='end':busy=False
   if kind=='data' and rd.draw()>=pd:
    sel=None
    if p<rn:sel=p
    elif p<rn+wr:
     sel=p;received.add(p)
     while rn in received:received.remove(rn);rn+=1
    if ra.draw()>=pa:put(now+5,'ack',rn-1,sel if sel is not None and sel>=rn else None)
   if kind=='ack':
    acked.update(range(base,min(p+1,next_id)))
    if payload is not None:acked.add(payload)
    while base in acked:base+=1
   if kind=='timer' and p>=base and p not in acked and version[p]==payload:
    pending.add(p);version[p]+=1
    for j in range(p+wr,next_id):
     if j not in acked and j not in pending:pending.add(j);version[j]=version.get(j,0)+1
  if base<n:start()
 return now,attempts,rn
if __name__=='__main__':
 rows=[]
 for ws,wr in [(1,1),(4,1),(4,4),(16,1),(16,4),(16,16)]:
  for pd,pa in [(0,0),(.1,0),(0,.5),(.5,.5)]:
   for t in [2,10.99,11,11.01,15,50]:
    expected=oracle(ws,wr,pd,pa,t,400452897,20)
    result,_=simulate(ws,wr,pd,pa,t,400452897,100000,0,20)
    actual=(result['completion_ms'],result['attempts'],result['delivered'])
    assert abs(actual[0]-expected[0])<1e-6 and actual[1:]==expected[1:],(ws,wr,pd,pa,t,actual,expected)
    rows.append((ws,wr,pd,pa,t,*actual))
 import csv
 with (ROOT/'results/oracle_checks.csv').open('w',newline='') as f:
  w=csv.writer(f);w.writerow(['ws','wr','pd','pa','tout','completion_ms','attempts','delivered']);w.writerows(rows)
 print(f'{len(rows)} independent Python/C finite-transfer comparisons passed (time, attempts, unique deliveries).')
