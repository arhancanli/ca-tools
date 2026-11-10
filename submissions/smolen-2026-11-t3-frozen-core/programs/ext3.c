/* ext3: frozen-core extension annealer, binary strength 3.
   Base CA (N0 x k0) is frozen. r free rows and m free columns are added; only triples containing a new
   column can be uncovered. Exact incremental counts; focus move (Nurmela): pick an uncovered pattern,
   try CAND rows that can take it, apply the best, Metropolis at fixed T.
   usage: ext3 base N0 k0 r m seed secs T out [-i state] [-c cand]
   state/out file: full (N0+r) x (k0+m) array. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <stdint.h>
static int N0,k0,r,m,N,k; static unsigned char **a;
static uint8_t *cnt; static long *zoff; static long total; static int32_t *hpos; static long *hole; static long H;
static uint64_t rs; static inline uint64_t rnd(void){rs^=rs<<13;rs^=rs>>7;rs^=rs<<17;return rs;}
static inline double urand(void){return (rnd()>>11)*(1.0/9007199254740992.0);}
static inline long cid(int u,int w,int z){return zoff[z-k0]+((long)w*(w-1)/2+u)*8;}
static inline void dec(long id){ if(--cnt[id]==0){hpos[id]=H;hole[H++]=id;} }
static inline void inc(long id){ if(cnt[id]++==0){long p=hpos[id];long l=hole[--H];hole[p]=l;hpos[l]=p;hpos[id]=-1;} }
static void flip(int R,int X){
  unsigned char *row=a[R]; int o=row[X], n=1-o;
  if(X>=k0){ long base=zoff[X-k0];
    for(int w=1;w<X;w++){ int bw=row[w]<<1; long b2=base+((long)w*(w-1)/2)*8;
      for(int u=0;u<w;u++){ long id=b2+u*8+((row[u]<<2)|bw); dec(id+o); inc(id+n);} } }
  int zs = X>=k0? X+1 : k0;
  for(int z=zs;z<k;z++){ int vz=row[z];
    for(int y=0;y<z;y++){ if(y==X) continue; int u,w,pu,pw_o,pat_o,pat_n;
      if(y<X){u=y;w=X; long id=cid(u,w,z); pat_o=(row[y]<<2)|(o<<1)|vz; pat_n=(row[y]<<2)|(n<<1)|vz; dec(id+pat_o); inc(id+pat_n);}
      else {u=X;w=y; long id=cid(u,w,z); pat_o=(o<<2)|(row[y]<<1)|vz; pat_n=(n<<2)|(row[y]<<1)|vz; dec(id+pat_o); inc(id+pat_n);}
      (void)pu;(void)pw_o; } }
  row[X]=n;
}
static int isfree(int R,int X){return R>=N0||X>=k0;}
static void save(const char*fn){FILE*f=fopen(fn,"w");for(int i=0;i<N;i++){for(int j=0;j<k;j++)fprintf(f,j?" %d":"%d",a[i][j]);fprintf(f,"\n");}fclose(f);}
int main(int argc,char**argv){
  if(argc<10){fprintf(stderr,"usage\n");return 2;}
  const char*basef=argv[1];N0=atoi(argv[2]);k0=atoi(argv[3]);r=atoi(argv[4]);m=atoi(argv[5]);
  long seed=atol(argv[6]);double secs=atof(argv[7]),T=atof(argv[8]);const char*out=argv[9];const char*init=NULL;int CAND=4;
  for(int i=10;i<argc;i++){if(!strcmp(argv[i],"-i"))init=argv[++i];else if(!strcmp(argv[i],"-c"))CAND=atoi(argv[++i]);}
  N=N0+r;k=k0+m;rs=0x9E3779B97F4A7C15ULL^(seed*0xD1B54A32D192ED03ULL);for(int i=0;i<20;i++)rnd();
  a=malloc(N*sizeof*a);for(int i=0;i<N;i++){a[i]=malloc(k);for(int j=0;j<k;j++)a[i][j]=rnd()&1;}
  FILE*f=fopen(basef,"r");if(!f){perror(basef);return 2;}
  for(int i=0;i<N0;i++)for(int j=0;j<k0;j++){int x;if(fscanf(f,"%d",&x)!=1){fprintf(stderr,"short base\n");return 2;}a[i][j]=x;}fclose(f);
  if(init){f=fopen(init,"r");if(!f){perror(init);return 2;}for(int i=0;i<N;i++)for(int j=0;j<k;j++){int x;if(fscanf(f,"%d",&x)!=1){fprintf(stderr,"short init\n");return 2;}if(isfree(i,j))a[i][j]=x;else if(a[i][j]!=x){fprintf(stderr,"init differs from base at %d %d\n",i,j);return 2;}}fclose(f);}
  zoff=malloc((m+1)*sizeof*zoff);total=0;for(int z=k0;z<k;z++){zoff[z-k0]=total;total+=(long)z*(z-1)/2*8;}
  cnt=calloc(total,1);hpos=malloc(total*sizeof*hpos);hole=malloc(total*sizeof*hole);
  for(int z=k0;z<k;z++)for(int w=1;w<z;w++)for(int u=0;u<w;u++){long id=cid(u,w,z);for(int R=0;R<N;R++){int p=(a[R][u]<<2)|(a[R][w]<<1)|a[R][z];if(cnt[id+p]<255)cnt[id+p]++;}}
  H=0;for(long id=0;id<total;id++){if(cnt[id]==0){hpos[id]=H;hole[H++]=id;}else hpos[id]=-1;}
  long best=H;time_t t0=time(NULL),tl=t0;long it=0;fprintf(stderr,"N=%d k=%d counters=%ld start holes=%ld\n",N,k,total,H);
  int *cr=malloc(N*sizeof*cr);
  while(H>0){
    if((it&255)==0){time_t now=time(NULL);if(now-t0>=secs)break;if(now-tl>=30){tl=now;fprintf(stderr,"t=%ld it=%ld holes=%ld best=%ld\n",(long)(now-t0),it,H,best);}}
    it++;
    long id=hole[rnd()%H];int pat=id&7;long q=id>>3;int z=k0;while(z+1<k&&zoff[z+1-k0]<=id)z++;long pid=(id-zoff[z-k0])>>3;
    int w=(int)((1+sqrt(1+8.0*pid))/2);while((long)w*(w-1)/2>pid)w--;while((long)(w+1)*w/2<=pid)w++;int u=pid-(long)w*(w-1)/2;(void)q;
    int col[3]={u,w,z},val[3]={(pat>>2)&1,(pat>>1)&1,pat&1};
    int nc=0;for(int R=0;R<N;R++){int ok=1;for(int e=0;e<3;e++)if(a[R][col[e]]!=val[e]&&!isfree(R,col[e])){ok=0;break;}if(ok)cr[nc++]=R;}
    if(!nc)continue;
    long H0=H,bestH=-1;int bestR=-1;int tries=nc<CAND?nc:CAND;
    for(int c=0;c<tries;c++){int j=c+rnd()%(nc-c);int R=cr[j];cr[j]=cr[c];cr[c]=R;
      int fl[3],nf=0;for(int e=0;e<3;e++)if(a[R][col[e]]!=val[e]){flip(R,col[e]);fl[nf++]=col[e];}
      if(bestH<0||H<bestH){bestH=H;bestR=R;}
      for(int e=nf-1;e>=0;e--)flip(R,fl[e]);}
    if(bestH<=H0||urand()<exp((H0-bestH)/T)){for(int e=0;e<3;e++)if(a[bestR][col[e]]!=val[e])flip(bestR,col[e]);
      if(H<best){best=H;if(best<200){char fn[512];snprintf(fn,sizeof fn,"%s_best.txt",out);save(fn);}}}
  }
  fprintf(stderr,"END holes=%ld best=%ld it=%ld secs=%ld\n",H,best,it,(long)(time(NULL)-t0));
  if(H==0){char fn[512];snprintf(fn,sizeof fn,"%s_%d_%d.txt",out,N,k);save(fn);printf("FOUND %s\n",fn);}
  return H?1:0;
}
