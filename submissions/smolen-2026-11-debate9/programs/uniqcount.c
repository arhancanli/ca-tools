/* uniqcount.c - for a binary array and a strength t, count for every row the number of
 * t-sets of columns on which that row is the only row showing its value tuple (its "unique"
 * t-way interactions). A row with count 0 can be deleted and the array stays a covering array
 * of strength t; small counts mark the rows a row-elimination search should try first.
 * Exact; nothing is sampled. Written for ca-tools, 2026-11-03.
 *
 * Method (the grouping of ca_verify version 2): every t-set is its t-1 smallest columns P plus
 * its largest column d. For a fixed P the rows are split into classes by their values on P
 * (depth-first, refining the classes one column at a time). In a class, for all later columns
 * d at once, two bit vectors over d record whether 1 is seen once or at least twice, and two
 * more do the same for 0; a value seen exactly once at d is a unique interaction of the row
 * that holds it. A second pass over the class gives each row its count. A value seen zero
 * times at d is a missing interaction (the array is then not covering at strength t; counted).
 *
 * Usage: uniqcount FILE t [threads]      (FILE: rows of 0/1 separated by spaces)
 * Output: one line per row "row count", then totals. Build: cc -O3 -pthread -o uniqcount uniqcount.c
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <pthread.h>

static int N, K, T, KW, NT = 4;
static uint8_t *A;               /* N x K */
static uint64_t *RB;             /* N x KW: bit c set iff A[r][c] == 1 */
static int next_c0 = 0;
static pthread_mutex_t mu = PTHREAD_MUTEX_INITIALIZER;

typedef struct {
    long long *uniq;             /* N */
    long long missing;
    int *lists;                  /* (T) levels x N row lists */
    int *starts;                 /* (T) levels x (N+1) class starts */
    int *ncls;                   /* T */
    int *P;
    uint64_t *o1, *t1, *o0, *t0; /* KW each */
} Work;

static void final_class(Work *w, const int *L, int m, int c) {
    const int w0 = (c + 1) >> 6;
    for (int x = w0; x < KW; x++) { w->o1[x] = w->t1[x] = w->o0[x] = w->t0[x] = 0; }
    for (int i = 0; i < m; i++) {
        const uint64_t *rb = &RB[(size_t)L[i] * KW];
        for (int x = w0; x < KW; x++) {
            uint64_t b1 = rb[x], b0 = ~rb[x];
            w->t1[x] |= w->o1[x] & b1; w->o1[x] |= b1;
            w->t0[x] |= w->o0[x] & b0; w->o0[x] |= b0;
        }
    }
    for (int x = w0; x < KW; x++) {
        uint64_t valid = ~0ULL;
        if (x == w0 && ((c + 1) & 63)) valid &= ~0ULL << ((c + 1) & 63);
        if (x == KW - 1 && (K & 63)) valid &= (1ULL << (K & 63)) - 1;
        w->missing += __builtin_popcountll(valid & ~w->o1[x]) + __builtin_popcountll(valid & ~w->o0[x]);
        w->o1[x] = valid & w->o1[x] & ~w->t1[x];     /* exactly one row with 1 */
        w->o0[x] = valid & w->o0[x] & ~w->t0[x];     /* exactly one row with 0 */
    }
    for (int i = 0; i < m; i++) {
        const uint64_t *rb = &RB[(size_t)L[i] * KW];
        long long s = 0;
        for (int x = w0; x < KW; x++)
            s += __builtin_popcountll(w->o1[x] & rb[x]) + __builtin_popcountll(w->o0[x] & ~rb[x]);
        w->uniq[L[i]] += s;
    }
}

/* classes at level j (prefix of j columns) are in lists[j], starts[j], ncls[j] */
static void dfs(Work *w, int j) {
    const int *L = w->lists + (size_t)j * N, *S = w->starts + (size_t)j * (N + 1);
    const int nc = w->ncls[j];
    if (j == T - 1) {
        /* prefix tuples that no row shows: both values missing at every later column */
        w->missing += (long long)((1LL << (T - 1)) - nc) * 2 * (K - 1 - w->P[T - 2]);
        for (int g = 0; g < nc; g++) final_class(w, L + S[g], S[g + 1] - S[g], w->P[T - 2]);
        return;
    }
    int *L2 = w->lists + (size_t)(j + 1) * N, *S2 = w->starts + (size_t)(j + 1) * (N + 1);
    const int lo = w->P[j - 1] + 1, hi = K - T + j;
    for (int c = lo; c <= hi; c++) {
        w->P[j] = c;
        int n = 0, g2 = 0;
        for (int g = 0; g < nc; g++) {
            const int a = S[g], b = S[g + 1];
            for (int v = 0; v < 2; v++) {
                const int st = n;
                for (int i = a; i < b; i++) if (A[(size_t)L[i] * K + c] == v) L2[n++] = L[i];
                if (n > st) S2[g2++] = st;
            }
        }
        S2[g2] = n; w->ncls[j + 1] = g2;
        dfs(w, j + 1);
    }
}

static void *worker(void *arg) {
    Work *w = (Work *)arg;
    for (;;) {
        pthread_mutex_lock(&mu); int c0 = next_c0++; pthread_mutex_unlock(&mu);
        if (c0 > K - T) break;
        w->P[0] = c0;
        int *L = w->lists + N, *S = w->starts + (N + 1);
        int n = 0, g = 0;
        for (int v = 0; v < 2; v++) {
            const int st = n;
            for (int r = 0; r < N; r++) if (A[(size_t)r * K + c0] == v) L[n++] = r;
            if (n > st) S[g++] = st;
        }
        S[g] = n; w->ncls[1] = g;
        if (T == 2) { w->missing += (long long)(2 - g) * 2 * (K - 1 - c0); for (int q = 0; q < g; q++) final_class(w, L + S[q], S[q + 1] - S[q], c0); }
        else dfs(w, 1);
    }
    return NULL;
}

int main(int argc, char **argv) {
    if (argc < 3) { fprintf(stderr, "usage: uniqcount FILE t [threads]\n"); return 2; }
    T = atoi(argv[2]); if (argc > 3) NT = atoi(argv[3]);
    if (T < 2 || T > 20) { fprintf(stderr, "t must be 2..20\n"); return 2; }
    FILE *f = fopen(argv[1], "r"); if (!f) { perror("open"); return 2; }
    size_t cap = 1 << 20, n = 0; int *buf = malloc(cap * sizeof(int)); int rows = 0, kin = -1, cur = 0, ch, val = -1;
    while (1) {
        ch = fgetc(f);
        if (ch >= '0' && ch <= '9') { val = (val < 0 ? 0 : val * 10) + (ch - '0'); continue; }
        if (val >= 0) { if (n == cap) { cap *= 2; buf = realloc(buf, cap * sizeof(int)); } buf[n++] = val; cur++; val = -1; }
        if (ch == '\n' || ch == EOF) { if (cur) { if (kin < 0) kin = cur; else if (cur != kin) { fprintf(stderr, "ragged\n"); return 2; } rows++; } cur = 0; if (ch == EOF) break; }
    }
    fclose(f);
    N = rows; K = kin; KW = (K + 63) / 64;
    int mn = 1 << 30, mx = -1; for (size_t i = 0; i < n; i++) { if (buf[i] < mn) mn = buf[i]; if (buf[i] > mx) mx = buf[i]; }
    if (mx - mn > 1) { fprintf(stderr, "not binary\n"); return 2; }
    A = malloc((size_t)N * K); RB = calloc((size_t)N * KW, sizeof(uint64_t));
    for (int r = 0; r < N; r++) for (int c = 0; c < K; c++) { int b = buf[(size_t)r * K + c] - mn; A[(size_t)r * K + c] = (uint8_t)b; if (b) RB[(size_t)r * KW + (c >> 6)] |= 1ULL << (c & 63); }
    fprintf(stderr, "read %d rows x %d columns, t = %d, %d threads\n", N, K, T, NT);
    pthread_t *th = malloc(sizeof(pthread_t) * NT); Work *W = calloc(NT, sizeof(Work));
    for (int i = 0; i < NT; i++) {
        W[i].uniq = calloc(N, sizeof(long long));
        W[i].lists = malloc(sizeof(int) * (size_t)T * N);
        W[i].starts = malloc(sizeof(int) * (size_t)T * (N + 1));
        W[i].ncls = calloc(T, sizeof(int)); W[i].P = calloc(T, sizeof(int));
        W[i].o1 = malloc(8 * KW); W[i].t1 = malloc(8 * KW); W[i].o0 = malloc(8 * KW); W[i].t0 = malloc(8 * KW);
        pthread_create(&th[i], NULL, worker, &W[i]);
    }
    long long missing = 0; long long *u = calloc(N, sizeof(long long));
    for (int i = 0; i < NT; i++) { pthread_join(th[i], NULL); missing += W[i].missing; for (int r = 0; r < N; r++) u[r] += W[i].uniq[r]; }
    long long tot = 0, zero = 0, mn_u = -1; int arg = -1;
    for (int r = 0; r < N; r++) { printf("%d %lld\n", r, u[r]); tot += u[r]; if (u[r] == 0) zero++; if (mn_u < 0 || u[r] < mn_u) { mn_u = u[r]; arg = r; } }
    printf("# missing interactions %lld (0 = covering at strength %d)\n", missing, T);
    printf("# rows with no unique interaction %lld; smallest count %lld (row %d); total %lld\n", zero, mn_u, arg, tot);
    return 0;
}
