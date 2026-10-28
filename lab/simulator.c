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
struct Packet { double arrival, duration; unsigned collisions; int station, collided; Packet *next, *data_next; };
typedef struct { Packet *head,*tail; unsigned long queued, departed; double delay; } Station;
static Station st[100];
static int n=10, persistent=-1, active=0, data_busy=0;
static int beb_cap=10, reservation_pipeline=0, last_success=-1;
static const char *fixed_distribution="uniform";
static const char *mode="fixed";
static double rate=.1, backoff=10, horizon=200000, warmup=20000, xr=.1;
static double guard=.001;
static const double reservation_guard=1e-9;
static unsigned max_exponent=0, data_count=0, max_data_count=0;
static unsigned long repeats=0, target_packets=0;
static double busy_time=0, data_started=0, persistent_wait=0;
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
static double slot_length(void) { return reservation()?xr:1+2*guard; }
static double slot_guard(void) { return reservation()?reservation_guard:guard; }
static double activate(Packet *p,double earliest) {
  double t=earliest;
  if(slotted()) {
    double slot=slot_length(), g=slot_guard();
    t=ceil((earliest-g)/slot-1e-10)*slot+g;
    if(t<earliest-1e-8)t+=slot;
  }
  schedule(start,p,t);
  return t;
}
static void enqueue(Station *s,Packet *p) {
  p->next=NULL; if(s->tail) s->tail->next=p; else s->head=p;
  s->tail=p; s->queued++;
}
static void pop(Station *s) { assert(s->head); s->head=s->head->next; if(!s->head)s->tail=NULL; s->queued--; }
static void data_start(void) {
  if(!data_busy && data_head) { data_busy=1; data_started=now(); schedule(data_finish,data_head,now()+data_head->duration); }
}
static void record(Packet *p) {
  if(now()>=warmup) {
    double d=now()-p->arrival; assert(d>=p->duration-1e-8);
    if(last_success==p->station)repeats++;
    last_success=p->station;
    successes++; delay_sum+=d; collisions_sum+=p->collisions;
    st[p->station].departed++; st[p->station].delay+=d;
    data_work+=p->duration;
  }
}
static void data_finish(Simulation_Run_Ptr s,void *v) {
  (void)s; Packet *p=v; assert(p==data_head); record(p);
  busy_time+=fmax(0,now()-fmax(data_started,warmup));
  data_head=p->data_next; if(!data_head)data_tail=NULL; data_count--;
  if(!reservation_pipeline) {
    Station *q=&st[p->station]; assert(q->head==p); pop(q);
    if(q->head)activate(q->head,now());
  }
  free(p); data_busy=0; data_start();
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
  if(slotted()) { double slot=slot_length(), g=slot_guard();
    assert(fabs((now()-g)/slot-round((now()-g)/slot))<1e-5); }
  air[p->station]=p;
  p->collided=active>0;
  if(active)for(int i=0;i<n;i++)if(air[i])air[i]->collided=1;
  active++; assert(active<=n); if(now()>=warmup)attempts++;
  /* A data payload always lasts one unit; guards extend its slot. */
  double duration=reservation()?xr-2*reservation_guard:1;
  schedule(finish,p,now()+duration);
}
static void finish(Simulation_Run_Ptr s,void *v) {
  (void)s; Packet *p=v; Station *q=&st[p->station];
  assert(air[p->station]==p);air[p->station]=NULL;active--;
  if(p->collided) {
    p->collisions++;
    if(p->station==persistent) {
      /* Unslotted persistence means retry immediately, without random wait. */
      double retry=activate(p,now()); persistent_wait+=retry-now();
    } else {
      double b;
      if(!strcmp(mode,"fixed"))b=!strcmp(fixed_distribution,"uniform")?2*uniform()*backoff:exponential(backoff);
      else {
        unsigned exponent=p->collisions;
        if(beb_cap>0 && exponent>(unsigned)beb_cap)exponent=(unsigned)beb_cap;
        if(exponent>max_exponent)max_exponent=exponent;
        double window=ldexp(1.0,(int)fmin(exponent,1024));
        double u=uniform();
        if(reservation()) {
          /* Whole minislots, including zero, after the failed slot. */
          double t=ceil(now()/xr-1e-10)*xr+floor(u*window)*xr+reservation_guard;
          if(t<=horizon)schedule(start,p,t);
          return;
        }
        /* Slotted ALOHA keeps the continuous BEB wait, then aligns it. */
        b=u*window;

      }
      if(b>horizon-now())return; /* Retry lies beyond observation window. */
      activate(p,now()+b);
    }
  } else {
    if(reservation()) {
      if(now()>=warmup)reserved++;
      if(reservation_pipeline)pop(q);
      /* The station FIFO and data FCFS queue need separate links. */
      p->data_next=NULL;
      if(data_tail)data_tail->data_next=p;else data_head=p;
      data_tail=p;data_count++;
      if(data_count>max_data_count)max_data_count=data_count;
      assert(reservation_pipeline || data_count<=(unsigned)n);
      data_start();
      if(reservation_pipeline && q->head)activate(q->head,now());
    } else {
      pop(q); record(p);free(p);
      if(q->head)activate(q->head,now());
    }
  }
}
static unsigned long backlog(void) {
  unsigned long b=0;for(int i=0;i<n;i++)b+=st[i].queued;
  if(reservation_pipeline)for(Packet *p=data_head;p;p=p->data_next)b++;
  return b;
}
static void boundary(Simulation_Run_Ptr s,void *v) { (void)s;(void)v;backlog_warm=backlog();last_success=-1; }
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
    else if(!strcmp(k,"--beb-cap"))beb_cap=atoi(v);
    else if(!strcmp(k,"--fixed-distribution"))fixed_distribution=v;
    else if(!strcmp(k,"--reservation-pipeline"))reservation_pipeline=atoi(v);
    else if(!strcmp(k,"--guard"))guard=atof(v);
    else if(!strcmp(k,"--packets"))target_packets=strtoul(v,NULL,10);
    else {fprintf(stderr,"Unknown option %s\n",k);return 2;}
  }
  if(!isfinite(guard)||guard<=0||beb_cap<0||beb_cap>1024||
     (reservation_pipeline!=0 && reservation_pipeline!=1)||
     (strcmp(fixed_distribution,"uniform") && strcmp(fixed_distribution,"exponential"))||!isfinite(rate)||!isfinite(backoff)||!isfinite(xr)||!isfinite(horizon)||!isfinite(warmup)||n<1||n>100||rate<=0||backoff<=0||xr<=2*reservation_guard||horizon<=warmup||warmup<0||persistent>=n||persistent< -1||
     (strcmp(mode,"fixed")&&strcmp(mode,"beb")&&strcmp(mode,"slotted")&&strcmp(mode,"reservation")))return 2;
  random_generator_initialize(seed);sim=simulation_run_new();
  schedule(arrival,NULL,exponential(1/rate));schedule(boundary,NULL,warmup);schedule(stop,NULL,horizon);
  while(now()<horizon && (!target_packets || successes<target_packets))simulation_run_execute_event(sim);
  double elapsed=now(), t=elapsed-warmup;
  if(data_busy)busy_time+=fmax(0,elapsed-fmax(data_started,warmup));
  printf("mode,stations,rate,backoff,seed,time,warmup,xr,persistent,arrivals,successes,attempts,throughput,load,delay,collisions,backlog_warm,backlog_end,backlog_growth,reserved,data_work_rate,fixed_distribution,beb_cap,reservation_pipeline,guard,target_packets,horizon,repeat_fraction,data_utilization,max_data_queue,max_beb_exponent,persistent_wait,packet_throughput\n");
  printf("%s,%d,%.17g,%.17g,%u,%.17g,%.17g,%.17g,%d,%lu,%lu,%lu,%.12g,%.12g,%.12g,%.12g,%lu,%lu,%.12g,%lu,%.12g,%s,%d,%d,%.17g,%lu,%.17g,%.12g,%.12g,%u,%u,%.12g,%.12g\n",
    mode,n,rate,backoff,seed,elapsed,warmup,xr,persistent,arrivals,successes,attempts,successes/t,attempts/t,
    successes?delay_sum/successes:NAN,successes?collisions_sum/successes:NAN,backlog_warm,backlog(),
    ((double)backlog()-backlog_warm)/t,reserved,data_work/t,fixed_distribution,beb_cap,reservation_pipeline,guard,target_packets,horizon,
    successes>1?(double)repeats/(successes-1):NAN,busy_time/t,max_data_count,max_exponent,persistent_wait,successes/t);
  printf("station,successes,throughput,delay,backlog\n");
  for(int i=0;i<n;i++)printf("%d,%lu,%.12g,%.12g,%lu\n",i,st[i].departed,st[i].departed/t,
    st[i].departed?st[i].delay/st[i].departed:NAN,st[i].queued);
  /* Process exit releases remaining events/packets; each replication is a process. */
  return 0;
}
