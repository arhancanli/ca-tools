/* cz2help.c - exact C helper of tools/construction_cert.py for the construction powercz-2
 * (tools/CONSTRUCTION_CERT.md, "Power CZ with relabelled blocks and enumerated constant tuples").
 *
 * construction_cert.py compiles this file at run time (cc -O2) into a temporary folder, after checking
 * that its sha256 is the one construction_cert.py records (HELPER_SHA256), and calls it for the work that
 * is too large for Python. Every mode is exact: every set of columns is visited, nothing is sampled.
 * The ingredient files it reads are written by construction_cert.py from the rows it parsed: one row per
 * line, entries 0 or 1 separated by single spaces.
 *
 *   cz2help quilt ING t WMASK
 *       WMASK has bit w set when every tuple of weight w must be shown on every t-set of columns.
 *       Prints "quilt missing N" (N = number of (t-set, tuple) pairs not shown) and, when N > 0,
 *       "first c_1 .. c_t weight w" (the first t-set in lexicographic order and the weight missed).
 *   cz2help bad ING t z
 *       For s = 1..t prints "bad s COUNT", COUNT the number of s-sets of columns on which no row is
 *       constant z; stops after the first s < t whose COUNT is positive.
 *   cz2help enum t z a b HFILE ING_0 .. ING_{M-1}
 *       HFILE: M lines of k integers, H[r][c] the column of ING_r that array column c uses (after the
 *       relabelling). Counts the t-sets T of array columns such that no row of any block is constant z
 *       on T, assuming (checked here for blocks a and b, by the caller for all blocks) that no ingredient
 *       has a bad s-set with s < t. Lists the bad t-sets X_a of block a and X_b of block b, takes every
 *       bijection X_a -> X_b, finds the array columns by the pair (H[a][c], H[b][c]) (one column at most:
 *       two columns agree in at most one row, e = 2, which the caller checks), and tests every other
 *       block directly. Prints "enum survivors N", "enum candidates C" (bijections that gave t array
 *       columns) and up to 5 "survivor c_1 .. c_t" (columns ascending).
 * Exit status 0 on success, 2 for a usage error, 3 for unreadable input, 4 when a hypothesis of the
 * enumeration fails (a bad s-set with s < t in block a or b, two columns with the same pair).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

typedef uint64_t u64;
typedef struct { int N, K, W; u64 *col; u64 *full; } Ing;   /* col[j * W + word]: column j as a bit set of rows */

static void die(int code, const char *msg, const char *arg) {
  fprintf(stderr, "cz2help: %s%s%s\n", msg, arg ? " " : "", arg ? arg : "");
  exit(code);
}

static void *xcalloc(size_t n, size_t s) {
  void *p = calloc(n ? n : 1, s ? s : 1);
  if (!p) die(3, "out of memory", NULL);
  return p;
}

static Ing load(const char *fn) {
  FILE *f = fopen(fn, "r");
  if (!f) die(3, "cannot open", fn);
  int N = 0, K = -1, ch, cnt = 0, intok = 0;
  size_t na = 0, ca = 1 << 16;
  unsigned char *a = xcalloc(ca, 1);
  for (;;) {
    ch = fgetc(f);
    if (ch == '0' || ch == '1') {
      if (intok) die(3, "an entry is not 0 or 1 in", fn);
      if (na == ca) { ca *= 2; a = realloc(a, ca); if (!a) die(3, "out of memory", NULL); }
      a[na++] = (unsigned char)(ch - '0'); cnt++; intok = 1;
    } else if (ch == ' ' || ch == '\t' || ch == '\r') {
      intok = 0;
    } else if (ch == '\n' || ch == EOF) {
      intok = 0;
      if (cnt) {
        if (K < 0) K = cnt; else if (cnt != K) die(3, "ragged rows in", fn);
        N++;
      }
      cnt = 0;
      if (ch == EOF) break;
    } else die(3, "an entry is not 0 or 1 in", fn);
  }
  fclose(f);
  if (N == 0 || K <= 0) die(3, "no rows in", fn);
  Ing g; g.N = N; g.K = K; g.W = (N + 63) / 64;
  g.col = xcalloc((size_t)K * g.W, sizeof(u64));
  g.full = xcalloc(g.W, sizeof(u64));
  for (int r = 0; r < N; r++) {
    g.full[r / 64] |= 1ULL << (r % 64);
    for (int j = 0; j < K; j++)
      if (a[(size_t)r * K + j]) g.col[(size_t)j * g.W + r / 64] |= 1ULL << (r % 64);
  }
  free(a);
  return g;
}

/* the rows on which column j equals z, as a bit set */
static u64 *zcols(const Ing *g, int z) {
  u64 *zc = xcalloc((size_t)g->K * g->W, sizeof(u64));
  for (int j = 0; j < g->K; j++)
    for (int w = 0; w < g->W; w++) {
      u64 x = g->col[(size_t)j * g->W + w];
      zc[(size_t)j * g->W + w] = (z ? x : ~x) & g->full[w];
    }
  return zc;
}

/* ---------------- quilt ---------------- */
static const Ing *QG; static int QT, QMASK; static u64 *qlvl[9]; static long long qmissing;
static int qcur[9], qfirst[9], qfirstw = -1;

static void qrec(int d, int start) {
  int W = QG->W;
  for (int j = start; j <= QG->K - (QT - d); j++) {
    qcur[d] = j;
    const u64 *c = QG->col + (size_t)j * W;
    int np = 1 << d;
    if (d + 1 == QT) {
      for (int p = 0; p < np; p++)
        for (int b = 0; b < 2; b++) {
          int pat = 2 * p + b, wt = __builtin_popcount((unsigned)pat);
          if (!((QMASK >> wt) & 1)) continue;
          const u64 *L = qlvl[d] + (size_t)p * W;
          u64 any = 0;
          for (int w = 0; w < W; w++) any |= L[w] & (b ? c[w] : ~c[w]);
          if (!any) {
            if (!qmissing) { memcpy(qfirst, qcur, sizeof qcur); qfirstw = wt; }
            qmissing++;
          }
        }
    } else {
      u64 *nx = qlvl[d + 1];
      for (int p = 0; p < np; p++) {
        const u64 *L = qlvl[d] + (size_t)p * W;
        u64 *n0 = nx + (size_t)(2 * p) * W, *n1 = nx + (size_t)(2 * p + 1) * W;
        for (int w = 0; w < W; w++) { n0[w] = L[w] & ~c[w]; n1[w] = L[w] & c[w]; }
      }
      qrec(d + 1, j + 1);
    }
  }
}

static int do_quilt(char **a) {
  Ing g = load(a[0]);
  QG = &g; QT = atoi(a[1]); QMASK = atoi(a[2]);
  if (QT < 1 || QT > 8) die(2, "t must be 1..8", NULL);
  for (int d = 0; d < QT; d++) qlvl[d] = xcalloc((size_t)(1 << d) * g.W, sizeof(u64));
  memcpy(qlvl[0], g.full, g.W * sizeof(u64));
  qmissing = 0;
  if (g.K >= QT) qrec(0, 0);
  printf("quilt missing %lld\n", qmissing);
  if (qmissing) {
    printf("first");
    for (int i = 0; i < QT; i++) printf(" %d", qfirst[i]);
    printf(" weight %d\n", qfirstw);
  }
  return 0;
}

/* ---------------- bad sets ---------------- */
static const u64 *BZ; static int BK, BW, BS; static u64 *blvl[9]; static long long bcount; static int bcur[9];
static int *blist; static long long bcap, bn; static int blisting;

static void brec(int d, int start) {
  for (int j = start; j <= BK - (BS - d); j++) {
    bcur[d] = j;
    const u64 *c = BZ + (size_t)j * BW;
    u64 *n = blvl[d + 1], any = 0;
    for (int w = 0; w < BW; w++) { n[w] = blvl[d][w] & c[w]; any |= n[w]; }
    if (d + 1 == BS) {
      if (!any) {
        bcount++;
        if (blisting) {
          if (bn + BS > bcap) {
            bcap = bcap ? 2 * bcap : 1 << 16;
            blist = realloc(blist, (size_t)bcap * sizeof(int));
            if (!blist) die(3, "out of memory", NULL);
          }
          for (int i = 0; i < BS; i++) blist[bn++] = bcur[i];
        }
      }
    } else brec(d + 1, j + 1);
  }
}

/* counts[s] for s = 1..t (-1 after the first s < t with a positive count); lists the bad t-sets when
   list != 0 (into blist, bn entries) */
static void bad_sets(const Ing *g, int t, int z, int list, long long *counts) {
  u64 *zc = zcols(g, z);
  BZ = zc; BK = g->K; BW = g->W;
  for (int d = 0; d <= 8; d++) blvl[d] = xcalloc(g->W, sizeof(u64));
  for (int s = 1; s <= t; s++) counts[s] = -1;
  for (int s = 1; s <= t; s++) {
    BS = s; bcount = 0; bn = 0; blisting = list && s == t;
    memcpy(blvl[0], g->full, g->W * sizeof(u64));
    if (g->K >= s) brec(0, 0);
    counts[s] = bcount;
    if (s < t && bcount > 0) break;
  }
  free(zc);
  for (int d = 0; d <= 8; d++) free(blvl[d]);
}

static int do_bad(char **a) {
  Ing g = load(a[0]);
  int t = atoi(a[1]), z = atoi(a[2]);
  if (t < 1 || t > 8 || (z != 0 && z != 1)) die(2, "t must be 1..8 and z 0 or 1", NULL);
  long long cnt[10];
  bad_sets(&g, t, z, 0, cnt);
  for (int s = 1; s <= t; s++) { if (cnt[s] < 0) break; printf("bad %d %lld\n", s, cnt[s]); }
  return 0;
}

/* ---------------- enumeration (e = 2) ---------------- */
static int *read_H(const char *fn, int M, int *kout) {
  FILE *f = fopen(fn, "r");
  if (!f) die(3, "cannot open", fn);
  size_t cap = 1 << 16, n = 0;
  int *v = xcalloc(cap, sizeof(int));
  int x, rows = 0, k = -1, cnt = 0, ch;
  for (;;) {
    ch = fgetc(f);
    if (ch >= '0' && ch <= '9') {
      x = ch - '0';
      while ((ch = fgetc(f)) >= '0' && ch <= '9') { x = 10 * x + (ch - '0'); if (x > 100000000) die(3, "entry too large in", fn); }
      if (n == cap) { cap *= 2; v = realloc(v, cap * sizeof(int)); if (!v) die(3, "out of memory", NULL); }
      v[n++] = x; cnt++;
    }
    if (ch == '\n' || ch == EOF) {
      if (cnt) { if (k < 0) k = cnt; else if (cnt != k) die(3, "ragged rows in", fn); rows++; }
      cnt = 0;
      if (ch == EOF) break;
    } else if (ch != ' ' && ch != '\r' && !(ch >= '0' && ch <= '9')) die(3, "bad character in", fn);
  }
  fclose(f);
  if (rows != M) die(3, "the H file does not have M rows:", fn);
  *kout = k;
  return v;
}

static int do_enum(int argc, char **a) {
  int t = atoi(a[0]), z = atoi(a[1]), A = atoi(a[2]), B = atoi(a[3]);
  const char *hf = a[4];
  int M = argc - 5;
  if (t < 2 || t > 7 || (z != 0 && z != 1)) die(2, "t must be 2..7 and z 0 or 1", NULL);
  if (M < 2 || A < 0 || B < 0 || A >= M || B >= M || A == B) die(2, "blocks a, b must be two distinct blocks", NULL);
  Ing *ing = xcalloc(M, sizeof(Ing));
  for (int r = 0; r < M; r++) ing[r] = load(a[5 + r]);
  int k;
  int *H = read_H(hf, M, &k);
  for (int r = 0; r < M; r++)
    for (int c = 0; c < k; c++)
      if (H[(size_t)r * k + c] < 0 || H[(size_t)r * k + c] >= ing[r].K) die(3, "an entry of H is not a column of its ingredient", NULL);
  /* bad t-sets of blocks A and B */
  int *X[2]; long long nx[2];
  for (int i = 0; i < 2; i++) {
    long long cnt[10];
    blist = NULL; bcap = bn = 0;
    bad_sets(&ing[i ? B : A], t, z, 1, cnt);
    for (int s = 1; s < t; s++) if (cnt[s] != 0) die(4, "block a or b has a bad set of size below t", NULL);
    X[i] = blist; nx[i] = cnt[t];
  }
  /* the column of each pair (H[A][c], H[B][c]) */
  int wa = ing[A].K, wb = ing[B].K;
  int *pair = xcalloc((size_t)wa * wb, sizeof(int));
  for (size_t i = 0; i < (size_t)wa * wb; i++) pair[i] = -1;
  for (int c = 0; c < k; c++) {
    size_t idx = (size_t)H[(size_t)A * k + c] * wb + H[(size_t)B * k + c];
    if (pair[idx] >= 0) die(4, "two columns agree in rows a and b", NULL);
    pair[idx] = c;
  }
  /* z-columns of the other blocks */
  u64 **Z = xcalloc(M, sizeof(u64 *));
  for (int r = 0; r < M; r++) if (r != A && r != B) Z[r] = zcols(&ing[r], z);
  /* permutations of 0..t-1 in lexicographic order */
  int nperm = 1;
  for (int i = 2; i <= t; i++) nperm *= i;
  int (*perm)[7] = xcalloc(nperm, sizeof *perm);
  {
    int p[7], n = 0;
    for (int i = 0; i < t; i++) p[i] = i;
    for (;;) {
      memcpy(perm[n++], p, sizeof p);
      int i = t - 2;
      while (i >= 0 && p[i] > p[i + 1]) i--;
      if (i < 0) break;
      int j = t - 1;
      while (p[j] < p[i]) j--;
      int tmp = p[i]; p[i] = p[j]; p[j] = tmp;
      for (int l = i + 1, r = t - 1; l < r; l++, r--) { tmp = p[l]; p[l] = p[r]; p[r] = tmp; }
    }
  }
  long long surv = 0, cand = 0; int shown = 0;
  int L[7][7];
  for (long long xa = 0; xa < nx[0]; xa++) {
    const int *Xa = X[0] + xa * t;
    for (long long xb = 0; xb < nx[1]; xb++) {
      const int *Xb = X[1] + xb * t;
      for (int i = 0; i < t; i++) for (int j = 0; j < t; j++) L[i][j] = pair[(size_t)Xa[i] * wb + Xb[j]];
      for (int pi = 0; pi < nperm; pi++) {
        int c[7], ok = 1;
        for (int j = 0; j < t; j++) { c[j] = L[j][perm[pi][j]]; if (c[j] < 0) { ok = 0; break; } }
        if (!ok) continue;
        cand++;
        int alive = 1;
        for (int r = 0; r < M && alive; r++) {
          if (r == A || r == B) continue;
          int W = ing[r].W;
          for (int w = 0; w < W; w++) {
            u64 x = ing[r].full[w];
            for (int j = 0; j < t; j++) x &= Z[r][(size_t)H[(size_t)r * k + c[j]] * W + w];
            if (x) { alive = 0; break; }   /* a row of block r is constant z on T */
          }
        }
        if (alive) {
          surv++;
          if (shown < 5) {
            shown++;
            for (int i = 1; i < t; i++) for (int j = i; j > 0 && c[j - 1] > c[j]; j--) { int tmp = c[j]; c[j] = c[j - 1]; c[j - 1] = tmp; }
            printf("survivor");
            for (int j = 0; j < t; j++) printf(" %d", c[j]);
            printf("\n");
          }
        }
      }
    }
  }
  printf("enum candidates %lld\n", cand);
  printf("enum survivors %lld\n", surv);
  return 0;
}

int main(int argc, char **argv) {
  if (argc == 5 && !strcmp(argv[1], "quilt")) return do_quilt(argv + 2);
  if (argc == 5 && !strcmp(argv[1], "bad")) return do_bad(argv + 2);
  if (argc >= 9 && !strcmp(argv[1], "enum")) return do_enum(argc - 2, argv + 2);
  fprintf(stderr, "usage: cz2help quilt ING t WMASK | bad ING t z | enum t z a b HFILE ING_0 .. ING_{M-1}\n");
  return 2;
}
