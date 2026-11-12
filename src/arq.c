/* Lab 4 ARQ model; uses Terence Todd's GPL-3.0-or-later simlib from Lab 3.
 * All times in ms; packet IDs are unbounded integers, no sequence wrap. */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <assert.h>
#include <math.h>
#include "simlib.h"
typedef struct { int type,seq,gen; } Msg;
typedef struct {
 int ws,wr,n,cap,base,next,recv,busy,done,trace,tgen,legacy,individual,cumulative_only;
 double pd,pa,tout,end,warm; long attempts,delivered;
 int *acked,*buffer,*pending,*generation;
 uint64_t rd,ra;
} Model;
enum {TXEND,DATA,ACK,TIMER};
static void event(Simulation_Run_Ptr,void*);
static double uniform(uint64_t *s) { /* SplitMix64: independent data/ACK streams */
 uint64_t z=(*s+=UINT64_C(0x9e3779b97f4a7c15));
 z=(z^(z>>30))*UINT64_C(0xbf58476d1ce4e5b9);
 z=(z^(z>>27))*UINT64_C(0x94d049bb133111eb);
 return (z^(z>>31)) * (1.0/18446744073709551616.0);
}
static void logmsg(Simulation_Run_Ptr s,const char *what,int p) {
 Model *m=s->data; if(m->trace) printf("%9.3f %-19s id=%d sendbase=%d next=%d recvbase=%d\n",s->clock->time,what,p,m->base,m->next,m->recv);
}
static void schedule(Simulation_Run_Ptr s,int type,int seq,int gen,double t) {
 Msg *p=malloc(sizeof(*p)); assert(p); *p=(Msg){type,seq,gen};
 Event e={"ARQ",event,p}; simulation_run_schedule_event(s,e,t);
}
static void gbntimer(Simulation_Run_Ptr s) {
 Model *m=s->data; m->tgen++;
 if(m->base<m->next) schedule(s,TIMER,m->base,m->tgen,s->clock->time+m->tout+1e-8);
}
static void kick(Simulation_Run_Ptr s) {
 Model *m=s->data; if(m->busy || m->done) return;
 if(s->eventlist->front_ptr && s->eventlist->front_ptr->occurrence_time==s->clock->time)return;
 int p=-1; for(int i=m->base;i<m->next;i++) if(m->pending[i]&&!m->acked[i]){p=i;break;}
 int fresh=0;
 if(p<0 && m->next<m->base+m->ws && (!m->n||m->next<m->n)) {p=m->next++;fresh=1;}
 if(p<0) return;
 assert(p<m->cap); m->pending[p]=0; m->busy=1;
 if((m->n || s->clock->time>m->warm)) m->attempts++;
 logmsg(s,fresh?"TX new":"TX retry",p);
 schedule(s,TXEND,p,0,s->clock->time+1);
 schedule(s,DATA,p,0,s->clock->time+6);
 if(!m->legacy || m->wr>1) schedule(s,TIMER,p,++m->generation[p],s->clock->time+m->tout);
 else if(p==m->base) gbntimer(s);
}
static void event(Simulation_Run_Ptr s,void *arg) {
 Msg e=*(Msg*)arg; free(arg); Model *m=s->data; int p=e.seq;
 if(e.type==TXEND) m->busy=0;
 if(e.type==DATA) {
  if(uniform(&m->rd)<m->pd) logmsg(s,"DATA lost",p);
  else {
   int sel=-1;
   if(p<m->recv) {sel=p;logmsg(s,"DATA duplicate",p);}
   else if(p<m->recv+m->wr) {
    m->buffer[p]=1;sel=p;logmsg(s,"DATA accepted",p);
    while(m->buffer[m->recv]) {m->buffer[m->recv]=0;m->recv++;if((m->n || s->clock->time>m->warm))m->delivered++;}
   } else logmsg(s,"DATA outside window",p);
   /* One atomic ACK contains both cumulative and selective information. */
   if(uniform(&m->ra)<m->pa) logmsg(s,"ACK lost",p);
   else schedule(s,ACK,m->recv-1,(!m->cumulative_only && sel>=m->recv)?sel+1:0,s->clock->time+5);
  }
 }
 if(e.type==ACK) {
  logmsg(s,"ACK cumulative",p);
  if(e.gen>0){int sel=e.gen-1;if(sel<m->next)m->acked[sel]=1;logmsg(s,"ACK selective",sel);}
  int old=m->base;
  for(int i=m->base;i<=p && i<m->next;i++) m->acked[i]=1;
  while(m->base<m->next && m->acked[m->base]) m->base++;
  if(m->legacy && m->wr==1 && old!=m->base) gbntimer(s);
  if(m->n && m->base==m->n) m->done=1;
 }
 if(e.type==TIMER) {
  /* Let ACKs at an exact timestamp beat timeouts; timeout precedes a queued TXEND. */
  for(Event_Container_Ptr c=s->eventlist->front_ptr;c && c->occurrence_time==s->clock->time;c=c->next_container)
   if(((Msg*)c->event.attachment)->type==ACK){schedule(s,TIMER,p,e.gen,s->clock->time);return;}
  if(m->legacy && m->wr==1) {
   if(e.gen==m->tgen && p==m->base && m->base<m->next){
    logmsg(s,"TIMEOUT go-back",p);m->tgen++;
    for(int i=m->base;i<m->next;i++) m->pending[i]=1;
   }
  } else if(p>=m->base && !m->acked[p] && e.gen==m->generation[p]) {
   logmsg(s,"TIMEOUT per-frame",p);m->pending[p]=1;m->generation[p]++;
   /* Conservative replay policy, not a deduction that the receiver lost them.
    * An expired timer can also mean ACK loss. Queued timers are invalidated. */
   if(!m->legacy && !m->individual) for(int i=p+m->wr;i<m->next;i++)
    if(!m->acked[i] && !m->pending[i]){m->pending[i]=1;m->generation[i]++;}
  }
 }
 assert(m->base<=m->next && m->next-m->base<=m->ws);
 kick(s);
}
int main(int argc,char **argv) {
 if(argc!=11){fprintf(stderr,"usage: arq Ws Wr pd pa Tout seed duration warmup N trace\n");return 2;}
 Model m={0};
 m.legacy=getenv("ARQ_LEGACY")!=NULL;
 m.individual=getenv("ARQ_INDIVIDUAL")!=NULL;
 m.cumulative_only=getenv("ARQ_CUMULATIVE_ONLY")!=NULL;
 m.ws=atoi(argv[1]);m.wr=atoi(argv[2]);m.pd=atof(argv[3]);m.pa=atof(argv[4]);m.tout=atof(argv[5]);
 m.rd=strtoull(argv[6],0,10);m.ra=m.rd^UINT64_C(0xd1b54a32d192ed03);
 m.end=atof(argv[7]);m.warm=atof(argv[8]);m.n=atoi(argv[9]);m.trace=atoi(argv[10]);
 if(m.ws<1||m.wr<1||m.pd<0||m.pd>=1||m.pa<0||m.pa>=1||m.tout<=0||m.end<=m.warm||m.warm<0||m.n<0)return 2;
 m.cap=m.n?m.n+m.wr+2:(int)ceil(m.end)+m.ws+m.wr+4;
 m.acked=calloc(m.cap,sizeof(int));m.buffer=calloc(m.cap,sizeof(int));m.pending=calloc(m.cap,sizeof(int));m.generation=calloc(m.cap,sizeof(int));
 assert(m.acked&&m.buffer&&m.pending&&m.generation);
 Simulation_Run_Ptr s=simulation_run_new();s->data=&m;kick(s);
 while(s->eventlist->size && !m.done && s->eventlist->front_ptr->occurrence_time<=m.end)simulation_run_execute_event(s);
 if(m.n&&!m.done){fprintf(stderr,"finite transfer did not finish\n");return 3;}
 double elapsed=m.n?s->clock->time:m.end-m.warm;
 printf("RESULT,%.12g,%.12g,%.12g,%ld,%ld\n",m.delivered/elapsed,m.attempts/(double)(m.delivered?m.delivered:1),m.n?elapsed:0,m.attempts,m.delivered);
 /* simlib frees containers but attachments belong to the model. */
 for(Event_Container_Ptr c=s->eventlist->front_ptr;c;c=c->next_container)free(c->event.attachment);
 simulation_run_free_memory(s);free(m.acked);free(m.buffer);free(m.pending);free(m.generation);return 0;
}
