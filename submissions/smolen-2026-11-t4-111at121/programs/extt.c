/* extt: frozen-core extension annealer, binary, strength t (2..6).
   Base CA (N0 x k0) frozen; r free rows, m free columns; only t-sets containing a new column are counted.
   usage: extt t base N0 k0 r m seed secs T out [-i state] [-c cand]   (k <= 64) */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <stdint.h>
static int t,N0,k0,r,m,N,k,P; static unsigned char **a;
static int *sets; static long ns; static int **inc_; static long *ninc;
static uint8_t *cnt; static int32_t *hpos; static int32_t *hole; static long H;
static uint64_t rs; static inline uint64_t rnd(void){rs^=rs<<13;rs^=rs>>7;rs^=rs<<17;return rs;}
static inline double urand(void){return (rnd()>>11)*(1.0/9007199254740992.0);}
static inline void decc(long id){ if(--cnt[id]==0){hpos[id]=H;hole[H++]=id;} }
static inline void incc(long id){ if(cnt[id]++==0){int32_t p=hpos[id];int32_t l=hole[--H];hole[p]=l;hpos[l]=p;hpos[id]=-1;} }
static inline int pat(const unsigned char*row,const int*s){int p=0;for(int e=0;e<t;e++)p=(p<<1)|row[s[e]];return p;}
static void flip(int R,int X){unsigned char*row=a[R];long n=ninc[X];int*L=inc_[X];
  for(long i=0;i<n;i++){long s=L[i];const int*S=sets+s*t;int p=pat(row,S);int bit=0;for(int e=0;e<t;e++)if(S[e]==X)bit=1<<(t-1-e);
    decc(s*P+p);incc(s*P+(p^bit));}
  row[X]^=1;}
static int isfree(int R,int X){return R>=N0||X>=k0;}
static void save(const char*fn){FILE*f=fopen(fn,"w");for(int i=0;i<N;i++){for(int j=0;j<k;j++)fprintf(f,j?" %d":"%d",a[i][j]);fprintf(f,"\n");}fclose(f);}
int main(int argc,char**argv){
  if(argc<11){fprintf(stderr,"usage\n");return 2;}
  t=atoi(argv[1]);const char*basef=argv[2];N0=atoi(argv[3]);k0=atoi(argv[4]);r=atoi(argv[5]);m=atoi(argv[6]);
  long seed=atol(argv[7]);double secs=atof(argv[8]),T=atof(argv[9]);const char*out=argv[10];const char*init=NULL;int CAND=4;
  for(int i=11;i<argc;i++){if(!strcmp(argv[i],"-i"))init=argv[++i];else if(!strcmp(argv[i],"-c"))CAND=atoi(argv[++i]);}
  N=N0+r;k=k0+m;P=1<<t;rs=0x9E3779B97F4A7C15ULL^(seed*0xD1B54A32D192ED03ULL);for(int i=0;i<20;i++)rnd();
  a=malloc(N*sizeof*a);for(int i=0;i<N;i++){a[i]=malloc(k);for(int j=0;j<k;j++)a[i][j]=rnd()&1;}
  FILE*f=fopen(basef,"r");if(!f){perror(basef);return 2;}
  for(int i=0;i<N0;i++)for(int j=0;j<k0;j++){int x;if(fscanf(f,"%d",&x)!=1){fprintf(stderr,"short base\n");return 2;}a[i][j]=x;}fclose(f);
  if(init){f=fopen(init,"r");if(!f){perror(init);return 2;}for(int i=0;i<N;i++)for(int j=0;j<k;j++){int x;if(fscanf(f,"%d",&x)!=1){fprintf(stderr,"short init\n");return 2;}if(isfree(i,j))a[i][j]=x;else if(a[i][j]!=x){fprintf(stderr,"init differs from base at %d %d\n",i,j);return 2;}}fclose(f);}
  /* enumerate t-sets with max >= k0 */
  long cap=1<<16;sets=malloc(cap*t*sizeof(int));ns=0;int c[8];for(int e=0;e<t;e++)c[e]=e;
  for(;;){ if(c[t-1]>=k0){ if(ns==cap){cap*=2;sets=realloc(sets,cap*t*sizeof(int));} memcpy(sets+ns*t,c,t*sizeof(int));ns++; }
    int e=t-1;while(e>=0&&c[e]==k-t+e)e--; if(e<0)break; c[e]++;for(int g=e+1;g<t;g++)c[g]=c[g-1]+1; }
  ninc=calloc(k,sizeof*ninc);inc_=malloc(k*sizeof*inc_);for(long s=0;s<ns;s++)for(int e=0;e<t;e++)ninc[sets[s*t+e]]++;
  for(int j=0;j<k;j++){inc_[j]=malloc((ninc[j]+1)*sizeof(int));ninc[j]=0;}
  for(long s=0;s<ns;s++)for(int e=0;e<t;e++){int j=sets[s*t+e];inc_[j][ninc[j]++]=s;}
  long total=ns*P;cnt=calloc(total,1);hpos=malloc(total*sizeof*hpos);hole=malloc(total*sizeof*hole);
  for(long s=0;s<ns;s++)for(int R=0;R<N;R++){long id=s*P+pat(a[R],sets+s*t);if(cnt[id]<255)cnt[id]++;}
  H=0;for(long id=0;id<total;id++){if(cnt[id]==0){hpos[id]=H;hole[H++]=id;}else hpos[id]=-1;}
  long best=H;time_t t0=time(NULL),tl=t0;long it=0;fprintf(stderr,"t=%d N=%d k=%d sets=%ld start holes=%ld\n",t,N,k,ns,H);
  int*cr=malloc(N*sizeof*cr);
  while(H>0){
    if((it&255)==0){time_t now=time(NULL);if(now-t0>=secs)break;if(now-tl>=30){tl=now;fprintf(stderr,"t=%ld it=%ld holes=%ld best=%ld\n",(long)(now-t0),it,H,best);}}
    it++;
    long id=hole[rnd()%H];long s=id/P;int p=id%P;const int*S=sets+s*t;int val[8];for(int e=0;e<t;e++)val[e]=(p>>(t-1-e))&1;
    int nc=0;for(int R=0;R<N;R++){int ok=1;for(int e=0;e<t;e++)if(a[R][S[e]]!=val[e]&&!isfree(R,S[e])){ok=0;break;}if(ok)cr[nc++]=R;}
    if(!nc)continue;
    long H0=H,bestH=-1;int bestR=-1;int tries=nc<CAND?nc:CAND;
    for(int q=0;q<tries;q++){int j=q+rnd()%(nc-q);int R=cr[j];cr[j]=cr[q];cr[q]=R;
      int fl[8],nf=0;for(int e=0;e<t;e++)if(a[R][S[e]]!=val[e]){flip(R,S[e]);fl[nf++]=S[e];}
      if(bestH<0||H<bestH){bestH=H;bestR=R;}
      for(int e=nf-1;e>=0;e--)flip(R,fl[e]);}
    if(bestH<=H0||urand()<exp((H0-bestH)/T)){for(int e=0;e<t;e++)if(a[bestR][S[e]]!=val[e])flip(bestR,S[e]);
      if(H<best){best=H;if(best<300){char fn[512];snprintf(fn,sizeof fn,"%s_best.txt",out);save(fn);}}}
  }
  fprintf(stderr,"END holes=%ld best=%ld it=%ld secs=%ld\n",H,best,it,(long)(time(NULL)-t0));
  if(H==0){char fn[512];snprintf(fn,sizeof fn,"%s_%d_%d.txt",out,N,k);save(fn);printf("FOUND %s\n",fn);}
  return H?1:0;
}
