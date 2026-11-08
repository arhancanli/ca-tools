/* caex.c - CAEX-style column extender for strength-2 covering arrays (v <= 4, tuned for v = 3).
 * debate 8, agent A, 2026-11-04. Methods (credit): column extension at fixed N with annealing repair
 * after Torres-Jimenez, Acevedo-Juarez, Avila-George (2021, CAEX, caex-tjaa2021); annealer moves N1/N2,
 * geometric cooling and restart rule after Avila-George, Torres-Jimenez, Hernandez (2012, ESSA).
 * Our own implementation; it reads only the start file given on the command line.
 *
 * Usage: caex START N KMAX seed seconds outprefix
 *   START   start array (n0 <= N rows; 0- or 1-based) or "OA9" (Bush/Bose OA(9;2,4,3)).
 *           Extra rows (N - n0) are random. Columns beyond K0 (env) are dropped.
 *   Grows k one column at a time; writes outprefix_N_k.txt whenever a new largest k is covered.
 * Env (optional):
 *   K0      use only the first K0 columns of START (default all)
 *   T0      start temperature (default 1.0; ESSA uses 4.0)
 *   TMIN    temperature floor of a cooling sweep (default 0.05)
 *   ALPHA   cooling factor (default 0.99)
 *   LMUL    moves per temperature = LMUL*N*k*v*v (default 1.0)
 *   STALL   temperature steps without a new best before reheating from the best (default 11)
 *   P1      probability of move N1 (set a random missing tuple into the best of R1 rows) (0.3)
 *   R1      rows sampled for N1 (default N = all)
 *   COLTRY  restarts of the column-only local search for a new column (default 20)
 *   COLSEC  seconds to spend on one column before giving up on it and trying a fresh column (60)
 *   MAXFAIL fresh columns tried at one k before stopping (default 1000)
 *   TSTALL  stall steps are counted only once T < TSTALL (default 0.3)
 *   FIXT    if set: fixed temperature (no cooling), still reheats-from-best on STALL
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>
#include <time.h>

static int N, KMAX, KM, V = 3, VV = 9;
static uint8_t *A;          /* N x KMAX row-major */
static uint8_t *cnt;        /* (c*KMAX + c2)*VV + a*V + b */
static int32_t *pos;        /* canonical index -> position in ml, or -1 */
static uint32_t *ml; static int64_t nm = 0;
static uint64_t rs = 0x9E3779B97F4A7C15ULL;
static inline uint64_t xr(void){ rs ^= rs << 13; rs ^= rs >> 7; rs ^= rs << 17; return rs; }
static inline int rnd(int n){ return (int)((xr() >> 11) % (uint64_t)n); }
static inline double urand(void){ return (xr() >> 11) * (1.0 / 9007199254740992.0); }
static double now(void){ struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec + 1e-9 * t.tv_nsec; }

static inline uint32_t cidx(int c, int c2, int a, int b){
    if (c < c2) return ((uint32_t)c * KMAX + c2) * VV + a * V + b;
    return ((uint32_t)c2 * KMAX + c) * VV + b * V + a;
}
static inline void madd(uint32_t i){ pos[i] = (int32_t)nm; ml[nm++] = i; }
static inline void mdel(uint32_t i){ int32_t p = pos[i]; uint32_t l = ml[--nm]; ml[p] = l; pos[l] = p; pos[i] = -1; }

static void rebuild(void){
    memset(cnt, 0, (size_t)KMAX * KMAX * VV);
    for (int64_t i = 0; i < nm; i++) pos[ml[i]] = -1;
    nm = 0;
    for (int r = 0; r < N; r++){ uint8_t *row = A + (size_t)r * KMAX;
        for (int c = 0; c < KM; c++) for (int c2 = 0; c2 < KM; c2++) if (c != c2)
            cnt[((size_t)c * KMAX + c2) * VV + row[c] * V + row[c2]]++; }
    for (int c = 0; c < KM; c++) for (int c2 = c + 1; c2 < KM; c2++) for (int t = 0; t < VV; t++)
        if (!cnt[((size_t)c * KMAX + c2) * VV + t]) madd(((uint32_t)c * KMAX + c2) * VV + t);
}

/* incremental: column KM (already written into A) joins; only its pairs are counted (O(N*KM)) */
static void addcol(void){
    int c = KM;
    for (int c2 = 0; c2 < c; c2++){ uint8_t *p = cnt + ((size_t)c * KMAX + c2) * VV, *q = cnt + ((size_t)c2 * KMAX + c) * VV;
        for (int r = 0; r < N; r++){ const uint8_t *row = A + (size_t)r * KMAX; p[row[c] * V + row[c2]]++; q[row[c2] * V + row[c]]++; }
        for (int t = 0; t < VV; t++) if (!q[t]) madd(((uint32_t)c2 * KMAX + c) * VV + t); }
    KM++;
}
/* deltas for changing cell (r,c) to each symbol; d[b] (d[a]=0) */
static inline void deltas(int r, int c, int *d){
    uint8_t *row = A + (size_t)r * KMAX; int a = row[c];
    const uint8_t *base = cnt + (size_t)c * KMAX * VV;
    int da = 0, d0 = 0, d1 = 0, d2 = 0;
    for (int c2 = 0; c2 < KM; c2++){ if (c2 == c) continue;
        const uint8_t *p = base + (size_t)c2 * VV; int y = row[c2];
        da += (p[a * V + y] == 1); d0 -= (p[y] == 0); d1 -= (p[V + y] == 0); d2 -= (p[2 * V + y] == 0); }
    d[0] = da + d0; d[1] = da + d1; d[2] = da + d2; d[a] = 0;
}
static inline void setcell(int r, int c, int b){
    uint8_t *row = A + (size_t)r * KMAX; int a = row[c]; if (a == b) return;
    for (int c2 = 0; c2 < KM; c2++){ if (c2 == c) continue; int y = row[c2];
        uint8_t *p = cnt + ((size_t)c * KMAX + c2) * VV, *q = cnt + ((size_t)c2 * KMAX + c) * VV;
        if (--p[a * V + y] == 0) madd(cidx(c, c2, a, y)); q[y * V + a]--;
        if (p[b * V + y]++ == 0) mdel(cidx(c, c2, b, y)); q[y * V + b]++; }
    row[c] = b;
}

/* ---- column-only local search for a new column given columns 0..KM-1 ---- */
static int colcost(const uint8_t *x, uint16_t *M){   /* M[c*9 + a*3+b] */
    memset(M, 0, sizeof(uint16_t) * KM * VV);
    for (int r = 0; r < N; r++){ uint8_t *row = A + (size_t)r * KMAX; for (int c = 0; c < KM; c++) M[c * VV + row[c] * V + x[r]]++; }
    int z = 0; for (int i = 0; i < KM * VV; i++) z += (M[i] == 0); return z;
}
static int DUPC = -1;
/* Redundancy (Nayeri-Colbourn-Konjevod style): a cell is redundant if every pair-tuple it is part of is
   covered at least twice; return the column with most redundant cells */
static int redundant_column(void){
    int bc = -1, bz = -1;
    for (int c = 0; c < KM; c++){ int z = 0;
        for (int r = 0; r < N; r++){ uint8_t *row = A + (size_t)r * KMAX; int ok = 1;
            for (int c2 = 0; c2 < KM && ok; c2++) if (c2 != c && cnt[((size_t)c * KMAX + c2) * VV + row[c] * V + row[c2]] < 2) ok = 0;
            z += ok; }
        if (z > bz || (z == bz && rnd(2))){ bz = z; bc = c; } }
    return bc;
}
static int bestcolumn(uint8_t *xbest, int tries){
    uint8_t *x = malloc(N); uint16_t *M = malloc(sizeof(uint16_t) * KM * VV); int best = 1 << 30;
    for (int t = 0; t < tries; t++){
        if (DUPC >= 0 && t % 2 == 0){   /* AddFactor with Redundancy: copy the most redundant column, perturb */
            for (int r = 0; r < N; r++) x[r] = A[(size_t)r * KMAX + DUPC];
            for (int j = 0; j < t / 2; j++){ int r = rnd(N); x[r] = (x[r] + 1 + rnd(V - 1)) % V; }
        } else {
        for (int r = 0; r < N; r++) x[r] = r % V;
        for (int r = N - 1; r > 0; r--){ int j = rnd(r + 1); uint8_t s = x[r]; x[r] = x[j]; x[j] = s; }
        }
        int cost = colcost(x, M), cb = cost; double T = 0.6;
        uint8_t *xb = malloc(N); memcpy(xb, x, N);
        for (int it = 0; it < 4000 + 40 * N; it++){
            int r = rnd(N), b0 = x[r], b = (b0 + 1 + rnd(V - 1)) % V; int d = 0;
            uint8_t *row = A + (size_t)r * KMAX;
            for (int c = 0; c < KM; c++){ int a = row[c]; d += (M[c * VV + a * V + b0] == 1) - (M[c * VV + a * V + b] == 0); }
            if (d <= 0 || urand() < exp(-d / T)){
                for (int c = 0; c < KM; c++){ int a = row[c]; M[c * VV + a * V + b0]--; M[c * VV + a * V + b]++; }
                x[r] = b; cost += d; if (cost < cb){ cb = cost; memcpy(xb, x, N); }
            }
            T *= 0.999; if (T < 0.05) T = 0.05;
        }
        if (cb < best){ best = cb; memcpy(xbest, xb, N); }
        free(xb);
        if (best == 0) break;
    }
    free(x); free(M); return best;
}

static void writeca(const char *pre){
    char fn[512]; snprintf(fn, sizeof fn, "%s_%d_%d.txt", pre, N, KM);
    FILE *f = fopen(fn, "w");
    for (int r = 0; r < N; r++){ for (int c = 0; c < KM; c++) fprintf(f, "%d%c", A[(size_t)r * KMAX + c], c + 1 < KM ? ' ' : '\n'); }
    fclose(f);
}
static double genv(const char *s, double d){ const char *e = getenv(s); return e ? atof(e) : d; }

int main(int argc, char **argv){
    if (argc < 7){ fprintf(stderr, "usage: caex START N KMAX seed seconds outprefix\n"); return 2; }
    N = atoi(argv[2]); KMAX = atoi(argv[3]); rs ^= (uint64_t)atoll(argv[4]) * 0x2545F4914F6CDD1DULL; for (int i = 0; i < 20; i++) xr();
    double secs = atof(argv[5]); const char *pre = argv[6];
    double T0 = genv("T0", 1.0), TMIN = genv("TMIN", 0.05), ALPHA = genv("ALPHA", 0.99), LMUL = genv("LMUL", 1.0), P1 = genv("P1", 0.3);
    double COLSEC = genv("COLSEC", 60), TSTALL = genv("TSTALL", 0.3); int STALL = (int)genv("STALL", 11), R1 = (int)genv("R1", 0), COLTRY = (int)genv("COLTRY", 20);
    int MAXFAIL = (int)genv("MAXFAIL", 1000); int FIXT = getenv("FIXT") != NULL;
    A = calloc((size_t)N * KMAX, 1); cnt = calloc((size_t)KMAX * KMAX * VV, 1);
    pos = malloc(sizeof(int32_t) * (size_t)KMAX * KMAX * VV); memset(pos, 0xff, sizeof(int32_t) * (size_t)KMAX * KMAX * VV);
    ml = malloc(sizeof(uint32_t) * (size_t)KMAX * KMAX * VV / 2 + 64);
    /* read start */
    int n0 = 0, k0 = 0;
    if (!strcmp(argv[1], "OA9")){ n0 = 9; k0 = 4; for (int x = 0; x < 3; x++) for (int y = 0; y < 3; y++){ uint8_t *row = A + (size_t)(x * 3 + y) * KMAX;
            row[0] = x; row[1] = y; row[2] = (x + y) % 3; row[3] = (x + 2 * y) % 3; } }
    else { FILE *f = fopen(argv[1], "r"); if (!f){ perror(argv[1]); return 2; }
        char *line = NULL; size_t cap = 0; int mn = 9;
        static int buf[100000];
        while (getline(&line, &cap, f) > 0){ int k = 0; char *p = line, *e;
            for (;;){ long v = strtol(p, &e, 10); if (e == p) break; buf[k++] = (int)v; p = e; }
            if (!k) continue; if (n0 >= N){ fprintf(stderr, "start has more than N rows\n"); return 2; }
            if (!k0) k0 = k; for (int c = 0; c < k0 && c < KMAX; c++){ A[(size_t)n0 * KMAX + c] = buf[c]; if (buf[c] < mn) mn = buf[c]; }
            n0++; }
        fclose(f); if (mn == 1) for (size_t i = 0; i < (size_t)N * KMAX; i++) if (A[i]) A[i]--; }
    if (getenv("K0")) k0 = atoi(getenv("K0")); if (k0 > KMAX) k0 = KMAX;
    for (int r = n0; r < N; r++) for (int c = 0; c < k0; c++) A[(size_t)r * KMAX + c] = rnd(V);
    KM = k0; rebuild();
    fprintf(stderr, "start %s: %d rows read, N=%d k=%d missing=%lld\n", argv[1], n0, N, KM, (long long)nm);
    double tst = now(); uint8_t *Abest = malloc((size_t)N * KMAX), *Aok = malloc((size_t)N * KMAX), *x = malloc(N);
    long long moves = 0; int okk = -1;
    /* first repair the start if needed */
    int fails = 0; double tcol = now(); int64_t best = nm; double T = T0; int stall = 0;
    memcpy(Abest, A, (size_t)N * KMAX);
    if (nm == 0){ okk = KM; memcpy(Aok, A, (size_t)N * KMAX); }
    while (now() - tst < secs){
        if (nm == 0){
            okk = KM; memcpy(Aok, A, (size_t)N * KMAX);
            if (KM >= 1 && KM > k0) { writeca(pre); }
            fprintf(stderr, "k=%d covered  t=%.1fs moves=%lld\n", KM, now() - tst, moves);
            if (KM == KMAX) break;
            DUPC = getenv("DUP") ? redundant_column() : -1; int z = bestcolumn(x, COLTRY);
            for (int r = 0; r < N; r++) A[(size_t)r * KMAX + KM] = x[r];
            addcol(); fails = 0; tcol = now(); best = nm; T = T0; stall = 0; memcpy(Abest, A, (size_t)N * KMAX);
            if (getenv("VERB")) fprintf(stderr, "  new column %d: column-LS missing %d\n", KM - 1, z);
            continue;
        }
        if (now() - tcol > COLSEC){
            fails++; if (fails >= MAXFAIL) break;
            if (okk == KM - 1){ memcpy(A, Aok, (size_t)N * KMAX); KM--; rebuild(); DUPC = getenv("DUP") ? redundant_column() : -1; int z = bestcolumn(x, COLTRY);
                for (int r = 0; r < N; r++) A[(size_t)r * KMAX + KM] = x[r]; addcol();
                if (getenv("VERB")) fprintf(stderr, "  retry column %d (fail %d, best was %lld): column-LS missing %d\n", KM - 1, fails, (long long)best, z); }
            tcol = now(); best = nm; T = T0; stall = 0; memcpy(Abest, A, (size_t)N * KMAX);
        }
        /* one temperature step */
        long L = (long)(LMUL * N * KM * VV); int64_t stepbest = best;
        for (long i = 0; i < L && nm; i++){
            moves++;
            if (urand() < P1){
                uint32_t m = ml[rnd((int)nm)]; uint32_t pc = m / VV; int t = m % VV; int c = pc / KMAX, c2 = pc % KMAX, a = t / V, b = t % V;
                int br = -1, bd = 1 << 30, nr = R1 > 0 ? R1 : N;
                for (int j = 0; j < nr; j++){ int r = R1 > 0 ? rnd(N) : j; uint8_t *row = A + (size_t)r * KMAX; int ra = row[c], rb = row[c2];
                    int d[3], dd = 0; if (ra != a){ deltas(r, c, d); dd = d[a]; setcell(r, c, a); }
                    if (rb != b){ deltas(r, c2, d); dd += d[b]; }
                    if (ra != a) setcell(r, c, ra);
                    if (dd < bd || (dd == bd && rnd(2))){ bd = dd; br = r; } }
                if (bd <= 0 || urand() < exp(-bd / T)){ setcell(br, c, a); setcell(br, c2, b); }
            } else {
                int r = rnd(N), c = rnd(KM), d[3]; deltas(r, c, d); int a = A[(size_t)r * KMAX + c];
                int b1 = (a + 1) % V, b2 = (a + 2) % V; int b = d[b1] < d[b2] ? b1 : d[b2] < d[b1] ? b2 : (rnd(2) ? b1 : b2);
                if (d[b] <= 0 || urand() < exp(-d[b] / T)) setcell(r, c, b);
            }
            if (nm < best){ best = nm; memcpy(Abest, A, (size_t)N * KMAX); }
        }
        if (best < stepbest || T > TSTALL) stall = 0; else stall++;
        if (!FIXT){ T *= ALPHA; if (T < TMIN) T = TMIN; }
        if (stall >= STALL){ memcpy(A, Abest, (size_t)N * KMAX); rebuild(); T = T0; stall = 0; }
    }
    fprintf(stderr, "end: largest covered k=%d at N=%d, t=%.1fs, moves=%lld (%.2f M/s)\n", okk, N, now() - tst, moves, moves / (now() - tst) / 1e6);
    if (okk > 0){ memcpy(A, Aok, (size_t)N * KMAX); KM = okk; writeca(pre); }
    printf("%d %d\n", N, okk);
    return 0;
}
