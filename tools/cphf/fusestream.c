/* fusestream.c - the fusing steps of an expansion rule (tools/cphf/README.md, "Expansion rules") applied to a
 * covering array in the table's canonical text, as a stream: one run in, at most one run out, never the whole
 * array in memory (fuse2.c holds its result in memory for its spot check; here the spot check is streamed too).
 *
 * usage: fusestream IN q STEP... [check t S seed] > OUT
 *   IN     the array in canonical text over the symbols 0..q-1 (one run per line, single spaces), a file or a
 *          FIFO; "-" reads stdin
 *   STEP   "fuse a b"  symbol a is written as b in every entry: the same runs, one symbol fewer
 *          "fuse2 a"   symbol a is removed with two runs, as fuse2.c does: the first run Z of this step's input
 *                      is made constant a by the transposition Z[c] <-> a in every column and deleted; the next
 *                      run after the same transposition is R, and is deleted; in every other run, after the
 *                      transposition, each a in column c is replaced by R[c] (by 0 where R[c] = a)
 *          (Colbourn, Keri, Rivas Soriano and Schlage-Puchta 2010, Lemma 3.1.) The steps act in order, each on the
 *          output of the one before, and each removes the largest symbol of its input: a = (symbols before it) - 1,
 *          and b < a. The rule "smc-1-affine+fuse2 6+fuse 5>0" is "fuse2 6 fuse 5 0" after expanding with q = 7.
 *   check  a spot check of the output (evidence, not proof): S random sets of t distinct columns (xorshift64 from
 *          seed), each of which must show all v^t tuples in the runs written; S is lowered so that the tuples
 *          seen take at most 256 MB. Its line "spot check: S random t-sets, uncovered U" goes to stderr.
 * Output: the fused array in canonical text, symbols 0..v-1 with v = q less the number of steps.
 * Exit 0; 1 when a spot-checked set misses a tuple; 2 on a usage error or a malformed input (an entry that is not
 * a symbol below q, a ragged run, fewer runs than the fuse2 steps remove, an output entry at or above v).
 * Build: cc -O2 -o fusestream fusestream.c */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#define MAXSTEPS 64
static int nst, kind[MAXSTEPS], A[MAXSTEPS], B[MAXSTEPS], state[MAXSTEPS];   /* kind 1 fuse, 2 fuse2 */
static unsigned char *Z[MAXSTEPS], *R[MAXSTEPS];

static int die(const char *msg, long run) {
    if (run >= 0) fprintf(stderr, "fusestream: %s (input run %ld)\n", msg, run + 1);
    else fprintf(stderr, "fusestream: %s\n", msg);
    return 2;
}

int main(int argc, char **argv) {
    if (argc < 4) return die("usage: fusestream IN q STEP... [check t S seed]", -1);
    int q = atoi(argv[2]), v = q, ct = 0;
    long cS = 0; uint64_t seed = 0;
    if (q < 2 || q > 255) return die("q must be 2..255", -1);
    for (int i = 3; i < argc; ) {
        if (!strcmp(argv[i], "check") && i + 4 == argc) {
            ct = atoi(argv[i + 1]); cS = atol(argv[i + 2]); seed = strtoull(argv[i + 3], NULL, 10); i += 4;
            if (ct < 2 || ct > 8 || cS < 1) return die("check t S seed needs 2 <= t <= 8 and S >= 1", -1);
            continue;
        }
        if (nst == MAXSTEPS) return die("too many steps", -1);
        if (!strcmp(argv[i], "fuse") && i + 2 < argc) {
            kind[nst] = 1; A[nst] = atoi(argv[i + 1]); B[nst] = atoi(argv[i + 2]); i += 3;
            if (B[nst] < 0 || B[nst] >= A[nst]) return die("fuse a b needs b < a", -1);
        } else if (!strcmp(argv[i], "fuse2") && i + 1 < argc) {
            kind[nst] = 2; A[nst] = atoi(argv[i + 1]); i += 2;
        } else return die("a step is \"fuse a b\" or \"fuse2 a\", then optionally \"check t S seed\"", -1);
        if (A[nst] != v - 1 || v - 1 < 2) return die("each step removes the largest symbol of its input, leaving at least two", -1);
        v--; nst++;
    }
    FILE *in = strcmp(argv[1], "-") ? fopen(argv[1], "rb") : stdin;
    if (!in) { perror(argv[1]); return 2; }
    static char ibuf[1 << 20], obuf[1 << 20];
    setvbuf(stdout, obuf, _IOFBF, sizeof obuf);
    size_t cap = 1 << 16, olen, W = 0; long k = -1, col, run = 0;
    unsigned char *row = malloc(cap); char *line = NULL;
    int *cols = NULL; uint64_t *seen = NULL;
    size_t got = 0, pos = 0; int val = -1, ch;
    for (;;) {                                   /* one run per pass: parse, apply the steps, write */
        col = 0;
        for (;;) {
            if (pos == got) { got = fread(ibuf, 1, sizeof ibuf, in); pos = 0; if (!got) { ch = EOF; break; } }
            ch = (unsigned char)ibuf[pos++];
            if (ch >= '0' && ch <= '9') { val = (val < 0 ? 0 : val * 10) + (ch - '0'); if (val >= q) return die("an entry is not a symbol below q", run); continue; }
            if (ch != ' ' && ch != '\n') return die("a character other than digits, single spaces and line feeds", run);
            if (val >= 0) { if ((size_t)col == cap) { cap *= 2; row = realloc(row, cap); } row[col++] = (unsigned char)val; val = -1; }
            if (ch == '\n') break;
        }
        if (ch == EOF && val >= 0) { if ((size_t)col == cap) { cap *= 2; row = realloc(row, cap); } row[col++] = (unsigned char)val; val = -1; }
        if (col == 0) { if (ch == EOF) break; return die("an empty line", run); }
        if (k < 0) {
            k = col;
            for (int s = 0; s < nst; s++) if (kind[s] == 2) { Z[s] = malloc(k); R[s] = malloc(k); }
            line = malloc((size_t)k * 4 + 2);
            if (ct) {                            /* the spot-checked sets: distinct columns, drawn once */
                if (ct > k) return die("check t needs t <= k", -1);
                double vt = 1; for (int j = 0; j < ct; j++) vt *= v;
                if (vt > (double)(1u << 31)) return die("check: v^t is too large to spot-check", -1);
                W = ((size_t)vt + 63) / 64;
                if ((double)cS * W * 8 > 256e6) cS = (long)(256e6 / (W * 8.0)) > 0 ? (long)(256e6 / (W * 8.0)) : 1;
                cols = malloc((size_t)cS * ct * sizeof(int)); seen = calloc((size_t)cS * W, 8);
                if (!cols || !seen) return die("out of memory for the spot check", -1);
                uint64_t x = seed ? seed : 0x9E3779B97F4A7C15ULL;
                for (long s = 0; s < cS; s++)
                    for (int j = 0; j < ct; ) {
                        x ^= x << 13; x ^= x >> 7; x ^= x << 17;
                        int c = (int)(x % (uint64_t)k), dup = 0;
                        for (int i = 0; i < j; i++) if (cols[s * ct + i] == c) dup = 1;
                        if (!dup) cols[s * ct + j++] = c;
                    }
            }
        } else if (col != k) return die("a run of another length than the first", run);
        int keep = 1;
        for (int s = 0; s < nst && keep; s++) {
            unsigned char a = (unsigned char)A[s];
            if (kind[s] == 1) { unsigned char b = (unsigned char)B[s]; for (long c = 0; c < k; c++) if (row[c] == a) row[c] = b; continue; }
            if (state[s] == 0) { memcpy(Z[s], row, k); state[s] = 1; keep = 0; break; }
            const unsigned char *z = Z[s];
            for (long c = 0; c < k; c++) { unsigned char x = row[c]; if (x == z[c]) x = a; else if (x == a) x = z[c]; row[c] = x; }
            if (state[s] == 1) { memcpy(R[s], row, k); state[s] = 2; keep = 0; break; }
            const unsigned char *r = R[s];
            for (long c = 0; c < k; c++) if (row[c] == a) row[c] = r[c] == a ? 0 : r[c];
        }
        if (keep) {
            olen = 0;
            for (long c = 0; c < k; c++) {
                unsigned x = row[c];
                if (x >= (unsigned)v) return die("an output entry is not below v", run);
                if (c) line[olen++] = ' ';
                if (x >= 100) { line[olen++] = (char)('0' + x / 100); x %= 100; line[olen++] = (char)('0' + x / 10); line[olen++] = (char)('0' + x % 10); }
                else if (x >= 10) { line[olen++] = (char)('0' + x / 10); line[olen++] = (char)('0' + x % 10); }
                else line[olen++] = (char)('0' + x);
            }
            line[olen++] = '\n';
            if (fwrite(line, 1, olen, stdout) != olen) return die("write failed", run);
            for (long s = 0; s < cS && ct; s++) {
                uint64_t idx = 0; const int *cs = cols + s * ct;
                for (int j = 0; j < ct; j++) idx = idx * v + row[cs[j]];
                seen[s * W + idx / 64] |= 1ULL << (idx % 64);
            }
        }
        run++;
        if (ch == EOF) break;
    }
    if (k < 0) return die("no runs", -1);
    for (int s = 0; s < nst; s++) if (kind[s] == 2 && state[s] != 2) return die("fewer runs than the fuse2 steps remove", -1);
    if (fflush(stdout)) return die("write failed", -1);
    if (ct) {
        uint64_t vt = 1; for (int j = 0; j < ct; j++) vt *= (uint64_t)v;
        long bad = 0;
        for (long s = 0; s < cS; s++) {
            uint64_t n = 0;
            for (size_t w = 0; w < W; w++) n += (uint64_t)__builtin_popcountll(seen[s * W + w]);
            if (n < vt) bad++;
        }
        fprintf(stderr, "spot check: %ld random %d-sets, uncovered %ld\n", cS, ct, bad);
        return bad ? 1 : 0;
    }
    return 0;
}
