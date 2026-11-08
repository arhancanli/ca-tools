/* gcycq.c - debate 12 agent B (2026-11-08). Own code; generalizes debate-11 cycq.c (same quotient idea).
 * Cyclic-orbit annealer for binary CA(N; t, k, 2), t <= 6, k <= 32, with MIXED orbit sizes and an optional
 * complement twist.
 *   Group element sigma = rotate columns by 1 (and, with -c, also complement all symbols).  The array is the
 *   union of sigma-orbits of generator words.  Orbit i has "period" d_i | k: its word is determined by d_i bits
 *   b[0..d_i-1]: w[c] = b[c mod d_i] (xor 1 when -c, d_i odd and (c div d_i) odd), and its rows are
 *   sigma^s(w) = rotl(w, s) [xor all-ones when -c and s odd], s = 0..d_i-1.   N = sum d_i.
 *   Period 1 without -c = a constant row; with -c the pair {0...0, 1...1} is one period-2 orbit.
 *   Coverage: a sigma-invariant array covers a t-set S iff it covers every rotation of S (with -c the
 *   pattern set on sigma(S) is the complement of the pattern set on S, so it is full iff that one is), so the
 *   cost = number of uncovered (rotation class, pattern) pairs is exact; it is updated incrementally.
 *   Moves: random generator bit, or Nurmela focus (pick a hole, sample R rows, flip one differing bit of the
 *   closest row).  Metropolis at fixed T, reload best every -r seconds without improvement.
 * usage: gcycq t k seed secs T outprefix -o SPEC [-c] [-f pf] [-R rows] [-i genfile] [-r reloadsec] [-q]
 *   SPEC = comma list of periods, "18x14,6,1,1" = 14 orbits of period 18, one of 6, two constants.
 * Writes <outprefix>_gen.txt (best generators: one line per orbit "period bits") and <outprefix>_<N>.txt at 0 holes.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>
#include <time.h>
#if defined(__x86_64__) && defined(__BMI2__)
#include <immintrin.h>
#else
/* portable fallback (Apple silicon has no PEXT instruction): gather the bits of x selected by m */
static inline uint32_t _pext_u32(uint32_t x, uint32_t m){ uint32_t r=0; int b=0; while(m){ uint32_t low=m&(0u-m); if(x&low) r|=1u<<b; b++; m&=m-1; } return r; }
#endif

#define MAXO 128
static int t, k, N, P, twist, norb; static int per[MAXO], off[MAXO]; static uint32_t gen[MAXO], bestgen[MAXO];
static long nrep;
static uint32_t *rmask; static uint8_t (*rcol)[6];
static uint16_t *cnt; static long holes; static int *hl, *hp;
static uint32_t full;
static uint64_t rs = 88172645463325252ULL;
static inline uint64_t xr(void){ rs ^= rs<<13; rs ^= rs>>7; rs ^= rs<<17; return rs; }
static inline long rndl(long n){ return (long)(((xr()>>32) * (uint64_t)n) >> 32); }
static inline double rndu(void){ return (xr()>>11) * (1.0/9007199254740992.0); }
static double now(void){ struct timespec ts; clock_gettime(CLOCK_MONOTONIC,&ts); return ts.tv_sec+1e-9*ts.tv_nsec; }
static inline uint32_t rotl(uint32_t v, int s){ s%=k; if(s<0) s+=k; if(s==0) return v; return ((v<<s)|(v>>(k-s)))&full; }
static inline uint32_t roww(int i, int s){ uint32_t w=rotl(gen[i],s); if(twist && (s&1)) w^=full; return w; }
static inline void addh(long i){ hp[i]=(int)holes; hl[holes++]=(int)i; }
static inline void remh(long i){ int q=hp[i]; int last=hl[--holes]; hl[q]=last; hp[last]=q; hp[i]=-1; }

/* word of orbit i from its d bits b (bit j of b = b[j]) */
static uint32_t mkword(int i, uint32_t b){ int d=per[i]; uint32_t w=0;
  for(int c=0;c<k;c++){ int bit=(b>>(c%d))&1; if(twist && (d&1) && ((c/d)&1)) bit^=1; w|=(uint32_t)bit<<c; } return w; }
/* mask of positions toggled by generator bit j of orbit i */
static inline uint32_t jmask(int i, int j){ int d=per[i]; uint32_t m=0; for(int c=j;c<k;c+=d) m|=1u<<c; return m; }

static void build(void){
  int idx[6]; for(int i=0;i<t;i++) idx[i]=i; nrep=0; long cap=1<<16; rmask=malloc(cap*4); rcol=malloc(cap*6);
  for(;;){ uint32_t M=0; for(int i=0;i<t;i++) M|=1u<<idx[i];
    int canon=1; for(int s=1;s<k && canon;s++) if(rotl(M,s)<M) canon=0;
    if(canon){ if(nrep==cap){ cap*=2; rmask=realloc(rmask,cap*4); rcol=realloc(rcol,cap*6); } rmask[nrep]=M; for(int i=0;i<t;i++) rcol[nrep][i]=idx[i]; nrep++; }
    int i=t-1; while(i>=0 && idx[i]==k-t+i) i--; if(i<0) break; idx[i]++; for(int j=i+1;j<t;j++) idx[j]=idx[j-1]+1; }
  P=1<<t; cnt=calloc((size_t)nrep*P,2); hl=malloc(nrep*P*sizeof(int)); hp=malloc(nrep*P*sizeof(int));
}
static void recount(void){
  memset(cnt,0,(size_t)nrep*P*2); holes=0;
  for(long r=0;r<nrep;r++){ uint16_t *C=cnt+r*P; uint32_t M=rmask[r];
    for(int i=0;i<norb;i++) for(int s=0;s<per[i];s++) C[_pext_u32(roww(i,s),M)]++; }
  for(long i=0;i<nrep*P;i++){ hp[i]=-1; if(!cnt[i]) addh(i); }
}
/* flip generator bit j (0<=j<per[i]) of orbit i; return change in holes */
static inline int gflip(int i, int j){
  int d=0, dd=per[i];
  for(long r=0;r<nrep;r++){ uint32_t M=rmask[r]; uint16_t *C=cnt+r*P; int sv[6]; int done=0;
    for(int b=0;b<t;b++){ int s=(rcol[r][b]-j)%dd; if(s<0) s+=dd; sv[b]=s; }
    for(int b=0;b<t;b++){ if(done>>b&1) continue; int diff=0; for(int b2=b;b2<t;b2++) if(sv[b2]==sv[b]){ diff|=1<<b2; done|=1<<b2; }
      int p=(int)_pext_u32(roww(i,sv[b]),M);
      if(--C[p]==0){ d++; addh(r*P+p); } if(C[p^diff]++==0){ d--; remh(r*P+(p^diff)); } } }
  gen[i]^=jmask(i,j); return d;
}
static void savegen(const char *fn){ FILE *o=fopen(fn,"w"); for(int i=0;i<norb;i++){ fprintf(o,"%d ",per[i]); for(int c=0;c<k;c++) fputc('0'+((gen[i]>>c)&1),o); fputc('\n',o); } fclose(o); }
static void savefull(const char *fn){ FILE *o=fopen(fn,"w");
  for(int i=0;i<norb;i++) for(int s=0;s<per[i];s++){ uint32_t row=roww(i,s); for(int c=0;c<k;c++) fputc('0'+((row>>c)&1),o), fputc(c==k-1?'\n':' ',o); }
  fclose(o); }

int main(int argc, char **argv){
  if(argc<8){ fprintf(stderr,"usage: gcycq t k seed secs T outprefix -o SPEC [-c] [-f pf] [-R rows] [-i genfile] [-r reloadsec] [-q]\n"); return 2; }
  t=atoi(argv[1]); k=atoi(argv[2]); rs^=strtoull(argv[3],0,10)*0x9E3779B97F4A7C15ULL;
  double secs=atof(argv[4]), T=atof(argv[5]); const char *out=argv[6]; double pf=0.5; int R=8; const char *init=NULL; int quiet=0; double reload=0; const char *spec=NULL;
  for(int a=7;a<argc;a++){ if(!strcmp(argv[a],"-f")) pf=atof(argv[++a]); else if(!strcmp(argv[a],"-R")) R=atoi(argv[++a]); else if(!strcmp(argv[a],"-i")) init=argv[++a];
    else if(!strcmp(argv[a],"-r")) reload=atof(argv[++a]); else if(!strcmp(argv[a],"-q")) quiet=1; else if(!strcmp(argv[a],"-c")) twist=1; else if(!strcmp(argv[a],"-o")) spec=argv[++a]; }
  if(k>32||t>6||!spec){ fprintf(stderr,"limits / need -o\n"); return 2; }
  if(twist && (k&1)){ fprintf(stderr,"-c needs even k\n"); return 2; }
  full=(k==32)?0xffffffffu:((1u<<k)-1);
  { char buf[1024]; strncpy(buf,spec,1023); buf[1023]=0; norb=0; for(char *tok=strtok(buf,","); tok; tok=strtok(NULL,",")){ int d,m=1; char *x=strchr(tok,'x'); if(x){ *x=0; m=atoi(x+1); } d=atoi(tok);
      if(d<1||k%d){ fprintf(stderr,"period %d must divide k\n",d); return 2; }
      if(twist && (d&1) && ((k/d)&1)){ fprintf(stderr,"with -c an odd period %d needs k/d even\n",d); return 2; }
      for(int q=0;q<m;q++){ if(norb>=MAXO){ fprintf(stderr,"too many orbits\n"); return 2; } per[norb++]=d; } } }
  N=0; for(int i=0;i<norb;i++){ off[i]=N; N+=per[i]; }
  build();
  for(int i=0;i<norb;i++) gen[i]=mkword(i,(uint32_t)xr());
  if(init){ FILE *fi=fopen(init,"r"); if(!fi){ perror(init); return 2; } char line[4096]; int ln=0;
    while(fgets(line,sizeof line,fi)&&ln<norb){ int d; char *p=line; d=(int)strtol(p,&p,10); if(d!=per[ln]) { fprintf(stderr,"init period mismatch at orbit %d\n",ln); return 2; }
      uint32_t v=0; int c=0; for(;*p&&c<k;p++) if(*p=='0'||*p=='1'){ if(*p=='1') v|=1u<<c; c++; } if(c<k) continue; gen[ln++]=v; } fclose(fi); }
  recount(); long best=holes; memcpy(bestgen,gen,sizeof gen);
  char fn[512]; snprintf(fn,sizeof fn,"%s_gen.txt",out); savegen(fn);
  fprintf(stderr,"N=%d (%d orbits, spec %s, twist=%d) t=%d k=%d classes=%ld holes=%ld\n",N,norb,spec,twist,t,k,nrep,holes);
  double t0=now(), tl=t0, tb=t0; long it=0, acc=0;
  while(holes>0){
    it++;
    if((it&1023)==0){ double tn=now(); if(tn-t0>secs) break;
      if(!quiet && tn-tl>=30){ tl=tn; fprintf(stderr,"t=%.0f it=%ld acc=%ld holes=%ld best=%ld\n",tn-t0,it,acc,holes,best); }
      if(reload>0 && tn-tb>reload){ memcpy(gen,bestgen,sizeof gen); recount(); tb=tn; } }
    int oi,j,d;
    if(rndu()<pf){ long h=hl[rndl(holes)]; long r=h/P; int p=(int)(h%P); uint32_t M=rmask[r]; int bi=-1,bs=0,bd=99,bdiff=0;
      for(int q=0;q<R;q++){ int x=(int)rndl(N); int i=norb-1; while(off[i]>x) i--; int s=x-off[i];
        int diff=(int)_pext_u32(roww(i,s),M)^p; int dd=__builtin_popcount(diff); if(dd<bd){ bd=dd; bi=i; bs=s; bdiff=diff; } }
      int nb=__builtin_popcount(bdiff); int pick=(int)rndl(nb); int b=0,cntb=0; for(int i=0;i<t;i++) if(bdiff>>i&1){ if(cntb==pick){ b=i; break; } cntb++; }
      int c=rcol[r][b]; oi=bi; j=(c-bs)%per[oi]; if(j<0) j+=per[oi];
    } else { int x=(int)rndl(N); oi=norb-1; while(off[oi]>x) oi--; j=x-off[oi]; }
    d=gflip(oi,j); if(d>0 && rndu()>=exp(-d/T)){ gflip(oi,j); continue; }
    acc++; if(holes<best){ best=holes; memcpy(bestgen,gen,sizeof gen); savegen(fn); tb=now(); }
  }
  double el=now()-t0; fprintf(stderr,"end t=%.0f it=%ld acc=%ld holes=%ld best=%ld\n",el,it,acc,holes,best);
  { long h1=holes; recount(); if(holes!=h1) fprintf(stderr,"SELFCHECK MISMATCH incremental=%ld recount=%ld\n",h1,holes); else fprintf(stderr,"selfcheck ok\n"); }
  if(holes==0){ snprintf(fn,sizeof fn,"%s_%d.txt",out,N); savefull(fn); printf("FOUND N=%d file=%s\n",N,fn); return 0; }
  printf("BEST quotient holes=%ld at N=%d (gen in %s_gen.txt)\n",best,N,out); return 1;
}
