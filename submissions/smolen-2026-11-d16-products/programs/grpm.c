/* grpm.c (debate15 A, own code, after grpq.c of debate 14 A): quotient annealer for binary CA(N; t, k, 2) whose rows
 * are the orbits of generator words under a permutation group G on the columns (spec from mkgrp.py: the left regular
 * action of any finite group, optionally plus one fixed column), with MIXED orbit sizes: word g is constant on the
 * column blocks of a subgroup H_g (so its orbit has |G|/|H_g| rows, listed by coset representatives). Coverage is
 * counted exactly on one representative per G-orbit of t-sets, incrementally. Plain C, no intrinsics.
 * usage: grpm t SPEC seed secs T outprefix [-r reloadsec] [-i genfile]
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>
#include <time.h>
#define MAXK 40
#define MAXG 64
#define MAXW 64
static int t,k,G,m,N,P,nrep; static int un0=-1, corb[MAXK];
static int act[MAXG][MAXK], iact[MAXG][MAXK];
static int whoN[MAXK][MAXK], who[MAXK][MAXK][MAXG];   /* who[o][c] = list of a with act[a][o]==c */
static int ncos[MAXW], cosrep[MAXW][MAXG], cosidx[MAXW][MAXG]; /* per word: coset reps and a -> coset index */
static int nblk[MAXW], blksz[MAXW][MAXK], blk[MAXW][MAXK][MAXG];
static uint64_t gen[MAXW], best[MAXW];
static uint64_t *rmask; static uint8_t (*rcol)[6]; static uint16_t *cnt; static long holes; static int *hl,*hp;
static uint64_t rs=88172645463325252ULL;
static inline uint64_t xr(void){rs^=rs<<13;rs^=rs>>7;rs^=rs<<17;return rs;}
static inline long rndl(long n){return (long)(((xr()>>32)*(uint64_t)n)>>32);}
static inline double rndu(void){return (xr()>>11)*(1.0/9007199254740992.0);}
static double now(void){struct timespec ts;clock_gettime(CLOCK_MONOTONIC,&ts);return ts.tv_sec+1e-9*ts.tv_nsec;}
static inline void addh(long i){hp[i]=(int)holes;hl[holes++]=(int)i;}
static inline void remh(long i){int q=hp[i];int last=hl[--holes];hl[q]=last;hp[last]=q;hp[i]=-1;}
static void readspec(const char*fn){
  FILE*f=fopen(fn,"r"); if(!f){perror(fn);exit(1);}
  if(fscanf(f,"%d %d",&k,&G)!=2)exit(2); if(k>MAXK||G>MAXG){fprintf(stderr,"too big\n");exit(1);}
  for(int a=0;a<G;a++)for(int c=0;c<k;c++){ if(fscanf(f,"%d",&act[a][c])!=1)exit(2); }
  for(int a=0;a<G;a++)for(int c=0;c<k;c++)iact[a][act[a][c]]=c;
  for(int o=0;o<k;o++)for(int c=0;c<k;c++)whoN[o][c]=0;
  for(int a=0;a<G;a++)for(int o=0;o<k;o++){int c=act[a][o]; who[o][c][whoN[o][c]++]=a;}
  if(fscanf(f,"%d",&m)!=1)exit(2); if(m>MAXW){fprintf(stderr,"too many words\n");exit(1);}
  N=0;
  for(int g=0;g<m;g++){
    if(fscanf(f,"%d",&ncos[g])!=1)exit(2); for(int i=0;i<ncos[g];i++)if(fscanf(f,"%d",&cosrep[g][i])!=1)exit(2);
    if(fscanf(f,"%d",&nblk[g])!=1)exit(2);
    for(int b=0;b<nblk[g];b++){ if(fscanf(f,"%d",&blksz[g][b])!=1)exit(2); for(int i=0;i<blksz[g][b];i++)if(fscanf(f,"%d",&blk[g][b][i])!=1)exit(2); }
    N+=ncos[g];
    /* coset index of every a: a is in coset rep*H; H = stabilizer; find rep r with r^-1 a in H.
       We do not have H explicitly; use blocks: a and r are in the same left coset iff a^-1 and r^-1 map every column into... simpler:
       the rows of a and r coincide for every H-invariant word iff for all c, iact[a][c] and iact[r][c] lie in the same block. */
    for(int a=0;a<G;a++){ cosidx[g][a]=-1;
      for(int i=0;i<ncos[g]&&cosidx[g][a]<0;i++){ int r=cosrep[g][i], ok=1;
        for(int c=0;c<k&&ok;c++){ int x=iact[a][c], y=iact[r][c]; int bx=-1,by=-1; for(int b=0;b<nblk[g];b++)for(int j=0;j<blksz[g][b];j++){ if(blk[g][b][j]==x)bx=b; if(blk[g][b][j]==y)by=b; } if(bx!=by)ok=0; }
        if(ok)cosidx[g][a]=i; }
      if(cosidx[g][a]<0){fprintf(stderr,"coset index failed word %d elt %d\n",g,a);exit(1);} }
  }
  fclose(f);
}
static inline uint64_t img(uint64_t M,int a){ uint64_t r=0; for(int c=0;c<k;c++) if(M>>c&1) r|=1ull<<act[a][c]; return r; }
static void build(void){
  int idx[6]; for(int i=0;i<t;i++)idx[i]=i; nrep=0; long cap=1<<16; rmask=malloc(cap*8); rcol=malloc(cap*6);
  for(int c=0;c<k;c++){ corb[c]=c; for(int a=0;a<G;a++) if(act[a][c]<corb[c]) corb[c]=act[a][c]; }
  for(;;){ uint64_t M=0; for(int i=0;i<t;i++)M|=1ull<<idx[i]; int canon=1;
    if(un0>=0){ for(int i=0;i<t&&canon;i++) if(idx[i]>=un0) for(int j=i+1;j<t;j++) if(corb[idx[j]]==corb[idx[i]]){canon=0;break;} } for(int a=1;a<G&&canon;a++) if(img(M,a)<M) canon=0;
    if(canon){ if(nrep==cap){cap*=2;rmask=realloc(rmask,cap*8);rcol=realloc(rcol,cap*6);} rmask[nrep]=M; for(int i=0;i<t;i++)rcol[nrep][i]=idx[i]; nrep++; }
    int i=t-1; while(i>=0&&idx[i]==k-t+i)i--; if(i<0)break; idx[i]++; for(int j=i+1;j<t;j++)idx[j]=idx[j-1]+1; }
  P=1<<t; cnt=calloc((size_t)nrep*P,2); hl=malloc((size_t)nrep*P*sizeof(int)); hp=malloc((size_t)nrep*P*sizeof(int));
}
static inline int patt(uint64_t v,int a,int r){ int p=0; for(int i=0;i<t;i++){ int c=rcol[r][i]; p|=(int)((v>>iact[a][c])&1)<<i; } return p; }
static void recount(void){ memset(cnt,0,(size_t)nrep*P*2); holes=0;
  for(int r=0;r<nrep;r++){ uint16_t*C=cnt+(size_t)r*P; for(int g=0;g<m;g++)for(int i=0;i<ncos[g];i++) C[patt(gen[g],cosrep[g][i],r)]++; }
  for(long i=0;i<(long)nrep*P;i++){hp[i]=-1; if(!cnt[i])addh(i);} }
static int touched[MAXG]; static int tmask[MAXG];
/* precomputed: for word g, block b: list of (class r, coset ci, mask) ; pattern table pat[g][ci][r] */
typedef struct { int r; uint8_t ci, msk; } ent;
static ent *lst[MAXW][MAXK]; static int lstn[MAXW][MAXK]; static uint8_t *pat[MAXW][MAXG];
static void precomp(void){
  for(int g=0;g<m;g++){ for(int i=0;i<ncos[g];i++){ pat[g][i]=malloc(nrep); for(int r=0;r<nrep;r++) pat[g][i][r]=(uint8_t)patt(gen[g],cosrep[g][i],r); }
    for(int b=0;b<nblk[g];b++){ long cap=1024,n=0; ent*L=malloc(cap*sizeof(ent));
      for(int r=0;r<nrep;r++){ int nt=0;
        for(int i=0;i<t;i++){ int c=rcol[r][i]; for(int j=0;j<blksz[g][b];j++){ int o=blk[g][b][j]; for(int q=0;q<whoN[o][c];q++){ int a=who[o][c][q]; int ci=cosidx[g][a]; if(tmask[ci]==0)touched[nt++]=ci; tmask[ci]|=1<<i; } } }
        for(int x=0;x<nt;x++){ int ci=touched[x]; if(n==cap){cap*=2;L=realloc(L,cap*sizeof(ent));} L[n].r=r; L[n].ci=(uint8_t)ci; L[n].msk=(uint8_t)tmask[ci]; n++; tmask[ci]=0; } }
      lst[g][b]=L; lstn[g][b]=(int)n; } } }
static inline int fflip(int g,int b){ int d=0; ent*L=lst[g][b]; int n=lstn[g][b];
  for(int x=0;x<n;x++){ int r=L[x].r; uint8_t*pp=pat[g][L[x].ci]+r; int p=*pp, p2=p^L[x].msk; uint16_t*C=cnt+(size_t)r*P;
    if(--C[p]==0){d++;addh((size_t)r*P+p);} if(C[p2]++==0){d--;remh((size_t)r*P+p2);} *pp=(uint8_t)p2; }
  uint64_t v=gen[g]; for(int j=0;j<blksz[g][b];j++) v^=1ull<<blk[g][b][j]; gen[g]=v; return d; }
/* flip block b of word g; returns delta holes */
static inline int gflip(int g,int b){ int d=0; uint64_t v=gen[g]; int nt;
  for(int r=0;r<nrep;r++){ uint16_t*C=cnt+(size_t)r*P; nt=0;
    for(int i=0;i<t;i++){ int c=rcol[r][i]; for(int j=0;j<blksz[g][b];j++){ int o=blk[g][b][j]; for(int q=0;q<whoN[o][c];q++){ int a=who[o][c][q]; int ci=cosidx[g][a]; if(tmask[ci]==0)touched[nt++]=ci; tmask[ci]|=1<<i; } } }
    for(int x=0;x<nt;x++){ int ci=touched[x]; int msk=tmask[ci]; tmask[ci]=0; int p=patt(v,cosrep[g][ci],r); int p2=p^msk;
      if(--C[p]==0){d++;addh((long)r*P+p);} if(C[p2]++==0){d--;remh((long)r*P+p2);} } }
  for(int j=0;j<blksz[g][b];j++) v^=1ull<<blk[g][b][j]; gen[g]=v; return d; }
int main(int argc,char**argv){
  if(argc<7){fprintf(stderr,"usage: grpm t SPEC seed secs T outprefix [-r reloadsec] [-i genfile]\n");return 1;}
  t=atoi(argv[1]); readspec(argv[2]); rs^=(uint64_t)atoi(argv[3])*2654435761ULL; double secs=atof(argv[4]),T=atof(argv[5]); const char*out=argv[6];
  double reload=0; const char*genfile=NULL; int zf=0; for(int i=7;i<argc;i++){ if(!strcmp(argv[i],"-r"))reload=atof(argv[++i]); else if(!strcmp(argv[i],"-i"))genfile=argv[++i]; else if(!strcmp(argv[i],"-z"))zf=atoi(argv[++i]); else if(!strcmp(argv[i],"-u"))un0=atoi(argv[++i]); }
  build();
  for(int g=0;g<m;g++){ gen[g]=0; for(int b=0;b<nblk[g];b++) if(xr()&1) for(int j=0;j<blksz[g][b];j++) gen[g]|=1ull<<blk[g][b][j]; }
  if(genfile){FILE*f=fopen(genfile,"r"); if(f){ for(int g=0;g<m;g++){ char buf[256]; if(!fgets(buf,256,f))break; uint64_t v=0; int c=0; for(char*p=buf;*p&&c<k;p++) if(*p=='0'||*p=='1'){ if(*p=='1')v|=1ull<<c; c++; } gen[g]=v; } fclose(f);} }
  recount(); precomp(); fprintf(stderr,"t=%d k=%d |G|=%d words=%d N=%d classes=%d holes=%ld\n",t,k,G,m,N,nrep,holes);
  memcpy(best,gen,sizeof gen); long bh=holes; double t0=now(),lastimp=t0; long it=0; char fn[512];
  while(holes>0){
    if((it&1023)==0){ double tn=now(); if(tn-t0>secs)break; if(reload>0&&tn-lastimp>reload){memcpy(gen,best,sizeof gen);recount(); for(int g=0;g<m;g++)for(int i=0;i<ncos[g];i++)for(int r=0;r<nrep;r++)pat[g][i][r]=(uint8_t)patt(gen[g],cosrep[g][i],r); lastimp=tn;} }
    it++; int g=rndl(m),b=rndl(nblk[g]); if(zf&&blk[g][b][0]>=k-zf)continue; int d=fflip(g,b);
    if(d>0&&rndu()>=exp(-d/T)){ fflip(g,b); continue; }
    if(holes<bh){bh=holes;memcpy(best,gen,sizeof gen);lastimp=now(); fprintf(stderr,"it=%ld t=%.1f holes=%ld\n",it,lastimp-t0,holes);}
  }
  { long hcur=holes; recount(); fprintf(stderr,"end it=%ld best=%ld (check incremental %ld == recount %ld)\n",it,bh,hcur,holes); }
  snprintf(fn,sizeof fn,"%s_gen.txt",out); FILE*f=fopen(fn,"w"); for(int g=0;g<m;g++){for(int c=0;c<k;c++)fputc((best[g]>>c&1)?'1':'0',f);fputc('\n',f);} fclose(f);
  if(bh>0){ snprintf(fn,sizeof fn,"%s_part.txt",out); f=fopen(fn,"w");
    for(int g=0;g<m;g++)for(int i=0;i<ncos[g];i++){ int a=cosrep[g][i]; for(int c=0;c<k;c++){ if(un0>=0&&c>=un0&&corb[c]!=c)continue; fprintf(f,"%d ",(int)((best[g]>>iact[a][c])&1)); } fputc('\n',f); }
    fclose(f); }
  if(bh==0){ snprintf(fn,sizeof fn,"%s_%d.txt",out,N); f=fopen(fn,"w");
    for(int g=0;g<m;g++)for(int i=0;i<ncos[g];i++){ int a=cosrep[g][i]; for(int c=0;c<k;c++){ if(un0>=0&&c>=un0&&corb[c]!=c)continue; fprintf(f,"%d ",(int)((best[g]>>iact[a][c])&1)); } fputc('\n',f); }
    fclose(f); printf("FOUND %s\n",fn); }
  printf("best %ld classes %d N %d\n",bh,nrep,N); return 0; }
