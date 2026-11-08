/* pool.c - large column neighbourhood: remove R columns from a strength-2 ternary CA, collect many
 * columns that are qualitatively independent of all kept columns (single-column local search),
 * then search a max clique of mutually QI candidates; report whether more than R fit back.
 * Usage: pool ARRAY N K R seed tries seconds [mode]   mode 0: random removal, 1: contiguous block
 * Own code, debate 9 agent C. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <time.h>
static int N,K,R,KK; static uint8_t *A; static int *keep,*rem; static uint64_t rs=99;
static inline uint64_t xr(void){rs^=rs<<13;rs^=rs>>7;rs^=rs<<17;return rs;}
static inline int rnd(int n){return (int)((xr()>>11)%(uint64_t)n);}
static int cost(uint8_t *x, int *cntb){ /* cntb[K*9] */ int m=0; memset(cntb,0,sizeof(int)*KK*9);
  for(int r=0;r<N;r++) for(int i=0;i<KK;i++) cntb[i*9+A[r*K+keep[i]]*3+x[r]]++;
  for(int i=0;i<KK*9;i++) if(!cntb[i]) m++; return m; }
static int qi(uint8_t*x,uint8_t*y){ int s=0; for(int r=0;r<N;r++) s|=1<<(x[r]*3+y[r]); return s==511; }
static void norm(uint8_t*x){ int map[3]={-1,-1,-1},n=0; for(int r=0;r<N;r++){ if(map[x[r]]<0) map[x[r]]=n++; x[r]=map[x[r]]; } }
int main(int argc,char**argv){ N=atoi(argv[2]); K=atoi(argv[3]); R=atoi(argv[4]); rs^=atoll(argv[5])*0x9E3779B97F4A7C15ULL; int tries=atoi(argv[6]); double secs=atof(argv[7]); int mode=argc>8?atoi(argv[8]):0;
  A=malloc(N*K); FILE*f=fopen(argv[1],"r"); for(int i=0;i<N*K;i++){int v; if(fscanf(f,"%d",&v)!=1) return 1; A[i]=v;} fclose(f);
  int mn=9; for(int i=0;i<N*K;i++) if(A[i]<mn) mn=A[i]; if(mn==1) for(int i=0;i<N*K;i++) A[i]--;
  int *perm=malloc(sizeof(int)*K); for(int i=0;i<K;i++) perm[i]=i; if(mode==0) for(int i=0;i<K;i++){int j=i+rnd(K-i),t=perm[i];perm[i]=perm[j];perm[j]=t;}
  else { int s=rnd(K); for(int i=0;i<K;i++) perm[i]=(s+i)%K; }
  rem=perm; keep=perm+R; KK=K-R;
  int *cb=malloc(sizeof(int)*KK*9); int cap=200000; uint8_t *pool=malloc((size_t)cap*N); int np=0;
  /* removed columns themselves are candidates */
  for(int i=0;i<R;i++){ for(int r=0;r<N;r++) pool[np*N+r]=A[r*K+rem[i]]; norm(pool+np*N); np++; }
  uint8_t x[64]; clock_t t0=clock(); int found=0;
  for(int t=0;t<tries && (double)(clock()-t0)/CLOCKS_PER_SEC<secs;t++){
    for(int r=0;r<N;r++) x[r]=rnd(3); int c=cost(x,cb);
    int steps=getenv("STEPS")?atoi(getenv("STEPS")):20000;
    for(int step=0; step<steps && c>0; step++){ int r=rnd(N), o=x[r], v=(o+1+rnd(2))%3; int d=0;
      for(int i=0;i<KK;i++){ int a=A[r*K+keep[i]]*3; int *q=cb+i*9+a; if(--q[o]==0) d++; if(q[v]++==0) d--; }
      if(d<=0 || rnd(1000)<30) c+=d; else { for(int i=0;i<KK;i++){ int a=A[r*K+keep[i]]*3; int *q=cb+i*9+a; q[v]--; q[o]++; } continue; }
      x[r]=v; }
    if(c==0){ found++; norm(x); int dup=0; for(int p=0;p<np&&!dup;p++) if(!memcmp(pool+p*N,x,N)) dup=1;
      if(!dup && np<cap){ memcpy(pool+np*N,x,N); np++; } } }
  /* clique: greedy randomized + one-swap improvement, many restarts */
  uint8_t *adj=calloc((size_t)np*np,1); for(int i=0;i<np;i++) for(int j=i+1;j<np;j++) adj[i*np+j]=adj[j*np+i]=qi(pool+i*N,pool+j*N);
  int bestc=0; int *cl=malloc(sizeof(int)*np),*ord=malloc(sizeof(int)*np);
  for(int rep=0; rep<2000; rep++){ for(int i=0;i<np;i++) ord[i]=i; for(int i=0;i<np;i++){int j=i+rnd(np-i),t=ord[i];ord[i]=ord[j];ord[j]=t;}
    int n=0; for(int i=0;i<np;i++){ int u=ord[i],ok=1; for(int j=0;j<n&&ok;j++) if(!adj[u*np+cl[j]]) ok=0; if(ok) cl[n++]=u; } if(n>bestc) bestc=n; }
  int deg=0; for(int i=0;i<np;i++){int d=0; for(int j=0;j<np;j++) d+=adj[i*np+j]; deg+=d;}
  if(getenv("KEEP")){FILE*g=fopen(getenv("KEEP"),"w"); for(int i=0;i<KK;i++){for(int r=0;r<N;r++) fputc('0'+A[r*K+keep[i]],g); fputc('\n',g);} fclose(g);}
  if(getenv("DUMP")){FILE*g=fopen(getenv("DUMP"),"w"); for(int p=0;p<np;p++){for(int r=0;r<N;r++) fputc('0'+pool[p*N+r],g); fputc('\n',g);} fclose(g);}
  printf("R=%d tries=%d found=%d distinct_pool=%d (incl %d removed) avgdeg=%.1f best_clique=%d (need >%d)\n",R,tries,found,np,R,np?(double)deg/np:0,bestc,R);
  return 0; }
