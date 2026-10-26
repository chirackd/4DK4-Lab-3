/* Lab 3 replacement driver using the supplied Simlib event engine and RNG.
 * Original supplied sources are retained for comparison. */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <math.h>
#include <assert.h>
#include "simlib.h"

typedef struct Packet Packet;
struct Packet { double arrival, duration; unsigned collisions; int station, collided; Packet *next; };
typedef struct { Packet *head,*tail; unsigned long queued, departed; double delay; } Station;
static Station st[100];
static int n=10, persistent=-1, active=0, data_busy=0;
static const char *mode="fixed";
static double rate=.1, backoff=10, horizon=200000, warmup=20000, xr=.1;
static const double guard=1e-7;
static unsigned seed=333333;
static unsigned long attempts=0, successes=0, arrivals=0, reserved=0, backlog_warm=0;
static double delay_sum=0, collisions_sum=0, data_work=0;
static Packet *air[100], *data_head=NULL,*data_tail=NULL;
static Simulation_Run_Ptr sim;
static double now(void) { return simulation_run_get_time(sim); }
static int reservation(void) { return !strcmp(mode,"reservation"); }
static int slotted(void) { return reservation() || !strcmp(mode,"slotted"); }
static double uniform(void) { double u=uniform_generator(); return fmax(1e-12,fmin(1-1e-12,u)); }
static double exponential(double mean) { return -mean*log(uniform()); }
static void schedule(void (*fn)(Simulation_Run_Ptr,void*),void *p,double t) {
  assert(isfinite(t) && t>=now()-1e-9);
  Event e={"lab3",fn,p}; simulation_run_schedule_event(sim,e,t);
}
static void start(Simulation_Run_Ptr,void*);
static void finish(Simulation_Run_Ptr,void*);
static void data_finish(Simulation_Run_Ptr,void*);
static void activate(Packet *p,double earliest) {
  double slot=reservation()?xr:1;
  double t=slotted()?ceil(earliest/slot-1e-10)*slot+guard:earliest;
  schedule(start,p,t);
}
static void enqueue(Station *s,Packet *p) {
  p->next=NULL; if(s->tail) s->tail->next=p; else s->head=p;
  s->tail=p; s->queued++;
}
static void pop(Station *s) { assert(s->head); s->head=s->head->next; if(!s->head)s->tail=NULL; s->queued--; }
static void data_start(void) {
  if(!data_busy && data_head) { data_busy=1; schedule(data_finish,data_head,now()+data_head->duration); }
}
static void record(Packet *p) {
  if(now()>=warmup) {
    double d=now()-p->arrival; assert(d>=p->duration-2*guard-1e-8);
    successes++; delay_sum+=d; collisions_sum+=p->collisions;
    st[p->station].departed++; st[p->station].delay+=d;
    data_work+=p->duration;
  }
}
static void data_finish(Simulation_Run_Ptr s,void *v) {
  (void)s; Packet *p=v; assert(p==data_head); record(p);
  data_head=p->next; if(!data_head)data_tail=NULL; free(p); data_busy=0; data_start();
}
static void arrival(Simulation_Run_Ptr s,void *v) {
  (void)s;(void)v;
  int id=(int)(uniform()*n); Packet *p=calloc(1,sizeof(*p)); assert(p);
  p->station=id; p->arrival=now(); p->duration=reservation()?exponential(1):1;
  int idle=!st[id].head; enqueue(&st[id],p);
  if(now()>=warmup)arrivals++;
  if(idle)activate(p,now());
  schedule(arrival,NULL,now()+exponential(1/rate));
}
static void start(Simulation_Run_Ptr s,void *v) {
  (void)s;Packet *p=v; assert(air[p->station]==NULL);
  if(slotted()) { double slot=reservation()?xr:1;
    assert(fabs((now()-guard)/slot-round((now()-guard)/slot))<1e-5); }
  air[p->station]=p;
  p->collided=active>0;
  if(active)for(int i=0;i<n;i++)if(air[i])air[i]->collided=1;
  active++; assert(active<=n); if(now()>=warmup)attempts++;
  double duration=reservation()?xr-2*guard:(slotted()?1-2*guard:1);
  schedule(finish,p,now()+duration);
}
static void finish(Simulation_Run_Ptr s,void *v) {
  (void)s; Packet *p=v; Station *q=&st[p->station];
  assert(air[p->station]==p);air[p->station]=NULL;active--;
  if(p->collided) {
    p->collisions++;
    if(p->station==persistent) {
      /* Part 4: next unit boundary, even though other stations are unslotted. */
      schedule(start,p,ceil(now()-1e-10)+guard);
    } else {
      double b;
      if(!strcmp(mode,"fixed"))b=exponential(backoff);
      else {
        /* No artificial Ethernet retry cap: lab specifies [0,2^Nc). */
        double window=ldexp(1.0,(int)fmin(p->collisions,1024));
        /* Overflow to infinity means no retry within this finite horizon. */
        b=uniform()*window*(reservation()?xr:1);
        if(slotted()) {
          double slot=reservation()?xr:1;
          double next=ceil(now()/slot-1e-10)*slot;
          double t=next+floor(b/slot)*slot+guard;
          if(t<=horizon)schedule(start,p,t);
          return;
        }
      }
      if(b>horizon-now())return; /* Retry lies beyond observation window. */
      activate(p,now()+b);
    }
  } else {
    pop(q);
    if(reservation()) {
      if(now()>=warmup)reserved++;
      p->next=NULL;if(data_tail)data_tail->next=p;else data_head=p;data_tail=p;data_start();
    } else { record(p);free(p); }
    if(q->head)activate(q->head,now());
  }
}
static unsigned long backlog(void) {
  unsigned long b=0;for(int i=0;i<n;i++)b+=st[i].queued;
  for(Packet *p=data_head;p;p=p->next)b++;
  return b;
}
static void boundary(Simulation_Run_Ptr s,void *v) { (void)s;(void)v;backlog_warm=backlog(); }
static void stop(Simulation_Run_Ptr s,void *v) { (void)s;(void)v; }
int main(int argc,char **argv) {
  for(int i=1;i<argc;i++) {
    if(i+1>=argc){fprintf(stderr,"Every option needs a value\n");return 2;}
    const char *k=argv[i],*v=argv[++i];
    if(!strcmp(k,"--mode"))mode=v;else if(!strcmp(k,"--stations"))n=atoi(v);
    else if(!strcmp(k,"--rate"))rate=atof(v);else if(!strcmp(k,"--backoff"))backoff=atof(v);
    else if(!strcmp(k,"--seed"))seed=(unsigned)strtoul(v,NULL,10);
    else if(!strcmp(k,"--time"))horizon=atof(v);else if(!strcmp(k,"--warmup"))warmup=atof(v);
    else if(!strcmp(k,"--xr"))xr=atof(v);else if(!strcmp(k,"--persistent"))persistent=atoi(v);
    else {fprintf(stderr,"Unknown option %s\n",k);return 2;}
  }
  if(!isfinite(rate)||!isfinite(backoff)||!isfinite(xr)||!isfinite(horizon)||!isfinite(warmup)||n<1||n>100||rate<=0||backoff<=0||xr<=2*guard||horizon<=warmup||warmup<0||persistent>=n||persistent< -1||
     (strcmp(mode,"fixed")&&strcmp(mode,"beb")&&strcmp(mode,"slotted")&&strcmp(mode,"reservation")))return 2;
  random_generator_initialize(seed);sim=simulation_run_new();
  schedule(arrival,NULL,exponential(1/rate));schedule(boundary,NULL,warmup);schedule(stop,NULL,horizon);
  while(now()<horizon)simulation_run_execute_event(sim);
  double t=horizon-warmup;
  printf("mode,stations,rate,backoff,seed,time,warmup,xr,persistent,arrivals,successes,attempts,throughput,load,delay,collisions,backlog_warm,backlog_end,backlog_growth,reserved,data_work_rate\n");
  printf("%s,%d,%.9g,%.9g,%u,%.9g,%.9g,%.9g,%d,%lu,%lu,%lu,%.12g,%.12g,%.12g,%.12g,%lu,%lu,%.12g,%lu,%.12g\n",
    mode,n,rate,backoff,seed,horizon,warmup,xr,persistent,arrivals,successes,attempts,successes/t,attempts/t,
    successes?delay_sum/successes:NAN,successes?collisions_sum/successes:NAN,backlog_warm,backlog(),
    ((double)backlog()-backlog_warm)/t,reserved,data_work/t);
  printf("station,successes,throughput,delay,backlog\n");
  for(int i=0;i<n;i++)printf("%d,%lu,%.12g,%.12g,%lu\n",i,st[i].departed,st[i].departed/t,
    st[i].departed?st[i].delay/st[i].departed:NAN,st[i].queued);
  /* Process exit releases remaining events/packets; each replication is a process. */
  return 0;
}
