// rep.c (debate10): exact fixed-N hole repair for small-k binary covering arrays, strength t<=6, k<=64.
// Nurmela-style focus move: pick a random missing tuple, flip the one cell of a row at Hamming distance 1
// that fixes it with the best exact delta (tabu + Metropolis at fixed T). On 0 holes: save, then delete the
// row with the fewest uniquely covered tuples (if N>NMIN) and continue.
// usage: rep FILE t secs seed T outprefix [spare] ; env NMIN (default N), SAVEBEST=1
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>
#include <time.h>
static int N,K,T,NS; static uint8_t *A; // A[r*K+c]
static uint8_t *cnt; // cnt[s*(1<<T)+p]
static uint8_t (*setc)[6]; // columns of set s
static int **colsets; static int *ncolsets; // sets containing column c
static uint64_t rs;
static inline uint64_t rnd(){rs^=rs<<13;rs^=rs>>7;rs^=rs<<17;return rs;}
static inline double ur(){return (rnd()>>11)*(1.0/9007199254740992.0);}
static inline int pat(int r,int s){const uint8_t*c=setc[s];const uint8_t*row=A+(size_t)r*K;int p=0;for(int i=0;i<T;i++)p|=row[c[i]]<<i;return p;}
static int holes; static int *hl,*hp; // hole list and positions
static inline void addh(size_t i){hp[i]=holes;hl[holes++]=i;}
static inline void remh(size_t i){int q=hp[i];int last=hl[--holes];hl[q]=last;hp[last]=q;hp[i]=-1;}
static void build(){ // enumerate sets
  int idx[8]; NS=0; // count
  // iterative enumeration
  for(int i=0;i<T;i++)idx[i]=i;
  int cap=1<<16; setc=malloc(cap*6); 
  while(1){ if(NS==cap){cap*=2;setc=realloc(setc,cap*6);} for(int i=0;i<T;i++)setc[NS][i]=idx[i]; NS++;
    int i=T-1; while(i>=0&&idx[i]==K-T+i)i--; if(i<0)break; idx[i]++; for(int j=i+1;j<T;j++)idx[j]=idx[j-1]+1; }
  cnt=calloc((size_t)NS<<T,1); hl=malloc(((size_t)NS<<T)*sizeof(int)); hp=malloc(((size_t)NS<<T)*sizeof(int));
  ncolsets=calloc(K,sizeof(int)); for(int s=0;s<NS;s++)for(int i=0;i<T;i++)ncolsets[setc[s][i]]++;
  colsets=malloc(K*sizeof(int*)); for(int c=0;c<K;c++){colsets[c]=malloc(ncolsets[c]*sizeof(int));ncolsets[c]=0;}
  for(int s=0;s<NS;s++)for(int i=0;i<T;i++){int c=setc[s][i];colsets[c][ncolsets[c]++]=s;}
}
static void recount(){ memset(cnt,0,(size_t)NS<<T); for(int r=0;r<N;r++)for(int s=0;s<NS;s++){int p=pat(r,s);if(cnt[(s<<T)|p]<255)cnt[(s<<T)|p]++;}
  holes=0; for(size_t i=0;i<((size_t)NS<<T);i++){hp[i]=-1; if(!cnt[i]) addh(i);} }
static int delta(int r,int c){ int d=0; const uint8_t*row=A+(size_t)r*K; int n=ncolsets[c]; int*L=colsets[c];
  for(int q=0;q<n;q++){int s=L[q]; const uint8_t*cc=setc[s]; int p=0,bit=0; for(int i=0;i<T;i++){p|=row[cc[i]]<<i; if(cc[i]==c)bit=1<<i;}
    uint8_t*C=cnt+((size_t)s<<T); if(C[p]==1)d++; if(C[p^bit]==0)d--; }
  return d; }
static void apply(int r,int c){ const uint8_t*row=A+(size_t)r*K; int n=ncolsets[c]; int*L=colsets[c];
  for(int q=0;q<n;q++){int s=L[q]; const uint8_t*cc=setc[s]; int p=0,bit=0; for(int i=0;i<T;i++){p|=row[cc[i]]<<i; if(cc[i]==c)bit=1<<i;}
    uint8_t*C=cnt+((size_t)s<<T); if(--C[p]==0)addh(((size_t)s<<T)|p); if(C[p^bit]++==0)remh(((size_t)s<<T)|(p^bit)); }
  A[(size_t)r*K+c]^=1; }
static void save(const char*fn){FILE*o=fopen(fn,"w");for(int r=0;r<N;r++){for(int c=0;c<K;c++)fprintf(o,"%d%c",A[r*K+c],c==K-1?'\n':' ');}fclose(o);}
int main(int argc,char**argv){
  FILE*f=fopen(argv[1],"r"); T=atoi(argv[2]); double secs=atof(argv[3]); rs=atoll(argv[4])*2654435761ULL+88172645463325252ULL; double Temp=atof(argv[5]); char*out=argv[6]; int spare=argc>7?atoi(argv[7]):0;
  static char line[40000]; int cap=0; N=0; uint8_t*B=NULL;
  while(fgets(line,sizeof line,f)){int k=0;static uint8_t row[4096];for(char*p=line;*p;p++)if(*p=='0'||*p=='1')row[k++]=*p-'0'; if(!k)continue;K=k; if(N==cap){cap=cap?cap*2:512;B=realloc(B,(size_t)cap*K);} memcpy(B+(size_t)N*K,row,K);N++;}
  fclose(f); A=malloc((size_t)(N+spare)*K); memcpy(A,B,(size_t)N*K); for(int r=N;r<N+spare;r++)for(int c=0;c<K;c++)A[(size_t)r*K+c]=rnd()&1; N+=spare;
  int Nmin=getenv("NMIN")?atoi(getenv("NMIN")):N; int savebest=getenv("SAVEBEST")?1:0;
  build();
  if(getenv("GREEDY")){ // rebuild spare rows greedily from the hole list
    int N1=N-spare; N=N1; recount(); fprintf(stderr,"base N=%d holes=%d\n",N,holes);
    for(int r=N1;r<N1+spare;r++){ int8_t asg[64]; for(int c=0;c<K;c++)asg[c]=-1;
      // random order over holes
      int *ord=malloc(holes*sizeof(int)); for(int i=0;i<holes;i++)ord[i]=hl[i]; for(int i=holes-1;i>0;i--){int j=rnd()%(i+1);int t=ord[i];ord[i]=ord[j];ord[j]=t;}
      int nh=holes, got=0;
      for(int q=0;q<nh;q++){ int s=ord[q]>>T,p=ord[q]&((1<<T)-1); const uint8_t*cc=setc[s]; int ok=1; for(int i=0;i<T;i++){int v=(p>>i)&1; if(asg[cc[i]]>=0&&asg[cc[i]]!=v){ok=0;break;}} if(!ok)continue; for(int i=0;i<T;i++)asg[cc[i]]=(p>>i)&1; got++; }
      for(int c=0;c<K;c++)A[(size_t)r*K+c]=asg[c]>=0?asg[c]:(rnd()&1);
      N++; recount(); fprintf(stderr,"greedy row %d: satisfied %d holes -> holes=%d\n",r,got,holes); free(ord); }
  } else recount();
  fprintf(stderr,"N=%d K=%d t=%d sets=%d holes=%d\n",N,K,T,NS,holes);
  clock_t t0=clock(); long it=0; int best=holes; static int tabu[1100][64]; long lastimp=0;
  while((double)(clock()-t0)/CLOCKS_PER_SEC<secs){
    if(holes==0){ char fn[512]; snprintf(fn,sizeof fn,"%s_%d.txt",out,N); save(fn); fprintf(stderr,"WROTE %s it=%ld t=%.1f\n",fn,it,(double)(clock()-t0)/CLOCKS_PER_SEC);
      if(N<=Nmin){printf("DONE N=%d %s\n",N,fn);return 0;}
      // delete row with fewest unique coverages
      int *u=calloc(N,sizeof(int)); for(int r=0;r<N;r++)for(int s=0;s<NS;s++){int p=pat(r,s);if(cnt[(s<<T)|p]==1)u[r]++;}
      int br=0;for(int r=1;r<N;r++)if(u[r]<u[br])br=r; fprintf(stderr,"delete row %d (unique %d; min/max over rows %d)\n",br,u[br],u[br]);
      free(u); memmove(A+(size_t)br*K,A+(size_t)(br+1)*K,(size_t)(N-1-br)*K); N--; recount(); best=holes; memset(tabu,0,sizeof tabu); lastimp=it;
      fprintf(stderr,"N=%d holes=%d\n",N,holes); continue; }
    it++;
    // random hole
    size_t hi=hl[rnd()%holes]; int s=hi>>T,p=hi&((1<<T)-1);
    const uint8_t*cc=setc[s];
    int bd=1<<30,br=-1,bc=-1,nb=0;
    for(int r=0;r<N;r++){ int q=pat(r,s)^p; if(q==0||(q&(q-1)))continue; int i=__builtin_ctz(q); int c=cc[i];
      if(tabu[r][c]>it) continue; int d=delta(r,c); if(d<bd){bd=d;br=r;bc=c;nb=1;} else if(d==bd){nb++;if(rnd()%nb==0){br=r;bc=c;}} }
    if(br<0){ // no distance-1 row: flip a random cell of a distance-2 row toward the hole
      for(int tries=0;tries<50&&br<0;tries++){int r=rnd()%N;int q=pat(r,s)^p; if(__builtin_popcount(q)==2){int i=(rnd()&1)?__builtin_ctz(q):31-__builtin_clz(q); br=r;bc=cc[i];bd=delta(r,bc);} }
      if(br<0)continue; }
    if(bd>0 && ur()>exp(-bd/Temp)) continue;
    apply(br,bc); tabu[br][bc]=it+20+rnd()%30;
    if(holes<best){best=holes;lastimp=it; if(it%1==0)fprintf(stderr,"it=%ld t=%.1f holes=%d\n",it,(double)(clock()-t0)/CLOCKS_PER_SEC,holes); if(savebest){char fn[512];snprintf(fn,sizeof fn,"%s_best_%d.txt",out,N);save(fn);} }
  }
  { char fn[512]; snprintf(fn,sizeof fn,"%s_cur_%d.txt",out,N); save(fn); fprintf(stderr,"end it=%ld holes=%d best=%d saved %s\n",it,holes,best,fn); }
  return 0; }
