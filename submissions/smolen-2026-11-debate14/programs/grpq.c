/* grpq.c (debate14 A, own code, after cycq.c of debate 11 B): quotient annealer for CA(N; t, k, 2) whose rows are
 * the images of m generator words under a REGULAR permutation group G of order k acting on the columns, plus
 * nconst constant rows. Groups: rot = Z_k, xor = Z_2^n (k=2^n, column index XOR), z4z4 (k=16), z2z8 (k=16),
 * dih = dihedral D_{k/2} (left regular action), z3z9 etc. not included. Coverage is counted on one
 * representative per G-orbit of t-sets (exact, incremental). Portable C (no intrinsics).
 * usage: grpq t k m nconst group seed secs T outprefix [-r reloadsec] [-i genfile]
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>
#include <time.h>
static int t,k,m,nconst,N,P,nrep; static int act[64][64], iact[64][64], awho[64][64];
static uint32_t *rmask; static uint8_t (*rcol)[6]; static uint16_t *cnt; static long holes; static int *hl,*hp;
static uint32_t *gen, full;
static uint64_t rs=88172645463325252ULL;
static inline uint64_t xr(void){rs^=rs<<13;rs^=rs>>7;rs^=rs<<17;return rs;}
static inline long rndl(long n){return (long)(((xr()>>32)*(uint64_t)n)>>32);}
static inline double rndu(void){return (xr()>>11)*(1.0/9007199254740992.0);}
static double now(void){struct timespec ts;clock_gettime(CLOCK_MONOTONIC,&ts);return ts.tv_sec+1e-9*ts.tv_nsec;}
static inline void addh(long i){hp[i]=(int)holes;hl[holes++]=(int)i;}
static inline void remh(long i){int q=hp[i];int last=hl[--holes];hl[q]=last;hp[last]=q;hp[i]=-1;}
static void mkgroup(const char*g){
  if(!strcmp(g,"rot")){ for(int a=0;a<k;a++)for(int c=0;c<k;c++)act[a][c]=(c+a)%k; }
  else if(!strcmp(g,"xor")){ for(int a=0;a<k;a++)for(int c=0;c<k;c++)act[a][c]=c^a; }
  else if(!strcmp(g,"z4z4")){ if(k!=16){fprintf(stderr,"k=16\n");exit(1);} for(int a=0;a<16;a++)for(int c=0;c<16;c++)act[a][c]=4*(((c>>2)+(a>>2))&3)+(((c&3)+(a&3))&3); }
  else if(!strcmp(g,"z2z8")){ if(k!=16){fprintf(stderr,"k=16\n");exit(1);} for(int a=0;a<16;a++)for(int c=0;c<16;c++)act[a][c]=8*(((c>>3)+(a>>3))&1)+(((c&7)+(a&7))&7); }
  else if(!strcmp(g,"z2rot")){ /* Z_2 x Z_{k/2} */ int h=k/2; for(int a=0;a<k;a++)for(int c=0;c<k;c++){int ca=c/h,cb=c%h,aa=a/h,ab=a%h; act[a][c]=h*((ca+aa)&1)+((cb+ab)%h);} }
  else if(!strcmp(g,"dih")){ /* D_n, n=k/2: elements r^i s^j -> index 2i+j; left multiplication */ int n=k/2;
    for(int a=0;a<k;a++)for(int c=0;c<k;c++){ int i1=a/2,j1=a%2,i2=c/2,j2=c%2; int i,j; if(j1==0){i=(i1+i2)%n;j=j2;} else {i=((i1-i2)%n+n)%n;j=j2^1;} act[a][c]=2*i+j; } }
  else {fprintf(stderr,"unknown group\n");exit(1);}
  for(int a=0;a<k;a++){ int seen[64]={0}; for(int c=0;c<k;c++){ iact[a][act[a][c]]=c; seen[act[a][c]]++; } for(int c=0;c<k;c++)if(seen[c]!=1){fprintf(stderr,"not a permutation\n");exit(1);} }
  for(int j=0;j<k;j++)for(int c=0;c<k;c++){ awho[j][c]=-1; for(int a=0;a<k;a++)if(act[a][j]==c){ if(awho[j][c]>=0){fprintf(stderr,"not regular\n");exit(1);} awho[j][c]=a; } if(awho[j][c]<0){fprintf(stderr,"not transitive\n");exit(1);} }
}
static inline uint32_t img(uint32_t M,int a){ uint32_t r=0; for(int c=0;c<k;c++) if(M>>c&1) r|=1u<<act[a][c]; return r; }
static void build(void){
  int idx[6]; for(int i=0;i<t;i++)idx[i]=i; nrep=0; long cap=1<<16; rmask=malloc(cap*4); rcol=malloc(cap*6);
  for(;;){ uint32_t M=0; for(int i=0;i<t;i++)M|=1u<<idx[i]; int canon=1; for(int a=1;a<k&&canon;a++) if(img(M,a)<M) canon=0;
    if(canon){ if(nrep==cap){cap*=2;rmask=realloc(rmask,cap*4);rcol=realloc(rcol,cap*6);} rmask[nrep]=M; for(int i=0;i<t;i++)rcol[nrep][i]=idx[i]; nrep++; }
    int i=t-1; while(i>=0&&idx[i]==k-t+i)i--; if(i<0)break; idx[i]++; for(int j=i+1;j<t;j++)idx[j]=idx[j-1]+1; }
  P=1<<t; cnt=calloc((size_t)nrep*P,2); hl=malloc((size_t)nrep*P*sizeof(int)); hp=malloc((size_t)nrep*P*sizeof(int));
}
static inline int patt(uint32_t v,int a,int r){ int p=0; for(int i=0;i<t;i++){ int c=rcol[r][i]; p|=((v>>iact[a][c])&1)<<i; } return p; }
static void recount(void){ memset(cnt,0,(size_t)nrep*P*2); holes=0;
  for(int r=0;r<nrep;r++){ uint16_t*C=cnt+(size_t)r*P; for(int g=0;g<m;g++)for(int a=0;a<k;a++) C[patt(gen[g],a,r)]++; if(nconst>=1)C[0]++; if(nconst>=2)C[P-1]++; }
  for(long i=0;i<(long)nrep*P;i++){hp[i]=-1; if(!cnt[i])addh(i);} }
static inline int gflip(int g,int j){ int d=0; uint32_t v=gen[g];
  for(int r=0;r<nrep;r++){ uint16_t*C=cnt+(size_t)r*P; for(int i=0;i<t;i++){ int c=rcol[r][i]; int a=awho[j][c]; int p=patt(v,a,r); int bit=1<<i;
      if(--C[p]==0){d++;addh((long)r*P+p);} if(C[p^bit]++==0){d--;remh((long)r*P+(p^bit));} } }
  gen[g]=v^(1u<<j); return d; }
int main(int argc,char**argv){
  if(argc<10){fprintf(stderr,"usage: grpq t k m nconst group seed secs T outprefix [-r reloadsec] [-i genfile]\n");return 1;}
  t=atoi(argv[1]);k=atoi(argv[2]);m=atoi(argv[3]);nconst=atoi(argv[4]); const char*grp=argv[5]; rs^=(uint64_t)atoi(argv[6])*2654435761ULL; double secs=atof(argv[7]),T=atof(argv[8]); const char*out=argv[9];
  double reload=0; const char*genfile=NULL; for(int i=10;i<argc;i++){ if(!strcmp(argv[i],"-r"))reload=atof(argv[++i]); else if(!strcmp(argv[i],"-i"))genfile=argv[++i]; }
  full=k==32?0xffffffffu:((1u<<k)-1); N=m*k+nconst; mkgroup(grp); build();
  gen=malloc(m*4); for(int g=0;g<m;g++)gen[g]=(uint32_t)xr()&full;
  if(genfile){FILE*f=fopen(genfile,"r"); for(int g=0;g<m;g++){ char buf[256]; if(!fgets(buf,256,f))break; uint32_t v=0; int c=0; for(char*p=buf;*p&&c<k;p++) if(*p=='0'||*p=='1'){ if(*p=='1')v|=1u<<c; c++; } gen[g]=v; } fclose(f);}
  recount(); fprintf(stderr,"t=%d k=%d m=%d nconst=%d N=%d group=%s classes=%d holes=%ld\n",t,k,m,nconst,N,grp,nrep,holes);
  uint32_t*best=malloc(m*4); memcpy(best,gen,m*4); long bh=holes; double t0=now(),lastimp=t0; long it=0; char fn[512];
  while(holes>0){
    if((it&1023)==0){ double tn=now(); if(tn-t0>secs)break; if(reload>0&&tn-lastimp>reload){memcpy(gen,best,m*4);recount();lastimp=tn;} }
    it++; int g=rndl(m),j=rndl(k); int d=gflip(g,j);
    if(d>0&&rndu()>=exp(-d/T)){ gflip(g,j); continue; }
    if(holes<bh){bh=holes;memcpy(best,gen,m*4);lastimp=now(); fprintf(stderr,"it=%ld t=%.1f holes=%ld\n",it,lastimp-t0,holes);}
  }
  fprintf(stderr,"end it=%ld best=%ld\n",it,bh);
  snprintf(fn,sizeof fn,"%s_gen.txt",out); FILE*f=fopen(fn,"w"); for(int g=0;g<m;g++){for(int c=0;c<k;c++)fputc((best[g]>>c&1)?'1':'0',f);fputc('\n',f);} fclose(f);
  if(bh==0){ snprintf(fn,sizeof fn,"%s_%d.txt",out,N); f=fopen(fn,"w");
    for(int g=0;g<m;g++)for(int a=0;a<k;a++){ for(int c=0;c<k;c++)fprintf(f,"%d%c",(best[g]>>iact[a][c])&1,c==k-1?'\n':' '); }
    if(nconst>=1){for(int c=0;c<k;c++)fprintf(f,"0%c",c==k-1?'\n':' ');} if(nconst>=2){for(int c=0;c<k;c++)fprintf(f,"1%c",c==k-1?'\n':' ');}
    fclose(f); printf("FOUND %s\n",fn); }
  printf("best %ld classes %d\n",bh,nrep); return 0; }
