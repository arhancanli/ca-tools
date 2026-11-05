/* kcl.c POOLFILE s seed seconds [mustfirst] - find s mutually QI columns in a pool (tabu swap search,
 * cost = conflicting pairs inside the set). Prints indices on success. Own code, debate 9 C. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <stdint.h>
static uint64_t rs=7; static inline uint64_t xr(void){rs^=rs<<13;rs^=rs>>7;rs^=rs<<17;return rs;}
static inline int rnd(int n){return (int)((xr()>>11)%(uint64_t)n);}
int main(int argc,char**argv){ FILE*f=fopen(argv[1],"r"); char line[256]; char **P=malloc(sizeof(char*)*200000); int n=0,N=0;
  while(fgets(line,256,f)){ int l=strlen(line); while(l&&(line[l-1]=='\n'||line[l-1]=='\r')) line[--l]=0; if(!l) continue; N=l; P[n]=strdup(line); n++; }
  int s=atoi(argv[2]); rs^=atoll(argv[3])*0x9E3779B97F4A7C15ULL; double secs=atof(argv[4]);
  uint8_t *conf=calloc((size_t)n*n,1);
  for(int i=0;i<n;i++) for(int j=i+1;j<n;j++){ int m=0; for(int r=0;r<N;r++) m|=1<<((P[i][r]-'0')*3+P[j][r]-'0'); conf[(size_t)i*n+j]=conf[(size_t)j*n+i]=(m!=511); }
  int *in=calloc(n,sizeof(int)), *S=malloc(sizeof(int)*s), *cc=calloc(n,sizeof(int)); /* cc[v] = conflicts of v with S */
  int *tabu=calloc(n,sizeof(int)); int perm_ok=0;
  int sf=getenv("SEEDFIRST")?atoi(getenv("SEEDFIRST")):0; if(sf>s) sf=s;
  for(int i=0;i<sf;i++){ in[i]=1; S[i]=i; }
  for(int i=sf;i<s;i++){ int v; do v=rnd(n); while(in[v]); in[v]=1; S[i]=v; }
  for(int v=0;v<n;v++) for(int i=0;i<s;i++) cc[v]+=conf[(size_t)v*n+S[i]];
  int cost=0; for(int i=0;i<s;i++) cost+=cc[S[i]]; cost/=2; int best=cost; long it=0; clock_t t0=clock();
  while(cost>0){ if((it&255)==0 && (double)(clock()-t0)/CLOCKS_PER_SEC>secs) break; it++;
    /* pick out: a conflicting member (random among max cc), in: non-member with min cc (not tabu) */
    int oi=-1,bo=-1; for(int t=0;t<s;t++){ int v=S[t]; if(cc[v]>0 && (cc[v]>bo || (cc[v]==bo && (xr()&1)))){bo=cc[v];oi=t;} }
    if(oi<0) break; int u=S[oi]; int bi=-1,bv=1<<30;
    for(int v=0;v<n;v++){ if(in[v]||tabu[v]>it) continue; int c=cc[v]-conf[(size_t)v*n+u]; if(c<bv||(c==bv&&(xr()&1))){bv=c;bi=v;} }
    if(bi<0) continue; int delta=bv-cc[u];
    in[u]=0; in[bi]=1; S[oi]=bi; tabu[u]=it+7+rnd(10);
    for(int v=0;v<n;v++) cc[v]+=conf[(size_t)v*n+bi]-conf[(size_t)v*n+u];
    cost+=delta; if(cost<best) best=cost; }
  printf("pool=%d s=%d best_conflicts=%d it=%ld\n",n,s,best,it);
  if(cost==0 && argc>5){ FILE*o=fopen(argv[5],"w"); for(int i=0;i<s;i++) fprintf(o,"%s\n",P[S[i]]); fclose(o); }
  return cost==0?0:1; }
