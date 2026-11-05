// bsa4.c (debate8 B): bit-parallel binary strength-4 annealer, N <= 128 rows (one __int128 per column).
// Exact delta of a single flip = C(k-1,3) mask AND/compare steps; no count tables (memory ~ hole list only).
// Moves: pS = best of omega random flips (omega=1: ESSA N2), pM = ESSA/MPO N1: random missing 4-tuple set
// into the best row (m1best=1) or a random row (m1best=0). Schedule: fixT>0 fixed T, else geometric
// T0, alpha, L moves per temperature, restart from best after phi non-improving temperatures.
// usage: bsa4 IN|- N K secs seed out [key=val ...]   (IN with fewer columns: extra columns best-of-cand)
//   chain: kmax>K adds columns one at a time at fixed N (cap s per column), writes out_N_K.txt per success
// gcc -O3 -march=native -o bsa4 bsa4.c -lm
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>
#include <time.h>
typedef unsigned __int128 m128; typedef uint64_t u64;
static int N, K; static m128 col[512], VALID, ONE = 1;
static m128 F[512], G[512];
static long holes; static u64 rs = 88172645463325252ULL;
static inline u64 rnd(void){ rs ^= rs << 13; rs ^= rs >> 7; rs ^= rs << 17; return rs; }
static inline double urand(void){ return (rnd() >> 11) * (1.0 / 9007199254740992.0); }
static double now(void){ struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec + 1e-9 * t.tv_nsec; }
static inline m128 pm(int x, int v){ return v ? col[x] : (~col[x] & VALID); }
static inline int gv(int x, int r){ return (int)((col[x] >> r) & 1); }
static u64 *hl; static long nh, caph;
static void addhole(int a[4], int v[4]){ // sort by column
  int c[4], w[4]; memcpy(c, a, 16); memcpy(w, v, 16);
  for (int i = 1; i < 4; i++) for (int j = i; j > 0 && c[j - 1] > c[j]; j--){ int t = c[j]; c[j] = c[j - 1]; c[j - 1] = t; t = w[j]; w[j] = w[j - 1]; w[j - 1] = t; }
  if (nh == caph){ caph = caph ? caph * 2 : 1 << 16; hl = realloc(hl, caph * 8); }
  hl[nh++] = (u64)c[0] | (u64)c[1] << 9 | (u64)c[2] << 18 | (u64)c[3] << 27 | (u64)(w[0] << 3 | w[1] << 2 | w[2] << 1 | w[3]) << 36; }
static inline void dec(u64 h, int c[4], int v[4]){ for (int i = 0; i < 4; i++){ c[i] = (h >> (9 * i)) & 511; v[i] = (h >> (36 + 3 - i)) & 1; } }
static inline int alive(u64 h){ int c[4], v[4]; dec(h, c, v); return (pm(c[0], v[0]) & pm(c[1], v[1]) & pm(c[2], v[2]) & pm(c[3], v[3])) == 0; }
static long flip(int r, int c, int commit){
  m128 bit = ONE << r; int vc = gv(c, r); m128 Ec = pm(c, vc);
  int m = 0; static int idx[512];
  for (int x = 0; x < K; x++){ if (x == c) continue; m128 e = pm(x, gv(x, r)); F[m] = e & Ec; G[m] = e & ~Ec; idx[m] = x; m++; }
  long d = 0;
  for (int i = 0; i < m; i++) for (int j = i + 1; j < m; j++){
    m128 ff = F[i] & F[j], gg = G[i] & G[j]; long s = 0;
    if (gg == 0){ s -= m - j - 1; }
    else for (int l = j + 1; l < m; l++) s -= ((gg & G[l]) == 0);
    if (ff == bit){ s += m - j - 1;
      if (commit) for (int l = j + 1; l < m; l++){ int a[4] = {idx[i], idx[j], idx[l], c}, v[4] = {gv(idx[i], r), gv(idx[j], r), gv(idx[l], r), vc}; addhole(a, v); } }
    else for (int l = j + 1; l < m; l++) if ((ff & F[l]) == bit){ s++;
      if (commit){ int a[4] = {idx[i], idx[j], idx[l], c}, v[4] = {gv(idx[i], r), gv(idx[j], r), gv(idx[l], r), vc}; addhole(a, v); } }
    d += s; }
  if (commit){ col[c] ^= bit; holes += d; }
  return d; }
static inline void tflip(int r, int c){ col[c] ^= ONE << r; }
static long full_holes(int rebuild){ long h = 0; if (rebuild) nh = 0;
  for (int a = 0; a < K; a++) for (int b = a + 1; b < K; b++){ m128 p2[4]; for (int q = 0; q < 4; q++) p2[q] = pm(a, q >> 1) & pm(b, q & 1);
    for (int c = b + 1; c < K; c++){ m128 p3[8]; for (int q = 0; q < 8; q++) p3[q] = p2[q >> 1] & pm(c, q & 1);
      for (int d = c + 1; d < K; d++){ m128 z0 = pm(d, 0), z1 = col[d];
        for (int q = 0; q < 8; q++){ if (!(p3[q] & z0)){ h++; if (rebuild){ int cc[4] = {a, b, c, d}, vv[4] = {q >> 2, (q >> 1) & 1, q & 1, 0}; addhole(cc, vv); } }
          if (!(p3[q] & z1)){ h++; if (rebuild){ int cc[4] = {a, b, c, d}, vv[4] = {q >> 2, (q >> 1) & 1, q & 1, 1}; addhole(cc, vv); } } } } } }
  return h; }
static long col_holes(int d){ long h = 0;
  for (int a = 0; a < K; a++) if (a != d) for (int b = a + 1; b < K; b++) if (b != d) for (int c = b + 1; c < K; c++) if (c != d)
    for (int q = 0; q < 16; q++) if (!(pm(a, q >> 3) & pm(b, (q >> 2) & 1) & pm(c, (q >> 1) & 1) & pm(d, q & 1))) h++;
  return h; }
static m128 balanced_col(void){ int ones = N / 2 + ((N & 1) ? (int)(rnd() & 1) : 0); m128 m = 0; int perm[128];
  for (int i = 0; i < N; i++) perm[i] = i;
  for (int i = 0; i < ones; i++){ int j = i + rnd() % (N - i); int t = perm[i]; perm[i] = perm[j]; perm[j] = t; m |= ONE << perm[i]; }
  return m; }
static int sample_hole(u64 *o){ while (nh > 0){ long i = rnd() % nh; if (alive(hl[i])){ *o = hl[i]; return 1; } hl[i] = hl[--nh]; } return 0; }
static void compact(void){ long j = 0; for (long i = 0; i < nh; i++) if (alive(hl[i])) hl[j++] = hl[i]; nh = j; }
static void write_arr(const char *fn){ FILE *o = fopen(fn, "w");
  for (int r = 0; r < N; r++) for (int c = 0; c < K; c++) fprintf(o, "%d%c", gv(c, r), c == K - 1 ? '\n' : ' '); fclose(o); }

// ExtendCA (Torres-Jimenez & Avila-George, SBSTT): fill the N cells of column c one at a time; each step
// sets the free cell/value pair that covers the most still-uncovered (triple of other columns, pattern, value).
static void gcol(int c){
  long nt = (long)c * (c - 1) * (c - 2) / 6; unsigned char *pat = malloc((size_t)N * nt); uint16_t *cov = calloc(nt, 2);
  for (int r = 0; r < N; r++){ long i = 0; for (int a = 0; a < c; a++) for (int b = a + 1; b < c; b++) for (int d = b + 1; d < c; d++)
    pat[(size_t)r * nt + i++] = (unsigned char)(gv(a, r) << 3 | gv(b, r) << 2 | gv(d, r) << 1); }
  int used[128] = {0}; m128 m = 0;
  for (int s = 0; s < N; s++){ long bg = -1; int br = -1, bv = 0;
    for (int r = 0; r < N; r++){ if (used[r]) continue; long g0 = 0, g1 = 0; unsigned char *p = pat + (size_t)r * nt;
      for (long i = 0; i < nt; i++){ uint16_t cv = cov[i]; g0 += !((cv >> p[i]) & 1); g1 += !((cv >> (p[i] | 1)) & 1); }
      if (g0 > bg || (g0 == bg && (rnd() & 1))){ bg = g0; br = r; bv = 0; }
      if (g1 > bg || (g1 == bg && (rnd() & 1))){ bg = g1; br = r; bv = 1; } }
    used[br] = 1; if (bv) m |= ONE << br; unsigned char *p = pat + (size_t)br * nt;
    for (long i = 0; i < nt; i++) cov[i] |= (uint16_t)1 << (p[i] | bv); }
  col[c] = m; free(pat); free(cov); }
static double P[32]; static const char *PN[] = {"pS","pM","omega","T0","alpha","L","phi","fixT","rep","cand","m1best","kmax","cap","x","pF","fr",0};
static double par(const char *n){ for (int i = 0; PN[i]; i++) if (!strcmp(PN[i], n)) return P[i]; return 0; }
static int KF; static long evals, moves; static int restarts; static m128 best[512];
static long anneal(double secs){
  double pS = par("pS"), pM = par("pM"); pS /= pS + pM; int omega = par("omega"), m1best = par("m1best"), phi = par("phi");
  double T0 = par("T0"), alpha = par("alpha"), fixT = par("fixT"), rep = par("rep"); long L = par("L") > 0 ? (long)par("L") : (long)N * K * 4;
  long besth = holes; memcpy(best, col, sizeof(m128) * K); double T = fixT > 0 ? fixT : T0; int noimp = 0;
  double ts = now(), lp = ts; long bestStep = besth, runbest = holes;
  while (holes > 0){
    for (long it = 0; it < L && holes > 0; it++){
      long bd = 1L << 60;
      if (urand() < pS){ int br = 0, bc = 0;
        int focus = urand() < par("pF"); int fr = par("fr"), k0f = (int)par("x") > 0 ? KF : K;
        for (int w = 0; w < omega; w++){ int r = rnd() % N, c = rnd() % K;
          if (focus){ long nfc = (long)N * (K - k0f), nfr = (long)fr * k0f; long u = rnd() % (nfc + nfr); if (u < nfc){ r = u % N; c = k0f + u / N; } else { u -= nfc; r = N - fr + u % fr; c = u / fr; } } long d = flip(r, c, 0); evals++; if (d < bd){ bd = d; br = r; bc = c; } }
        if (bd <= 0 || urand() < exp(-bd / T)){ flip(br, bc, 1); moves++; }
      } else { u64 h; if (!sample_hole(&h)){ compact(); if (!sample_hole(&h)){ holes = full_holes(1); continue; } }
        int cs[4], vs[4]; dec(h, cs, vs); int brow = -1;
        for (int r0 = 0; r0 < (m1best ? N : 1); r0++){ int r = m1best ? r0 : (int)(rnd() % N); long d = 0; int fl[4], nf = 0;
          for (int j = 0; j < 4; j++) if (gv(cs[j], r) != vs[j]){ d += flip(r, cs[j], 0); tflip(r, cs[j]); fl[nf++] = cs[j]; evals++; }
          for (int j = 0; j < nf; j++) tflip(r, fl[j]);
          if (d < bd || (d == bd && (rnd() & 1))){ bd = d; brow = r; } }
        if (brow >= 0 && (bd <= 0 || urand() < exp(-bd / T))){ for (int j = 0; j < 4; j++) if (gv(cs[j], brow) != vs[j]) flip(brow, cs[j], 1); moves++; }
      }
      if (holes < runbest) runbest = holes;
      if (holes < besth){ besth = holes; memcpy(best, col, sizeof(m128) * K); }
      if (nh > 8 * (holes + 4096)) compact();
      if ((it & 15) == 0){ double tn = now(); if (tn - ts > secs) goto done;
        if (rep > 0 && tn - lp > rep){ lp = tn; fprintf(stderr, "t=%.0f T=%.3g holes=%ld best=%ld evals=%ld moves=%ld\n", tn - ts, T, holes, besth, evals, moves); } }
    }
    if (fixT > 0) continue;
    T *= alpha; if (runbest < bestStep){ bestStep = runbest; noimp = 0; } else noimp++;
    if (noimp >= phi){ memcpy(col, best, sizeof(m128) * K); holes = full_holes(1); T = T0; noimp = 0; restarts++; bestStep = runbest = holes; }
  }
done:
  if (besth < holes){ memcpy(col, best, sizeof(m128) * K); holes = full_holes(1); }
  return holes; }
int main(int ac, char **av){
  if (ac < 7){ fprintf(stderr, "usage: bsa4 IN|- N K secs seed out [key=val]\n"); return 1; }
  N = atoi(av[2]); K = atoi(av[3]); double secs = atof(av[4]); rs ^= (u64)atoll(av[5]) * 0x9E3779B97F4A7C15ULL; for (int i = 0; i < 20; i++) rnd();
  const char *out = av[6]; if (N > 128 || K > 511){ fprintf(stderr, "N<=128, K<=511\n"); return 1; }
  VALID = N == 128 ? ~(m128)0 : (ONE << N) - 1;
  double def[] = {0.7, 0.3, 1, 4, 0.99, 0, 11, 0, 30, 100, 1, 0, 600, 0, 0, 0};
  for (int i = 0; PN[i]; i++) P[i] = def[i];
  for (int i = 7; i < ac; i++){ char *e = strchr(av[i], '='); if (!e) continue; *e = 0; int ok = 0; for (int j = 0; PN[j]; j++) if (!strcmp(PN[j], av[i])){ P[j] = atof(e + 1); ok = 1; } if (!ok){ fprintf(stderr, "unknown key %s\n", av[i]); return 1; } }
  int k0 = 0;
  if (strcmp(av[1], "-")){ FILE *f = fopen(av[1], "r"); if (!f){ perror(av[1]); return 1; }
    static char line[1 << 16]; int r = 0;
    while (fgets(line, sizeof line, f) && r < N){ int k = 0; for (char *p = line; *p; p++) if (*p == '0' || *p == '1'){ if (k < K && *p == '1') col[k] |= ONE << r; k++; }
      if (k){ if (!k0) k0 = k < K ? k : K; r++; } }
    fclose(f); if (r < N){ fprintf(stderr, "input has %d rows; random fill\n", r); for (int c = 0; c < k0; c++) for (int i = r; i < N; i++) if (rnd() & 1) col[c] |= ONE << i; } }
  double t0 = now(); int cand = par("cand");
  KF = k0; if (par("x") > 0 && k0 > 3) for (int c = k0; c < K; c++){ double tg = now(); gcol(c); fprintf(stderr, "greedy col %d: %.1fs\n", c, now() - tg); }
  else for (int c = k0; c < K; c++){ long bh = 1L << 60; m128 bm = 0; int Ks = K; K = c + 1;
    for (int i = 0; i < (c > 3 && k0 ? cand : 1); i++){ col[c] = balanced_col(); long h = (c > 3 && k0) ? col_holes(c) : 0; if (h < bh){ bh = h; bm = col[c]; } }
    col[c] = bm; K = Ks; }
  holes = full_holes(1); int kmax = par("kmax"); char fn[512];
  fprintf(stderr, "N=%d K=%d (from %d) holes=%ld init %.1fs\n", N, K, k0, holes, now() - t0);
  if (kmax <= K){ anneal(secs); double el = now() - t0; { long ch = full_holes(0); if (ch != holes) fprintf(stderr, "MISMATCH %ld vs full %ld\n", holes, ch); }
    fprintf(stderr, "done t=%.1f holes=%ld evals=%ld (%.0f/s) moves=%ld restarts=%d\n", el, holes, evals, evals / el, moves, restarts);
    snprintf(fn, sizeof fn, "%s.txt", out); write_arr(fn); printf("%ld\n", holes); return 0; }
  double cap = par("cap"); anneal(cap);
  while (holes == 0){ snprintf(fn, sizeof fn, "%s_%d_%d.txt", out, N, K); write_arr(fn); fprintf(stderr, "K=%d solved t=%.0f\n", K, now() - t0);
    if (K >= kmax || now() - t0 > secs) break;
    int c = K; K++; long bh = 1L << 60; m128 bm = 0;
    if (par("x") > 0) gcol(c); else { for (int i = 0; i < cand; i++){ col[c] = balanced_col(); long h = col_holes(c); if (h < bh){ bh = h; bm = col[c]; } }
    col[c] = bm; } holes = full_holes(1); fprintf(stderr, "K=%d init holes %ld\n", K, holes); anneal(cap); }
  if (holes){ snprintf(fn, sizeof fn, "%s_fail_%d_%d.txt", out, N, K); write_arr(fn); fprintf(stderr, "stuck at K=%d holes=%ld\n", K, holes); }
  printf("%d\n", holes ? K - 1 : K); return 0; }
