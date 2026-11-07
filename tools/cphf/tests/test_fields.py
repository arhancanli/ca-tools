#!/usr/bin/env python3
"""Tests of the fields of tools/cphf/cphfcheck.c for every prime power q <= 32, and of certificates over
alphabets above 25 (v = 27, 29, 31, 32) through the table (standard library only; needs a C compiler).

Usage: python3 tools/cphf/tests/test_fields.py [--no-derive]

  conway     the Conway polynomials computed here from their definition (the least monic primitive
             polynomial, in Conway's order, compatible with those of the subfields) equal the published
             values (F. Luebeck's tables) for q = 4, 8, 9, 16, 25, 27, 32
  tables     cphfcheck's addition and multiplication tables (its field_setup(), compiled into a harness
             without changing cphfcheck.c) equal those of GF(p)[x]/(f) for the Conway polynomial f, in
             the element coding of the family files, for every prime power q <= 32
  curves     the moment curves (1, x, x^2) and (1, x, x^2, x^3) over GF(q) are CPHF(1; q, q, 3) and
             CPHF(1; q, q, 4) for cphfcheck (Vandermonde), for every q; the same curve written with
             another irreducible polynomial than Conway's is not, with cphfcheck's count of uncovered
             t-sets equal to a brute force in Python
  brute      random families over GF(27), GF(29), GF(31) and GF(32): cphfcheck full and fullfast count
             the uncovered t-sets that a brute force in Python counts
  table      certificates at v = 27, 29, 31, 32 enter a copy of the table as VERIFIED (local exact check
             and --apply), pass the consistency checks, appear on the page with the note that there is no
             baseline for them, answer ca_table.py best, and (unless --no-derive) tools/derive_table.py
             runs on that table and its result passes the consistency check of derived.csv
Prints PASS/FAIL per test; exit status 0 only if everything passed.
"""
import csv
import itertools
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "tools"))
sys.path.insert(0, HERE)
import check_certificates as ck  # noqa: E402
import consistency  # noqa: E402
from test_certificates import fresh, consistency_problems, table_rows, quiet  # noqa: E402

RESULTS = []
PRIMES = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31]
QS = sorted(p ** e for p in PRIMES for e in range(1, 6) if p ** e <= 32)
# F. Luebeck, Conway polynomials for finite fields, coefficients of x^0, x^1, ..., x^e
KNOWN = {(2, 1): [1, 1], (2, 2): [1, 1, 1], (2, 3): [1, 1, 0, 1], (2, 4): [1, 1, 0, 0, 1],
         (2, 5): [1, 0, 1, 0, 0, 1], (3, 1): [1, 1], (3, 2): [2, 2, 1], (3, 3): [1, 2, 0, 1],
         (5, 1): [3, 1], (5, 2): [2, 4, 1]}


def record(name, ok, detail=""):
    RESULTS.append((name, ok))
    print("%s %s%s" % ("PASS" if ok else "FAIL", name, "" if ok else ": " + " ".join(str(detail).split())[-400:]),
          flush=True)


def pe(q):
    p = next(d for d in range(2, q + 1) if q % d == 0)
    e = 0
    while p ** (e + 1) <= q:
        e += 1
    return p, e


# ---------------------------------------------------------------------------------------------
# polynomials over GF(p), coefficients low first

def pmod(a, f, p):
    a = [x % p for x in a]
    while len(a) >= len(f):
        c = a[-1]
        if c:
            s = len(a) - len(f)
            for i, y in enumerate(f):
                a[s + i] = (a[s + i] - c * y) % p
        a.pop()
    return a


def pmul(a, b, f, p):
    r = [0] * (len(a) + len(b) - 1 if a and b else 0)
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            r[i + j] += x * y
    return pmod(r, f, p)


def ppow(a, n, f, p):
    r, b = [1], a
    while n:
        if n & 1:
            r = pmul(r, b, f, p)
        b = pmul(b, b, f, p); n >>= 1
    return r


def strip(a):
    a = list(a)
    while a and a[-1] == 0:
        a.pop()
    return a


def primes_of(n):
    out, d = [], 2
    while d * d <= n:
        if n % d == 0:
            out.append(d)
            while n % d == 0:
                n //= d
        d += 1
    return out + ([n] if n > 1 else [])


def primitive(f, p):
    n = len(f) - 1; order = p ** n - 1
    if strip(ppow([0, 1], order, f, p)) != [1]:
        return False
    return all(strip(ppow([0, 1], order // r, f, p)) != [1] for r in primes_of(order))


def conway(p, n, known):
    """the Conway polynomial C(p, n) from the definition, given C(p, m) for the proper divisors m of n:
    f = x^n + sum (-1)^(n-i) a_i x^i with (a_(n-1), ..., a_0) least, f primitive, and for every m the
    element x^((p^n - 1)/(p^m - 1)) a root of C(p, m)"""
    for alpha in itertools.product(range(p), repeat=n):          # (a_(n-1), ..., a_0), least first
        f = [0] * n + [1]
        for i in range(n):
            f[i] = ((-1) ** (n - i) * alpha[n - 1 - i]) % p
        if f[0] == 0 or not primitive(f, p):
            continue
        ok = True
        for m in range(1, n):
            if n % m:
                continue
            y = ppow([0, 1], (p ** n - 1) // (p ** m - 1), f, p)
            val, power = [0], [1]
            for c in known[(p, m)]:                                 # C(p, m) at y
                val = [(x + c * z) % p for x, z in itertools.zip_longest(val, power, fillvalue=0)]
                power = pmul(power, y, f, p)
            if strip(pmod(val, f, p)):
                ok = False
                break
        if ok:
            return f
    return None


class Field:
    """GF(q) in the coding of the family files: the element sum c_i p^i is c_0 + c_1 x + ..."""
    def __init__(self, q, f=None):
        self.q = q; self.p, self.e = pe(q)
        self.f = f or (KNOWN[(self.p, self.e)] if self.e > 1 else [0, 1])
        self.mul_t = [[self.mul_(a, b) for b in range(q)] for a in range(q)]
        self.add_t = [[self.add_(a, b) for b in range(q)] for a in range(q)]

    def vec(self, a):
        return [(a // self.p ** i) % self.p for i in range(self.e)]

    def code(self, v):
        return sum((c % self.p) * self.p ** i for i, c in enumerate(v))

    def add_(self, a, b):
        return self.code([x + y for x, y in zip(self.vec(a), self.vec(b))])

    def mul_(self, a, b):
        if self.e == 1:
            return a * b % self.q
        return self.code((pmul(self.vec(a), self.vec(b), self.f, self.p) + [0] * self.e)[:self.e])

    def rank(self, rows):
        M = [list(r) for r in rows]; r = 0; t = len(M[0])
        for c in range(t):
            piv = next((i for i in range(r, len(M)) if M[i][c]), None)
            if piv is None:
                continue
            M[r], M[piv] = M[piv], M[r]
            inv = next(b for b in range(1, self.q) if self.mul_t[M[r][c]][b] == 1)
            M[r] = [self.mul_t[x][inv] for x in M[r]]
            for i in range(len(M)):
                if i != r and M[i][c]:
                    neg = next(b for b in range(self.q) if self.add_t[M[i][c]][b] == 0)
                    M[i] = [self.add_t[x][self.mul_t[neg][y]] for x, y in zip(M[i], M[r])]
            r += 1
        return r


def digits(x, q, t):
    return [(x // q ** (t - 1 - j)) % q for j in range(t)]


def brute_uncovered(F, fam, t):
    k = len(fam[0])
    return sum(1 for S in itertools.combinations(range(k), t)
               if not any(F.rank([digits(r[c], F.q, t) for c in S]) == t for r in fam))


def cphf_count(exe, path, t, q, mode):
    out = subprocess.run([exe, path, str(t), str(q), mode, "2"], stdout=subprocess.PIPE,
                         universal_newlines=True).stdout
    m = re.search(r"uncovered (\d+)", out)
    return int(m.group(1)) if m else None


def curve(F, t):
    """the moment curve (1, x, ..., x^(t-1)) over GF(q), one row of q codes"""
    row = []
    for x in range(F.q):
        v, pw = [], 1
        for _ in range(t):
            v.append(pw); pw = F.mul_t[pw][x]
        row.append(sum(c * F.q ** (t - 1 - j) for j, c in enumerate(v)))
    return [row]


def write_family(path, fam):
    with open(path, "w") as f:
        f.write("".join(" ".join(map(str, r)) + "\n" for r in fam))


def main():
    tmp = tempfile.mkdtemp(prefix="fieldtest-")
    try:
        run_all(tmp, "--no-derive" not in sys.argv[1:])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    bad = [n for n, ok in RESULTS if not ok]
    print("%d tests, %d failed%s" % (len(RESULTS), len(bad), (": " + ", ".join(bad)) if bad else ""))
    return 1 if bad else 0


def run_all(tmp, derive):
    exe = ck.build(tmp)
    ck.build = lambda _tmp: exe
    rng = random.Random(1)

    # conway
    found = {}
    for p, n in sorted(KNOWN, key=lambda x: (x[1], x[0])):
        found[(p, n)] = conway(p, n, found)
        record("conway: C(%d, %d) from the definition is the published %s" % (p, n, KNOWN[(p, n)]),
               found[(p, n)] == KNOWN[(p, n)], found[(p, n)])

    # tables: cphfcheck's own field_setup(), compiled with its main renamed
    harness = os.path.join(tmp, "fieldtab.c")
    with open(harness, "w") as f:
        f.write('#define main cphfcheck_main\n#include "cphfcheck.c"\n#undef main\n'
                'int main(int argc, char **argv) {\n    q = atoi(argv[1]);\n'
                '    if (!field_setup()) { printf("unsupported\\n"); return 2; }\n'
                '    for (int a = 0; a < q; a++) for (int b = 0; b < q; b++) printf("%d %d\\n", ADD[a][b], MUL[a][b]);\n'
                '    return 0;\n}\n')
    tab = os.path.join(tmp, "fieldtab")
    subprocess.run(["cc", "-O1", "-w", "-I", os.path.join(REPO, "tools", "cphf"), "-o", tab, harness, "-lm"],
                   check=True)
    for q in QS:
        F = Field(q)
        out = subprocess.run([tab, str(q)], stdout=subprocess.PIPE, universal_newlines=True).stdout.split()
        want = [str(x) for a in range(q) for b in range(q) for x in (F.add_t[a][b], F.mul_t[a][b])]
        record("tables: cphfcheck's GF(%d) is GF(%d)[x]/(%s)" % (q, F.p, F.f if F.e > 1 else "x"), out == want,
               " ".join(out[:12]))
    out = subprocess.run([tab, "33"], stdout=subprocess.PIPE, universal_newlines=True).stdout
    record("tables: q = 33 and above are refused", "unsupported" in out, out[:60])

    # curves
    fam = os.path.join(tmp, "curve.txt")
    for q in [x for x in QS if x >= 3]:
        F = Field(q)
        for t in (3, 4):
            if q < t:
                continue
            write_family(fam, curve(F, t))
            record("curves: the moment curve of degree %d over GF(%d) is a CPHF(1; %d, %d, %d)" % (t - 1, q, q, q, t),
                   cphf_count(exe, fam, t, q, "full") == 0)
    for q, other in ((27, [2, 2, 0, 1]), (32, [1, 0, 0, 1, 0, 1]), (25, [2, 1, 1]), (16, [1, 0, 0, 1, 1])):
        G = Field(q, other)                    # another irreducible polynomial than Conway's
        if any(G.mul_t[a][b] == 0 for a in range(1, q) for b in range(1, q)):
            record("curves: GF(%d) with %s (not Conway's) is a field" % (q, other), False, other)
            continue
        write_family(fam, curve(G, 3))
        want = brute_uncovered(Field(q), curve(G, 3), 3)
        got = cphf_count(exe, fam, 3, q, "full")
        record("curves: the curve written with %s over GF(%d) is not a CPHF for cphfcheck: %s uncovered, brute force %d"
               % (other, q, got, want), got == want and want > 0, got)

    # brute
    for q in (27, 29, 31, 32):
        F = Field(q)
        for t, k, n in ((3, 12, 1), (3, 10, 2), (4, 8, 1)):
            fam_rows = [[rng.randrange(q ** t) for _ in range(k)] for _ in range(n)]
            if rng.random() < 0.5:
                fam_rows = [[x % q ** (t - 1) + q ** (t - 1) for x in r] for r in fam_rows]   # affine rows
            write_family(fam, fam_rows)
            want = brute_uncovered(F, fam_rows, t)
            got = (cphf_count(exe, fam, t, q, "full"), cphf_count(exe, fam, t, q, "fullfast"))
            record("brute: GF(%d), t = %d, k = %d, n = %d: cphfcheck full and fullfast %s, brute force %d"
                   % (q, t, k, n, got, want), got == (want, want))

    # table: certificates above v = 25 through a copy of the table
    root = fresh(tmp); tdir = os.path.join(root, "table")
    sub = os.path.join(root, "submissions", "test-v27-32")
    os.makedirs(sub)
    claims = []
    for q in (27, 29, 31, 32):
        write_family(os.path.join(sub, "curve%d.txt" % q), curve(Field(q), 3))
        claims.append(dict(t=3, v=q, k=q, N=q ** 3, file="curve%d.txt" % q, mode="", source_detail="test",
                           construction="test CPHF, moment curve", builds_on="cphf-smc2006", credit="Test Person",
                           notes=""))
    with open(os.path.join(sub, "certificates.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(ck.HEADER)
        for c in claims:
            w.writerow([c[x] for x in ck.HEADER])
    code, out = quiet(ck.main, [sub, "--table-dir", tdir, "--light", "--out", os.path.join(root, "light")])
    record("table: light check of v = 27, 29, 31, 32 passes", code == 0, out[-300:])
    code, out = quiet(ck.main, [sub, "--table-dir", tdir, "--threads", "2", "--apply"])
    rows = table_rows(root)
    new = [r for r in rows if int(r["v"]) > 25]
    record("table: VERIFIED rows at v = 27, 29, 31, 32", code == 0 and sorted(int(r["v"]) for r in new) == [27, 29, 31, 32]
           and all(r["tier"] == "VERIFIED" for r in new), out[-300:])
    pr = consistency_problems(root)
    record("table: consistency", not pr, "; ".join(pr[:3]))
    page = os.path.join(root, "index.html")
    p = subprocess.run([sys.executable, os.path.join(REPO, "tools", "render_table.py"), "--table-dir", tdir, "--out", page],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    html = open(page).read() if os.path.exists(page) else ""
    sec = html[html.find("t = 3, v = 27:"):][:3000]
    record("table: the page has t = 3, v = 27 with the note that there is no baseline",
           p.returncode == 0 and "t = 3, v = 27:" in html and "no baseline for this strength and alphabet" in sec
           and html.count("no baseline for this strength and alphabet") == 4, p.stdout[-300:])
    p = subprocess.run([sys.executable, os.path.join(tdir, "ca_table.py"), "best", "3", "27", "27"],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True,
                       env=dict(os.environ, CA_TABLE=os.path.join(tdir, "ca_table.csv")))
    record("table: ca_table.py best 3 27 27 answers 19683", "19683" in p.stdout, p.stdout[-300:])
    if derive:
        der = os.path.join(root, "derived.csv")
        p = subprocess.run([sys.executable, os.path.join(REPO, "tools", "derive_table.py"), "--out", der],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True,
                           env=dict(os.environ, CA_TABLE=os.path.join(tdir, "ca_table.csv")))
        shutil.copy(der, os.path.join(tdir, "derived.csv"))
        cwd = os.getcwd(); os.chdir(root)
        try:
            consistency.problems.clear()
            raw, rws, man = consistency.load()
            n = consistency.check_derived(rws)
            prob = list(consistency.problems)
        finally:
            os.chdir(cwd)
        record("table: derive_table.py runs with rows above v = 25 and its %d lines pass check_derived" % n,
               p.returncode == 0 and not prob, (p.stdout[-200:] + " ".join(prob[:2])))


if __name__ == "__main__":
    sys.exit(main())
