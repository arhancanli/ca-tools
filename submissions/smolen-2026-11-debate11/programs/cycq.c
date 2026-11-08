/* cycq.c - debate 11 agent B (2026-11-08). Own code. Quotient version of cyc.c.
 * Cyclic-orbit annealer for CA(N; t, k, 2), t <= 6, k <= 32, N = m*k + nconst:
 * rows = all k cyclic shifts of m generators, plus nconst constant rows (0 or 2: all-0 and all-1; 1 = all-0).
 * Because the array is Z_k-invariant, coverage is checked on one representative per rotation class of
 * t-sets (about C(k,t)/k classes).  Cost = uncovered (class, pattern) pairs, exact and incremental:
 * a generator bit flip (g, j) changes, for each class representative S and each c in S, the pattern of
 * row (g, s = c - j) on S.  Moves: random generator bit, or focus (Nurmela 2004: pick a hole, sample R
 * rows, flip one differing bit of the closest row).  Metropolis at fixed T; reload-best every `reload`
 * seconds without improvement (0 = never).
 * usage: cycq t k m nconst seed secs T outprefix [-f pf] [-R rows] [-i genfile] [-r reloadsec] [-m period] [-q]
 *   -m period: Z_period acts on each block of `period` consecutive columns (period | k); orbits have `period` rows; default k.
 * Writes <outprefix>_gen.txt (generators of the best state) and <outprefix>_<N>.txt (full array) at 0 holes.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>
#include <time.h>
#include <immintrin.h>

static int t, k, m, nconst, N, P, NG, mp; static uint32_t bmask0;
static long nrep;
static uint32_t *rmask; static uint8_t (*rcol)[6];
static uint16_t *cnt; static long holes; static int *hl, *hp;
static uint32_t *gen, full;
static uint64_t rs = 88172645463325252ULL;
static inline uint64_t xr(void){ rs ^= rs<<13; rs ^= rs>>7; rs ^= rs<<17; return rs; }
static inline long rndl(long n){ return (long)(((xr()>>32) * (uint64_t)n) >> 32); }
static inline double rndu(void){ return (xr()>>11) * (1.0/9007199254740992.0); }
static double now(void){ struct timespec ts; clock_gettime(CLOCK_MONOTONIC,&ts); return ts.tv_sec+1e-9*ts.tv_nsec; }
static inline uint32_t rotl(uint32_t v, int s){ s%=mp; if(s<0) s+=mp; if(s==0) return v;
  if(mp==k) return ((v<<s)|(v>>(k-s)))&full;
  uint32_t r=0; for(int b=0;b<k;b+=mp){ uint32_t blk=(v>>b)&bmask0; r|=(((blk<<s)|(blk>>(mp-s)))&bmask0)<<b; } return r; }
static inline void addh(long i){ hp[i]=(int)holes; hl[holes++]=(int)i; }
static inline void remh(long i){ int q=hp[i]; int last=hl[--holes]; hl[q]=last; hp[last]=q; hp[i]=-1; }

static void build(void){
  int idx[6]; for(int i=0;i<t;i++) idx[i]=i; nrep=0; long cap=1<<16; rmask=malloc(cap*4); rcol=malloc(cap*6);
  for(;;){ uint32_t M=0; for(int i=0;i<t;i++) M|=1u<<idx[i];
    int canon=1; for(int s=1;s<mp && canon;s++) if(rotl(M,s)<M) canon=0;
    if(canon){ if(nrep==cap){ cap*=2; rmask=realloc(rmask,cap*4); rcol=realloc(rcol,cap*6); } rmask[nrep]=M; for(int i=0;i<t;i++) rcol[nrep][i]=idx[i]; nrep++; }
    int i=t-1; while(i>=0 && idx[i]==k-t+i) i--; if(i<0) break; idx[i]++; for(int j=i+1;j<t;j++) idx[j]=idx[j-1]+1; }
  P=1<<t; cnt=calloc((size_t)nrep*P,2); hl=malloc(nrep*P*sizeof(int)); hp=malloc(nrep*P*sizeof(int));
}
static void recount(void){
  memset(cnt,0,(size_t)nrep*P*2); holes=0;
  for(long r=0;r<nrep;r++){ uint16_t *C=cnt+r*P; uint32_t M=rmask[r];
    for(int g=0;g<m;g++) for(int s=0;s<mp;s++) C[_pext_u32(rotl(gen[g],s),M)]++;
    if(nconst>=1) C[0]++; if(nconst>=2) C[P-1]++; }
  for(long i=0;i<nrep*P;i++){ hp[i]=-1; if(!cnt[i]) addh(i); }
}
/* flip generator bit (g,j); return change in holes */
static inline int gflip(int g, int j){
  int d=0; uint32_t v=gen[g];
  for(long r=0;r<nrep;r++){ uint32_t M=rmask[r]; uint16_t *C=cnt+r*P;
    for(int i=0;i<t;i++){ int c=rcol[r][i]; if(c/mp!=j/mp) continue; int s=(c%mp)-(j%mp); if(s<0) s+=mp; uint32_t row=rotl(v,s); int p=(int)_pext_u32(row,M); int bit=1<<i;
      if(--C[p]==0){ d++; addh(r*P+p); } if(C[p^bit]++==0){ d--; remh(r*P+(p^bit)); } } }
  gen[g]=v^(1u<<j); return d;
}
static void savegen(const char *fn){ FILE *o=fopen(fn,"w"); for(int g=0;g<m;g++){ for(int c=0;c<k;c++) fputc('0'+((gen[g]>>c)&1),o), fputc(c==k-1?'\n':' ',o); } fclose(o); }
static void savefull(const char *fn){ FILE *o=fopen(fn,"w");
  for(int g=0;g<m;g++) for(int s=0;s<mp;s++){ uint32_t row=rotl(gen[g],s); for(int c=0;c<k;c++) fputc('0'+((row>>c)&1),o), fputc(c==k-1?'\n':' ',o); }
  for(int c=0;c<nconst;c++){ for(int j=0;j<k;j++) fputc(c==0?'0':'1',o), fputc(j==k-1?'\n':' ',o); } fclose(o); }

int main(int argc, char **argv){
  if(argc<9){ fprintf(stderr,"usage: cycq t k m nconst seed secs T outprefix [-f pf] [-R rows] [-i genfile] [-r reloadsec] [-q]\n"); return 2; }
  t=atoi(argv[1]); k=atoi(argv[2]); m=atoi(argv[3]); nconst=atoi(argv[4]); rs^=strtoull(argv[5],0,10)*0x9E3779B97F4A7C15ULL;
  double secs=atof(argv[6]), T=atof(argv[7]); const char *out=argv[8]; double pf=0.5; int R=8; const char *init=NULL; int quiet=0; double reload=0; int exact=0; mp=k;
  for(int a=9;a<argc;a++){ if(!strcmp(argv[a],"-f")) pf=atof(argv[++a]); else if(!strcmp(argv[a],"-R")) R=atoi(argv[++a]); else if(!strcmp(argv[a],"-i")) init=argv[++a];
    else if(!strcmp(argv[a],"-r")) reload=atof(argv[++a]); else if(!strcmp(argv[a],"-q")) quiet=1; else if(!strcmp(argv[a],"-m")) mp=atoi(argv[++a]); else if(!strcmp(argv[a],"-X")) exact=1; }
  if(k>32||t>6||nconst>2||m>64){ fprintf(stderr,"limits\n"); return 2; }
  if(k%mp){ fprintf(stderr,"-m must divide k\n"); return 2; } bmask0=(mp==32)?0xffffffffu:((1u<<mp)-1);
  full=(k==32)?0xffffffffu:((1u<<k)-1); N=m*mp+nconst; NG=m*mp; build();
  gen=malloc(m*4); for(int g=0;g<m;g++) gen[g]=xr()&full;
  if(init){ FILE *fi=fopen(init,"r"); if(!fi){ perror(init); return 2; } char line[4096]; int ln=0;
    while(fgets(line,sizeof line,fi)&&ln<m){ uint32_t v=0; int c=0; for(char*p=line;*p&&c<k;p++) if(*p=='0'||*p=='1'){ if(*p=='1') v|=1u<<c; c++; } if(c<k) continue; gen[ln++]=v; } fclose(fi); }
  recount(); long best=holes; uint32_t *bestgen=malloc(m*4); memcpy(bestgen,gen,m*4);
  char fn[512]; snprintf(fn,sizeof fn,"%s_gen.txt",out); savegen(fn);
  fprintf(stderr,"N=%d (m=%d orbits of %d, k=%d, const=%d) t=%d classes=%ld holes=%ld\n",N,m,mp,k,nconst,t,nrep,holes);

  if(exact){ /* exhaustive focused repair: for each hole (S,p) and each row (g,s) at Hamming distance d<=3 from p on S,
                apply the d forced generator flips, then up to 3-d free flips (all pairs / singles); stop at 0 holes */
    long tried=0; int done=0; int NGB=m*mp; /* generator bits: g*mp.. no: bits are (g, j) with j in 0..k-1 */
    int nb=m*k;
    for(long hi=0; hi<holes && !done; hi++){ long h=hl[hi]; long r=h/P; int p=(int)(h%P); uint32_t M=rmask[r];
      for(int g=0;g<m && !done;g++) for(int s=0;s<mp && !done;s++){ int diff=(int)_pext_u32(rotl(gen[g],s),M)^p; int d=__builtin_popcount(diff); if(d>3||d==0) continue;
        int fj[3],nf=0; for(int i=0;i<t;i++) if(diff>>i&1){ int c=rcol[r][i]; int u=(c%mp)-s; if(u<0) u+=mp; fj[nf++]=(c/mp)*mp+u; }
        for(int i=0;i<nf;i++) gflip(g,fj[i]); tried++;
        if(holes==0) done=1;
        else if(d<=2){ for(int x=0;x<nb && !done;x++){ int g1=x/k,j1=x%k; gflip(g1,j1); tried++; if(holes==0){ done=1; break; }
            if(d==1){ for(int y=x+1;y<nb;y++){ int g2=y/k,j2=y%k; gflip(g2,j2); tried++; if(holes==0){ done=1; break; } gflip(g2,j2); } }
            if(!done) gflip(g1,j1); } }
        if(!done) for(int i=nf-1;i>=0;i--) gflip(g,fj[i]);
      } }
    fprintf(stderr,"exact: tried=%ld holes=%ld\n",tried,holes);
    if(holes==0){ snprintf(fn,sizeof fn,"%s_%d.txt",out,N); savefull(fn); savegen(fn); snprintf(fn,sizeof fn,"%s_gen.txt",out); savegen(fn); snprintf(fn,sizeof fn,"%s_%d.txt",out,N); savefull(fn); printf("FOUND N=%d file=%s\n",N,fn); return 0; }
    printf("exact repair failed, holes=%ld\n",holes); return 1; }
  double t0=now(), tl=t0, tb=t0; long it=0, acc=0;
  while(holes>0){
    it++;
    if((it&1023)==0){ double tn=now(); if(tn-t0>secs) break;
      if(!quiet && tn-tl>=30){ tl=tn; fprintf(stderr,"t=%.0f it=%ld acc=%ld holes=%ld best=%ld\n",tn-t0,it,acc,holes,best); }
      if(reload>0 && tn-tb>reload){ memcpy(gen,bestgen,m*4); recount(); tb=tn; } }
    int g,j,d;
    if(rndu()<pf){ long h=hl[rndl(holes)]; long r=h/P; int p=(int)(h%P); uint32_t M=rmask[r]; int bg=-1,bs=0,bd=99,bdiff=0;
      for(int q=0;q<R;q++){ int x=(int)rndl(NG); int gg=x/mp, s=x%mp; int diff=(int)_pext_u32(rotl(gen[gg],s),M)^p; int dd=__builtin_popcount(diff); if(dd<bd){ bd=dd; bg=gg; bs=s; bdiff=diff; } }
      int nb=__builtin_popcount(bdiff); int pick=(int)rndl(nb); int bi=0,cntb=0; for(int i=0;i<t;i++) if(bdiff>>i&1){ if(cntb==pick){ bi=i; break; } cntb++; }
      int c=rcol[r][bi]; g=bg; { int u=(c%mp)-bs; if(u<0) u+=mp; j=(c/mp)*mp+u; }
    } else { long x=rndl((long)m*k); g=(int)(x/k); j=(int)(x%k); }
    d=gflip(g,j); if(d>0 && rndu()>=exp(-d/T)){ gflip(g,j); continue; }
    acc++; if(holes<best){ best=holes; memcpy(bestgen,gen,m*4); savegen(fn); tb=now(); }
  }
  double el=now()-t0; fprintf(stderr,"end t=%.0f it=%ld acc=%ld holes=%ld best=%ld\n",el,it,acc,holes,best);
  if(holes==0){ snprintf(fn,sizeof fn,"%s_%d.txt",out,N); savefull(fn); printf("FOUND N=%d file=%s\n",N,fn); return 0; }
  printf("BEST quotient holes=%ld at N=%d (gen in %s_gen.txt)\n",best,N,out); return 1;
}
