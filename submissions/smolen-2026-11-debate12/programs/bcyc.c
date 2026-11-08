/* bcyc.c - debate 12 agent A (2026-11-08). Own code; the quotient idea follows debate 11 B's cycq.c.
 * Block-cyclic orbit annealer for CA(N; t, k, 2): Z_m acts on c column blocks of m columns each (k = c*m).
 * Rows: norb full orbits (each = m cyclic shifts of a generator word of length k, shifting every block
 * together) plus nconst block-constant rows (a c-bit pattern each, free to change).  N = norb*m + nconst.
 * The array is Z_m-invariant, so coverage is checked on one representative per rotation class of t-sets.
 * Cost = uncovered (class, tuple) pairs, exact and incremental. Moves: random generator bit, random const
 * block bit, or focus (pick a hole, sample R rows, flip one differing bit of the closest row). Metropolis at
 * fixed T; reload best after `reload` seconds without improvement.
 * usage: bcyc t m c norb nconst seed secs T outprefix [-f pf] [-R rows] [-r reloadsec] [-i genfile] [-q]
 * Writes <out>_gen.txt (best state) and <out>_<N>.txt (full unfolded array) at 0 holes.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>
#include <time.h>

static int t, m, c, k, norb, nconst, N, P;
static long nrep;
static uint16_t *rcol;        /* nrep*t representative columns */
static uint8_t *cnt;          /* nrep*P counts (N<=255) */
static long holes; static int *hl, *hp;
static uint8_t *gen;          /* norb*k */
static uint8_t *cst;          /* nconst*c */
static int32_t **blist; static long *blen; /* per block: packed (class<<3 | i) */
static uint64_t rs = 88172645463325252ULL;
static inline uint64_t xr(void){ rs ^= rs<<13; rs ^= rs>>7; rs ^= rs<<17; return rs; }
static inline long rndl(long n){ return (long)(((xr()>>32) * (uint64_t)n) >> 32); }
static inline double rndu(void){ return (xr()>>11) * (1.0/9007199254740992.0); }
static double now(void){ struct timespec ts; clock_gettime(CLOCK_MONOTONIC,&ts); return ts.tv_sec+1e-9*ts.tv_nsec; }
static inline void addh(long i){ hp[i]=(int)holes; hl[holes++]=(int)i; }
static inline void remh(long i){ int q=hp[i]; int last=hl[--holes]; hl[q]=last; hp[last]=q; hp[i]=-1; }
static inline int modm(int a){ a%=m; if(a<0) a+=m; return a; }

/* entry of orbit row (g,s) at column col */
static inline int gent(int g, int s, int col){ int j=col/m, x=col-j*m; return gen[(long)g*k + j*m + modm(x-s)]; }
static inline int tuple_orb(long r, int g, int s){ int p=0; const uint16_t *R=rcol+r*t; for(int l=0;l<t;l++) p=(p<<1)|gent(g,s,R[l]); return p; }
static inline int tuple_cst(long r, int q){ int p=0; const uint16_t *R=rcol+r*t; for(int l=0;l<t;l++) p=(p<<1)|cst[q*c + R[l]/m]; return p; }

static int cmpset(const int *a, const int *b){ for(int i=0;i<t;i++){ if(a[i]!=b[i]) return a[i]<b[i]?-1:1; } return 0; }
static void sortt(int *a){ for(int i=1;i<t;i++){ int v=a[i], j=i-1; while(j>=0 && a[j]>v){ a[j+1]=a[j]; j--; } a[j+1]=v; } }
static void build(void){
  int idx[8]; for(int i=0;i<t;i++) idx[i]=i; nrep=0; long cap=1<<16; rcol=malloc(cap*t*2);
  int rot[8];
  for(;;){
    int canon=1;
    for(int s=1;s<m && canon;s++){ for(int i=0;i<t;i++){ int j=idx[i]/m, x=idx[i]-j*m; rot[i]=j*m+modm(x+s); } sortt(rot); if(cmpset(rot,idx)<0) canon=0; }
    if(canon){ if(nrep==cap){ cap*=2; rcol=realloc(rcol,cap*t*2); } for(int i=0;i<t;i++) rcol[nrep*t+i]=(uint16_t)idx[i]; nrep++; }
    int i=t-1; while(i>=0 && idx[i]==k-t+i) i--; if(i<0) break; idx[i]++; for(int j=i+1;j<t;j++) idx[j]=idx[j-1]+1; }
  P=1<<t; cnt=calloc((size_t)nrep*P,1); hl=malloc(nrep*P*sizeof(int)); hp=malloc(nrep*P*sizeof(int));
  blen=calloc(c,sizeof(long)); blist=malloc(c*sizeof(int32_t*));
  for(long r=0;r<nrep;r++) for(int i=0;i<t;i++) blen[rcol[r*t+i]/m]++;
  for(int j=0;j<c;j++){ blist[j]=malloc(blen[j]*sizeof(int32_t)); blen[j]=0; }
  for(long r=0;r<nrep;r++) for(int i=0;i<t;i++){ int j=rcol[r*t+i]/m; blist[j][blen[j]++]=(int32_t)((r<<3)|i); }
}
static void recount(void){
  memset(cnt,0,(size_t)nrep*P); holes=0;
  for(long r=0;r<nrep;r++){ uint8_t *C=cnt+r*P;
    for(int g=0;g<norb;g++) for(int s=0;s<m;s++) C[tuple_orb(r,g,s)]++;
    for(int q=0;q<nconst;q++) C[tuple_cst(r,q)]++; }
  for(long i=0;i<nrep*P;i++){ hp[i]=-1; if(!cnt[i]) addh(i); }
}
/* flip generator cell (g, col); returns change in holes */
static int gflip(int g, int col){
  int d=0; int j=col/m, y=col-j*m; const int32_t *L=blist[j]; long n=blen[j];
  for(long e=0;e<n;e++){ long r=L[e]>>3; int i=L[e]&7; int xi=rcol[r*t+i]-j*m; int s=modm(xi-y);
    int p=tuple_orb(r,g,s); int pn=p^(1<<(t-1-i)); uint8_t *C=cnt+r*P;
    if(--C[p]==0){ d++; addh(r*P+p); } if(C[pn]++==0){ d--; remh(r*P+pn); } }
  gen[(long)g*k+col]^=1; return d;
}
/* flip const row q block j */
static int cflip(int q, int j){
  int d=0; const int32_t *L=blist[j]; long n=blen[j];
  for(long e=0;e<n;e++){ long r=L[e]>>3; int i=L[e]&7; const uint16_t *R=rcol+r*t; int first=1, mask=0;
    for(int l=0;l<t;l++) if(R[l]/m==j){ if(l<i) first=0; mask|=1<<(t-1-l); }
    if(!first) continue;
    int p=tuple_cst(r,q); int pn=p^mask; uint8_t *C=cnt+r*P;
    if(--C[p]==0){ d++; addh(r*P+p); } if(C[pn]++==0){ d--; remh(r*P+pn); } }
  cst[q*c+j]^=1; return d;
}
static void savegen(const char *fn){ FILE *o=fopen(fn,"w"); if(!o) return;
  for(int g=0;g<norb;g++){ for(int col=0;col<k;col++) fputc('0'+gen[(long)g*k+col],o); fputc('\n',o); }
  for(int q=0;q<nconst;q++){ for(int j=0;j<c;j++) fputc('0'+cst[q*c+j],o); fputc('\n',o); } fclose(o); }
static void savefull(const char *fn){ FILE *o=fopen(fn,"w");
  for(int g=0;g<norb;g++) for(int s=0;s<m;s++){ for(int col=0;col<k;col++){ fputc('0'+gent(g,s,col),o); fputc(col==k-1?'\n':' ',o); } }
  for(int q=0;q<nconst;q++){ for(int col=0;col<k;col++){ fputc('0'+cst[q*c+col/m],o); fputc(col==k-1?'\n':' ',o); } } fclose(o); }

int main(int argc, char **argv){
  if(argc<10){ fprintf(stderr,"usage: bcyc t m c norb nconst seed secs T outprefix [-f pf] [-R rows] [-r reloadsec] [-i genfile] [-q]\n"); return 2; }
  t=atoi(argv[1]); m=atoi(argv[2]); c=atoi(argv[3]); norb=atoi(argv[4]); nconst=atoi(argv[5]); rs^=strtoull(argv[6],0,10)*0x9E3779B97F4A7C15ULL;
  double secs=atof(argv[7]), T=atof(argv[8]); const char *out=argv[9]; double pf=0.5; int R=8; const char *init=NULL; int quiet=0; double reload=0;
  for(int a=10;a<argc;a++){ if(!strcmp(argv[a],"-f")) pf=atof(argv[++a]); else if(!strcmp(argv[a],"-R")) R=atoi(argv[++a]); else if(!strcmp(argv[a],"-i")) init=argv[++a];
    else if(!strcmp(argv[a],"-r")) reload=atof(argv[++a]); else if(!strcmp(argv[a],"-q")) quiet=1; }
  k=c*m; N=norb*m+nconst; if(t>7||N>255||k>65000){ fprintf(stderr,"limits\n"); return 2; }
  build();
  gen=malloc((long)norb*k); cst=malloc(nconst*c+1);
  for(long i=0;i<(long)norb*k;i++) gen[i]=xr()&1; for(int i=0;i<nconst*c;i++) cst[i]=xr()&1;
  if(nconst>=1) for(int j=0;j<c;j++) cst[j]=0; if(nconst>=2) for(int j=0;j<c;j++) cst[c+j]=1;
  if(init){ FILE *fi=fopen(init,"r"); if(!fi){ perror(init); return 2; } char line[70000]; int ln=0;
    while(fgets(line,sizeof line,fi)){ int len=0; for(char*p=line;*p=='0'||*p=='1';p++) len++;
      if(ln<norb && len>=k){ for(int i=0;i<k;i++) gen[(long)ln*k+i]=line[i]=='1'; ln++; }
      else if(ln>=norb && ln<norb+nconst && len>=c){ for(int i=0;i<c;i++) cst[(ln-norb)*c+i]=line[i]=='1'; ln++; } }
    fclose(fi); }
  recount(); long best=holes; uint8_t *bg=malloc((long)norb*k), *bc=malloc(nconst*c+1); memcpy(bg,gen,(long)norb*k); memcpy(bc,cst,nconst*c);
  char fn[512]; snprintf(fn,sizeof fn,"%s_gen.txt",out); savegen(fn);
  fprintf(stderr,"N=%d (%d orbits of Z_%d on %d blocks, k=%d, const=%d) t=%d classes=%ld holes=%ld\n",N,norb,m,c,k,nconst,t,nrep,holes);
  double t0=now(), tl=t0, tb=t0; long it=0, acc=0; long ncells=(long)norb*k, nall=ncells+(long)nconst*c;
  while(holes>0){
    it++;
    if((it&255)==0){ double tn=now(); if(tn-t0>secs) break;
      if(!quiet && tn-tl>=30){ tl=tn; fprintf(stderr,"t=%.0f it=%ld acc=%ld holes=%ld best=%ld\n",tn-t0,it,acc,holes,best); }
      if(reload>0 && tn-tb>reload){ memcpy(gen,bg,(long)norb*k); memcpy(cst,bc,nconst*c); recount(); tb=tn; } }
    int d; int isc=0, g=0, col=0, q=0, j=0;
    if(rndu()<pf){ long h=hl[rndl(holes)]; long r=h/P; int p=(int)(h%P); int bd=99, bdiff=0, brow=0;
      for(int u=0;u<R;u++){ int row=(int)rndl(N); int pp = row<norb*m ? tuple_orb(r,row/m,row%m) : tuple_cst(r,row-norb*m); int diff=pp^p; int dd=__builtin_popcount(diff); if(dd<bd){ bd=dd; bdiff=diff; brow=row; } }
      int nb=__builtin_popcount(bdiff); int pick=(int)rndl(nb); int bi=0,cb=0; for(int i=0;i<t;i++) if(bdiff>>(t-1-i)&1){ if(cb==pick){ bi=i; break; } cb++; }
      int colr=rcol[r*t+bi];
      if(brow<norb*m){ g=brow/m; int s=brow%m; int jj=colr/m, x=colr-jj*m; col=jj*m+modm(x-s); }
      else { isc=1; q=brow-norb*m; j=colr/m; }
    } else { long x=rndl(nall); if(x<ncells){ g=(int)(x/k); col=(int)(x%k); } else { isc=1; x-=ncells; q=(int)(x/c); j=(int)(x%c); } }
    d = isc ? cflip(q,j) : gflip(g,col);
    if(d>0 && rndu()>=exp(-d/T)){ if(isc) cflip(q,j); else gflip(g,col); continue; }
    acc++; if(holes<best){ best=holes; memcpy(bg,gen,(long)norb*k); memcpy(bc,cst,nconst*c); savegen(fn); tb=now(); }
  }
  double el=now()-t0; fprintf(stderr,"end t=%.0f it=%ld acc=%ld holes=%ld best=%ld\n",el,it,acc,holes,best);
  if(holes==0){ snprintf(fn,sizeof fn,"%s_%d.txt",out,N); savefull(fn); printf("FOUND N=%d file=%s\n",N,fn); return 0; }
  printf("BEST quotient holes=%ld at N=%d (gen in %s_gen.txt)\n",best,N,out); return 1;
}
