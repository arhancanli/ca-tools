#!/usr/bin/env python3
"""test_smx.py - tests of the construction certificate kind sm-xplication-1 (tools/construction_cert.py) and of
tools/sm_xplication.py, the x-plication arrays of Shokri and Moura (J. Combin. Des. 33 (2025) 156-171, thesis of
K. Shokri, doi:10.20381/ruor-31663, Chapter 5).

Part 1, the script and the checker: for the five theorems at small q the script's certificate is accepted, the array
the checker writes (--write) is byte for byte the script's, and ca_verify verifies it on every 3-set. The script
reproduces published arrays with their sha256 (the constants in REFERENCE, Bai XunDi's arrays of Zenodo 23787055 and
T. N. Sitjar's arrays from the thesis); a reducible modulus is reported by the field check.

Part 2, random certificates against an independent oracle. The oracle decides every hypothesis by its definition
(2 x 2 and 3 x 3 determinants over F_q on every pair and 3-set of columns, numpy counts for P, D and the last block),
builds the array with numpy and checks it with ca_verify. Assertions, as for the other kinds:
  A1 the checker accepts exactly when the oracle finds every hypothesis true and N, k and sha256 as claimed;
  A2 every check agrees with the oracle on its own hypothesis, and a planted fault is reported;
  A3 every accepted certificate gives a covering array (ca_verify) with the oracle's sha256, and the array the
     checker writes has that sha256;
  A4 every certificate whose hypotheses all hold gives a covering array (the theorem).
Then mutation testing: each check is disabled in turn, some together with the cubic check (points and cphf follow
from a primitive cubic, so they can only fail alone when cubic is off), and boundary mutants are applied. A mutant is
killed when A1 or A2 fails on a case that passed without it.

Part 3: the ten real certificates of submissions/smolen-2026-11-sm-xplication pass with their recorded sha256, and
planted faults on two of them are rejected by the intended check.

Usage: test_smx.py [--cases N] [--seed S] [--skip-real] [--quick]   (exit 1 on any violation or surviving mutant)
"""
import hashlib
import itertools
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
TOOLS = os.path.join(ROOT, "tools")
sys.path.insert(0, TOOLS)
import construction_cert as cc  # noqa: E402
import sm_xplication as smx  # noqa: E402
from sms_theorem51 import GF, write_rows, HashOut  # noqa: E402

SCRIPT = os.path.join(TOOLS, "sm_xplication.py")
REAL_DIR = os.path.join(ROOT, "submissions", "smolen-2026-11-sm-xplication")

# (theorem, q, script options, sha256 of the published array, the array)
REFERENCE = [
    ("2", 3, {}, "d531431a6d89288d630d5ff8441b794a698cca9939c2360dc69185bb1fb584b9", "Bai XunDi CA(69; 3, 26, 3)"),
    ("2", 5, {}, "23f6abba2ec4ca334d093e50ae8243eadf005b4f2d718e96123390f6d8d891e8", "Bai XunDi CA(385; 3, 62, 5)"),
    ("2", 7, {}, "eab6f35097720284f5bd9e8113549d465f6c7c8de4eda2e68461b45de26dab37", "Bai XunDi CA(1141; 3, 114, 7)"),
    ("2", 9, {}, "52edb50fb980db50f33edd7a62fac3d8426c3eab960cf6234181a302317be965", "Bai XunDi CA(2529; 3, 182, 9)"),
    ("2", 13, {}, "77cfc867093f337a748be7a8c42fd44b1b5e1960376a606f23f8bba48660e3ad", "Bai XunDi CA(7969; 3, 366, 13)"),
    ("2", 16, {"modulus": [1, 1, 0, 0]}, "67bb6feda0a2bb1028e31730cb036982d7a60014de148b0b97e10df53caabbe8",
     "Bai XunDi CA(15136; 3, 546, 16)"),
    ("2", 17, {}, "fcf90589c197e5dc62ef25032d13973992df9a7d62613e9e10beba4b12c05791", "Bai XunDi CA(18241; 3, 614, 17)"),
    ("2", 19, {}, "edfe1661655285038d9b0375b89c834f75c4c92d7f0d13bb85128f6883284705", "Bai XunDi CA(25669; 3, 762, 19)"),
    ("q", 4, {}, "6450b5cf56f4906f352a0edca7e582518a8af4ddc20d28b751e14b3deef1015e", "Bai XunDi CA(232; 3, 84, 4)"),
    ("q", 5, {}, "d9bc2ae7c08a42ddb2aa38de6e511c790c0f6337f527c25e6ac2a1fd11adb077", "Bai XunDi CA(485; 3, 155, 5)"),
    ("q", 7, {}, "70e0a5cafb6299d589124772495f33d5639e78bee8ef484f8bf1449bb04522a5", "Bai XunDi CA(1435; 3, 399, 7)"),
    ("q", 8, {"modulus": [1, 1, 0]}, "24addefe40a5a6f6a7a43d0fd8fac13312d16154630b54b97a544047db4a2bf5",
     "Bai XunDi CA(2192; 3, 584, 8)"),
    ("q", 9, {}, "8afc6a671c5f61caf290d0932a2266b525aca921b884abf84feb2c1a6e31676f", "Bai XunDi CA(3177; 3, 819, 9)"),
    ("q", 11, {}, "136a61dabfa04dc98ccfd9d16958e45f6eaff503ce47f27701ba2e4dad576f01", "Bai XunDi CA(5951; 3, 1463, 11)"),
    ("q", 13, {}, "a9f9ab57a0fe5521da8941a971e2610be7221821089a0e9fda406f8981bc8e06", "Bai XunDi CA(9997; 3, 2379, 13)"),
    ("q2even", 4, {}, "5b83ca0d1013c123cff95997925456750ec8ca0b2b85372d84cbbc0227daab4e",
     "T. N. Sitjar CA(364; 3, 336, 4), thesis Corollary 5.2.12"),
    ("q2", 5, {"cubic": [2, 3, 0]}, "935caf9eddc8d495591eda86dd7ff1e0e04e16bc1158b0439cc8d2388a100810",
     "T. N. Sitjar CA(769; 3, 775, 5), thesis Theorem 5.2.11"),
    ("q2q1", 5, {"cubic": [2, 3, 0]}, "8bb6455364a594936732c1eedf0ddbc8eb77f668ed5118e35204918edbf160e2",
     "T. N. Sitjar CA(765; 3, 651, 5), thesis Theorem 5.2.13"),
]

SCRIPT_CASES = [("2", 2), ("2", 3), ("2", 4), ("2", 5), ("q", 3), ("q", 4), ("q", 5), ("q", 7), ("q2", 2), ("q2", 3),
                ("q2", 4), ("q2even", 2), ("q2even", 4), ("q2q1", 3), ("q2q1", 4), ("q2q1", 5)]
QUICK_SCRIPT_CASES = [("2", 3), ("q", 3), ("q", 4), ("q2", 3), ("q2even", 4), ("q2q1", 3)]


class Sink:
    def write(self, b):
        pass


def canon_sha(M):
    h = HashOut(Sink())
    write_rows(np.asarray(M, dtype=np.uint8), h)
    return h.h.hexdigest()


def script_sha(thm, q, opts):
    b = smx.Build(thm, q, opts.get("modulus"), opts.get("cubic"))
    h = HashOut(Sink())
    for R in b.rows():
        write_rows(R, h)
    return h.h.hexdigest()


def run_checker(path, write=None):
    try:
        r = cc.run(path, write)
        return r["ok"], {f[0] for f in r["failures"]}, r["sha256"]
    except cc.CertError as e:
        return False, {"malformed: %s" % e}, None


# ---------------------------------------------------------------------------------------------
# the oracle: every hypothesis by its definition, the array with numpy

def field_of(cert):
    fd = cert["field"]
    return GF(fd["q"], fd.get("modulus", [0, 1])[:-1] if fd["m"] > 1 else None)


def det2(F, a, b, c, d):
    return F.add[F.mul[a][d]][F.neg[F.mul[b][c]]]


def det3(F, u, v, w):
    """the determinant of the 3 x 3 matrix with columns u, v, w (cofactor expansion along the first row)"""
    m, a = F.mul, F.add
    t1 = m[u[0]][det2(F, v[1], w[1], v[2], w[2])]
    t2 = m[v[0]][det2(F, u[1], w[1], u[2], w[2])]
    t3 = m[w[0]][det2(F, u[1], v[1], u[2], v[2])]
    return a[a[t1][F.neg[t2]]][t3]


def oracle_powers(F, f):
    """x^e mod f, e = 0 .. q^3 - 2, as coefficient lists (constant first), by multiplying by x"""
    q = F.q
    cur = [1, 0, 0]
    out = []
    for _ in range(q ** 3 - 1):
        out.append(tuple(cur))
        top = cur[2]
        cur = [F.neg[F.mul[top][f[0]]], F.add[cur[0]][F.neg[F.mul[top][f[1]]]], F.add[cur[1]][F.neg[F.mul[top][f[2]]]]]
    return out, cur == [1, 0, 0]


def oracle(cert):
    """{hypothesis: True/False} and the rebuilt array (numpy) or None when it cannot be built"""
    F = field_of(cert)
    q = F.q
    hyp = {}
    f = cert["cubic"]
    L, back = oracle_powers(F, f)
    n = q ** 3 - 1
    hyp["cubic"] = back and len(set(L)) == n        # x^n = 1 and x^0 .. x^(n-1) distinct: x has order n
    k0 = q * q + q + 1
    G1 = [L[j % n] for j in range(k0)]
    G2 = [L[(-j) % n] for j in range(k0)]
    ok = True
    for G in (G1, G2):
        for i, j in itertools.combinations(range(k0), 2):
            u, v = G[i], G[j]
            if all(det2(F, u[r], v[r], u[s], v[s]) == 0 for r, s in ((0, 1), (0, 2), (1, 2))):
                ok = False
                break
        if not ok:
            break
    hyp["points"] = ok
    hyp["cphf"] = all(det3(F, G1[a], G1[b], G1[c]) or det3(F, G2[a], G2[b], G2[c])
                      for a, b, c in itertools.combinations(range(k0), 3))
    pts = cert.get("points", list(range(q)))
    P = smx.cor519(F, pts)[:, :k0].astype(np.int64)
    hyp["P"] = all(len(np.unique(P[:, a] * q + P[:, b])) == q * q for a, b in itertools.combinations(range(k0), 2))
    D = np.array(cert["dca"], dtype=np.int64)
    x = D.shape[1]
    ADD = np.array(F.add)
    NEG = np.array(F.neg)
    hyp["dca"] = all(len(np.unique(ADD[D[:, b], NEG[D[:, a]]])) == q for a, b in itertools.combinations(range(x), 2))
    ED = [tuple(int(ADD[d, a]) for d in r) for r in D for a in range(q)]
    seen, C = set(ED), []
    for H in cert["last"]:
        Hm = np.array(H, dtype=np.int64)
        for u in itertools.product(range(q), repeat=3):
            row = tuple(int(F.add[F.add[F.mul[u[0]][Hm[0, j]]][F.mul[u[1]][Hm[1, j]]]][F.mul[u[2]][Hm[2, j]]])
                        for j in range(x))
            if row not in seen:
                seen.add(row)
                C.append(row)
    E = np.array(sorted(set(ED)) + C, dtype=np.int64).reshape(-1, x)
    hyp["last"] = x < 3 or all(len(np.unique(E[:, a] * q * q + E[:, b] * q + E[:, c])) == q ** 3
                               for a, b, c in itertools.combinations(range(x), 3))
    # the array
    U = np.array(list(itertools.product(range(q), repeat=3)), dtype=np.int64)
    MUL = np.array(F.mul)

    def span(G):
        Gm = np.array(G, dtype=np.int64).T            # 3 x k0
        A = MUL[U[:, 0][:, None], Gm[0][None, :]]
        for i in (1, 2):
            A = ADD[A, MUL[U[:, i][:, None], Gm[i][None, :]]]
        return A
    blocks = [span(G1), span(G2)] + [P] * (D.shape[0] - 2)
    parts = [np.concatenate([ADD[B, D[r, l]] for l in range(x)], axis=1) for r, B in enumerate(blocks)]
    if C:
        parts.append(np.repeat(np.array(C, dtype=np.int64), k0, axis=1))
    X = np.vstack(parts)
    return hyp, X


def evaluate(cert):
    hyp, X = oracle(cert)
    fails = {k for k, v in hyp.items() if v is False}
    exp = cert["expected"]
    if exp["N"] != X.shape[0]:
        fails.add("N")
    if exp["k"] != X.shape[1]:
        fails.add("k")
    if exp["array_sha256"] != canon_sha(X):
        fails.add("sha256")
    return hyp, fails, X


# ---------------------------------------------------------------------------------------------
# cases

def random_cubic(rng, F, primitive):
    q = F.q
    while True:
        f = [rng.randrange(q), rng.randrange(q), rng.randrange(q), 1]
        if smx.is_primitive(F, f) == primitive or (not primitive and rng.random() < 0.2):
            return f


INSTANCES = {2: ["2", "q2", "q2even"], 3: ["2", "q", "q2", "q2q1"], 4: ["2", "q", "q2", "q2even", "q2q1"],
             5: ["2", "q", "q2q1"]}


def instance_case(rng, q):
    thm = rng.choice(INSTANCES[q])
    F = GF(q)
    for _ in range(50):
        f = random_cubic(rng, F, True)
        try:
            b = smx.Build(thm, q, None, f[:3])
            break
        except ValueError:
            continue
    else:
        b = smx.Build(thm, q)
    cert = b.certificate()
    if rng.random() < 0.3:
        pts = list(range(q))
        rng.shuffle(pts)
        cert["points"] = pts
    return thm, cert


def random_case(rng, q):
    F = GF(q)
    x = rng.randint(2, 5)
    m = rng.randint(2, q + 2)
    a = smx.points(F)[1]
    if rng.random() < 0.6 and x <= q:
        cols = rng.sample(range(q), x)
        D = [[F.mul[a[r % q]][a[c]] for c in cols] for r in range(max(m, q))]
    else:
        D = [[rng.randrange(q) for _ in range(x)] for _ in range(m)]
    last = []
    for _ in range(rng.choice((0, 1, 1, 2))):
        if rng.random() < 0.5 and x <= q:
            pts = rng.sample(a, x)
            last.append([[F.mul[b][b] for b in pts], list(pts), [1] * x])
        else:
            last.append([[rng.randrange(q) for _ in range(x)] for _ in range(3)])
    cert = {"format": "construction-cert-1", "construction": "sm-xplication-1", "t": 3, "v": q,
            "field": smx.field_json(F), "cubic": random_cubic(rng, F, rng.random() < 0.6),
            "dca": D, "last": last}
    if rng.random() < 0.5:
        pts = list(range(q))
        rng.shuffle(pts)
        cert["points"] = pts
    return "random", cert


FAULTS = ["cubic", "dca", "last", "N", "sha256"]


def plant(rng, cert, fault):
    F = field_of(cert)
    q = F.q
    if fault == "cubic":
        cert["cubic"] = random_cubic(rng, F, False)
    elif fault == "dca":
        r = rng.randrange(len(cert["dca"]))
        c = rng.randrange(len(cert["dca"][0]))
        cert["dca"][r][c] = (cert["dca"][r][c] + 1 + rng.randrange(q - 1)) % q if q > 1 else 0
    elif fault == "last":
        if cert["last"]:
            H = rng.choice(cert["last"])
            r, c = rng.randrange(3), rng.randrange(len(H[0]))
            H[r][c] = (H[r][c] + 1) % q
        else:
            fault = "N"
    if fault == "N":
        cert["expected"]["N"] += 1
    elif fault == "sha256":
        s = cert["expected"]["array_sha256"]
        cert["expected"]["array_sha256"] = ("0" if s[0] != "0" else "1") + s[1:]
    return fault


def targeted():
    """certificates in which a single hypothesis (or k) fails; the expected values are those of the array"""
    out = []

    def inst(thm, q):
        return smx.Build(thm, q).certificate()
    for q in (3, 4, 5):
        c = inst("q", q)
        c["last"] = []
        out.append(("no last block, q-plication q=%d" % q, "last", c))
    c = inst("q2", 3)
    c["last"][1] = c["last"][0]
    out.append(("G2' replaced by G1', q^2-plication q=3", "last", c))
    c = inst("q", 4)
    for row in c["last"][0]:
        row[3] = row[0]
    out.append(("last column 3 = column 0 (a non-consecutive 3-set fails), q=4", "last", c))
    for q in (4, 5):
        c = inst("q", q)
        for row in c["dca"]:
            row[2] = row[0]
        out.append(("D column 2 = column 0 (a non-adjacent pair fails), q=%d" % q, "dca", c))
    c = inst("q2q1", 3)
    out.append(("k + 1", "k", c))
    return out


# ---------------------------------------------------------------------------------------------
# mutants

def disabled(c):
    return []


def _cphf_same_functional(c):          # dependent in both only for the same functional (too weak)
    F, q = c["F"], c["q"]
    hs = [h for h in itertools.product(range(q), repeat=3) if cc.smx_normal(F, h) == h]
    G1, G2 = cc.smx_columns(c)
    for h in hs:
        z1 = {j for j, g in enumerate(G1) if F.add[F.add[F.mul[h[0]][g[0]]][F.mul[h[1]][g[1]]]][F.mul[h[2]][g[2]]] == 0}
        z2 = {j for j, g in enumerate(G2) if F.add[F.add[F.mul[h[0]][g[0]]][F.mul[h[1]][g[1]]]][F.mul[h[2]][g[2]]] == 0}
        if len(z1 & z2) >= 3:
            return ["bad"]
    return []


def _dca_adjacent(c):                  # only pairs of adjacent columns (too weak)
    F, q, D, x = c["F"], c["q"], c["D"], c["x"]
    neg = [F.add[a].index(0) for a in range(q)]
    for l in range(x - 1):
        if len({F.add[r[l + 1]][neg[r[l]]] for r in D}) != q:
            return ["bad"]
    return []


def _last_without_ED(c):               # the last block alone must cover (too strict)
    _, C = cc.smx_last(c)
    q, x = c["q"], c["x"]
    if x < 3:
        return []
    for a, b, d in itertools.combinations(range(x), 3):
        if len({(r[a], r[b], r[d]) for r in C}) != q ** 3:
            return ["bad"]
    return []


def _last_consecutive(c):              # only the 3-sets of consecutive columns (too weak)
    ED, C = cc.smx_last(c)
    q, x = c["q"], c["x"]
    E = list(ED) + C
    for a in range(x - 2):
        if len({(r[a], r[a + 1], r[a + 2]) for r in E}) != q ** 3:
            return ["bad"]
    return []


def _points_g1_only(c):                # (H1) for G1 only (too weak)
    saved = c.get("G2c")
    G1, G2 = cc.smx_columns(c)
    c["G2c"] = G1
    try:
        return cc.check_smx_points(c)
    finally:
        c["G2c"] = G2 if saved is None else saved


IMPLIED = {"field": "q prime or the default modulus here; part 1 plants a reducible modulus",
           "P": "Corollary 5.1.9 holds for every order of the points, so P never fails on a certificate; "
                "part 3 breaks the recipe instead",
           "symbols": "every array has symbol 0 (A(G1) has the zero row)",
           "alphabet": "the entries are field labels"}


def check_lists():
    return [cc.SMX_CHECKS, cc.POST_CHECKS, cc.KIND_POST_CHECKS]


def all_check_names():
    names = set()
    for lst in check_lists():
        names |= {n for n, _ in lst}
    return sorted(names)


def install(repl):
    saved = [list(lst) for lst in check_lists()]
    for lst in check_lists():
        lst[:] = [(n, repl.get(n, f)) for n, f in lst]
    return saved


def restore(saved):
    for lst, old in zip(check_lists(), saved):
        lst[:] = old


# ---------------------------------------------------------------------------------------------

def part_scripts(work, cav, errors, quick):
    print("part 1: the script and the checker")
    for thm, q in (QUICK_SCRIPT_CASES if quick else SCRIPT_CASES):
        t0 = time.time()
        arr = os.path.join(work, "s_%s_%d.txt" % (thm, q))
        cert = os.path.join(work, "s_%s_%d.json" % (thm, q))
        with open(arr, "wb") as fo:
            p = subprocess.run([sys.executable, SCRIPT, thm, str(q), "--certificate", cert], stdout=fo,
                               stderr=subprocess.PIPE)
        if p.returncode:
            if b"|Z| = q - 1" in p.stderr:
                print("  %s q=%d: no primitive cubic has |Z| = q - 1 (Theorem 5.2.13 cannot be applied)" % (thm, q))
                continue
            errors.append("script %s %d failed: %s" % (thm, q, p.stderr.decode()[-300:]))
            continue
        wpath = arr + ".rebuilt"
        ok, got, sha = run_checker(cert, wpath)
        same = ok and open(wpath, "rb").read() == open(arr, "rb").read()
        cav_ok = subprocess.run([cav, arr, "3", str(q), "2"], stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL).returncode == 0
        if q == 2 and thm in ("q2", "q2even"):
            # at q = 2, A(G2') repeats rows of E_D or of A(G1') that the thesis keeps (3 for 5.2.11, 6 for 5.2.12); the
            # checker drops them, so its array is shorter than the script's (and than the theorem's N): it must still
            # pass every hypothesis and cover
            n_script = sum(1 for _ in open(arr, "rb"))
            n_check = sum(1 for _ in open(wpath, "rb")) if os.path.exists(wpath) else -1
            w_ok = n_check > 0 and subprocess.run([cav, wpath, "3", "2", "2"], stdout=subprocess.DEVNULL,
                                                  stderr=subprocess.DEVNULL).returncode == 0
            good = got == {"N", "sha256"} and 0 < n_check < n_script and w_ok and cav_ok
            print("  %-6s q=%-2d: the checker drops %d repeated rows the thesis keeps (N %d, not %d), every hypothesis "
                  "holds, ca_verify %s on both arrays" % (thm, q, n_script - n_check, n_check, n_script,
                                                          "VERIFIED" if w_ok and cav_ok else "FAILED"))
            if not good:
                errors.append("part 1 %s %d: %s, N %d against %d" % (thm, q, sorted(got), n_check, n_script))
            for f in (arr, wpath):
                if os.path.exists(f):
                    os.remove(f)
            continue
        print("  %-6s q=%-2d: checker %s, rebuild %s the script's array, ca_verify %s (%.1f s)"
              % (thm, q, "VALID" if ok else "REJECTED %s" % sorted(got), "equals" if same else "DIFFERS FROM",
                 "VERIFIED" if cav_ok else "FAILED", time.time() - t0))
        if not (ok and same and cav_ok):
            errors.append("part 1 %s %d: ok %s same %s ca_verify %s" % (thm, q, ok, same, cav_ok))
        for f in (arr, wpath):
            if os.path.exists(f):
                os.remove(f)
    # a reducible modulus
    cert = json.load(open(os.path.join(work, "s_q2even_4.json" if not quick else "s_q2even_4.json")))
    cert["field"]["modulus"] = [0, 0, 1]
    bad = os.path.join(work, "bad_field.json")
    json.dump(cert, open(bad, "w"))
    ok, got, _ = run_checker(bad)
    print("  GF(4) with the reducible modulus y^2: %s" % ("rejected by field" if "field" in got else "NOT REJECTED"))
    if ok or "field" not in got:
        errors.append("part 1: a reducible modulus is not reported by field (%s)" % sorted(got))
    print("  published arrays rebuilt by the script:")
    for thm, q, opts, sha, what in REFERENCE:
        if quick and q > 9:
            continue
        got = script_sha(thm, q, opts)
        print("    %-6s q=%-2d %s: %s" % (thm, q, what, "same sha256" if got == sha else "DIFFERENT (%s)" % got[:16]))
        if got != sha:
            errors.append("reference %s %d %s: sha256 %s, expected %s" % (thm, q, what, got, sha))


def part_real(work, errors):
    print("part 3: the real certificates")
    if not os.path.isdir(REAL_DIR):
        errors.append("part 3: %s is missing" % REAL_DIR)
        return
    names = sorted(f for f in os.listdir(REAL_DIR) if f.endswith(".cert.json"))
    for name in names:
        t0 = time.time()
        ok, got, sha = run_checker(os.path.join(REAL_DIR, name))
        exp = json.load(open(os.path.join(REAL_DIR, name)))["expected"]["array_sha256"]
        print("  %-32s %s (%.0f s)" % (name, "VALID, sha256 as recorded" if ok and sha == exp else "FAILED %s" % sorted(got),
                                       time.time() - t0))
        if not ok or sha != exp:
            errors.append("part 3: %s %s" % (name, sorted(got)))
    small = [n for n in names if n.endswith("_7.cert.json")]
    for name in small:
        base = json.load(open(os.path.join(REAL_DIR, name)))
        F = field_of(base)
        nonprim = next(f for f in ([c0, c1, c2, 1] for c0, c1, c2 in itertools.product(range(F.q), repeat=3))
                       if not smx.is_primitive(F, f))
        faults = [("cubic", lambda c: c.__setitem__("cubic", nonprim), {"cubic"}),
                  ("a D entry", lambda c: c["dca"][3].__setitem__(5, (c["dca"][3][5] + 1) % 7), {"dca"}),
                  ("G2' replaced by G1'", lambda c: c["last"].__setitem__(1, c["last"][0]), {"last"}),
                  ("N + 1", lambda c: c["expected"].__setitem__("N", c["expected"]["N"] + 1), {"N"}),
                  ("no last block", lambda c: c.__setitem__("last", []), {"last"})]
        for label, fn, want in faults:
            cert = json.loads(json.dumps(base))
            fn(cert)
            path = os.path.join(work, "real_fault.json")
            json.dump(cert, open(path, "w"))
            ok, got, _ = run_checker(path)
            hit = not ok and want <= got
            print("  %s, planted %s: %s" % (name, label, "rejected by %s" % sorted(got) if hit else "NOT REJECTED as intended %s" % sorted(got)))
            if not hit:
                errors.append("part 3: %s with %s: %s" % (name, label, sorted(got)))
    # a broken recipe for P is caught by the P check
    saved = cc.smx_P

    def broken_P(c):
        P = saved(c)
        return [[r[1]] + r[1:] for r in P]
    cc.smx_P = broken_P
    try:
        ok, got, _ = run_checker(os.path.join(REAL_DIR, small[0]))
    finally:
        cc.smx_P = saved
    print("  %s with P's column 0 replaced by column 1 in the checker: %s" % (small[0], "rejected by P" if "P" in got else "NOT REJECTED"))
    if ok or "P" not in got:
        errors.append("part 3: a broken P recipe is not caught (%s)" % sorted(got))


def main():
    args = sys.argv[1:]
    ncases = int(args[args.index("--cases") + 1]) if "--cases" in args else 60
    seed = int(args[args.index("--seed") + 1]) if "--seed" in args else 20261110
    quick = "--quick" in args
    rng = random.Random(seed)
    t0 = time.time()
    work = tempfile.mkdtemp(prefix="casmx-")
    cav = os.path.join(work, "ca_verify")
    subprocess.check_call(["cc", "-O2", "-pthread", "-o", cav, os.path.join(ROOT, "ca_verify.c")])
    errors = []
    part_scripts(work, cav, errors, quick)

    print("part 2: random certificates, seed %d" % seed)
    cases = []
    for idx in range(ncases):
        q = rng.choice((2, 3, 3, 4, 5))
        label, cert = instance_case(rng, q) if idx % 2 == 0 else random_case(rng, q)
        hyp, X = oracle(cert)
        cert["expected"] = {"N": int(X.shape[0]), "k": int(X.shape[1]), "array_sha256": canon_sha(X)}
        fault = None
        if idx % 3 == 1:
            fault = plant(rng, cert, rng.choice(FAULTS))
        hyp, fails, X = evaluate(cert)
        path = os.path.join(work, "case%04d.json" % idx)
        json.dump(cert, open(path, "w"))
        cases.append({"label": label, "fault": fault, "path": path, "hyp": hyp, "fails": fails, "X": X, "q": q})
    for label, fault, cert in targeted():
        idx += 1
        hyp, X = oracle(cert)
        cert["expected"] = {"N": int(X.shape[0]), "k": int(X.shape[1]) + (fault == "k"), "array_sha256": canon_sha(X)}
        hyp, fails, X = evaluate(cert)
        path = os.path.join(work, "case%04d.json" % idx)
        json.dump(cert, open(path, "w"))
        q = cert["v"]
        cases.append({"label": "targeted", "fault": fault, "path": path, "hyp": hyp, "fails": fails, "X": X, "q": q,
                      "what": label})
        if fails != {fault}:
            errors.append("targeted case %s: the oracle finds %s, not only %s" % (label, sorted(fails), fault))
    stats, theorem, agree = {}, [0, 0], [0, 0]
    for cs in cases:
        key = (cs["label"], cs["fault"] or "none")
        st = stats.setdefault(key, [0, 0, 0])
        st[0] += 1
        nerr = len(errors)
        wpath = cs["path"] + ".out"
        ok, got, csha = run_checker(cs["path"], wpath)
        apath = cs["path"] + ".ind"
        with open(apath, "wb") as f:
            write_rows(cs["X"].astype(np.uint8), f)
        cover = subprocess.run([cav, apath, "3", str(cs["q"]), "1"], stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL).returncode == 0
        os.remove(apath)
        st[1] += ok
        st[2] += cover
        fails = cs["fails"]
        if ok != (not fails):
            errors.append("A1 %s %s: checker ok=%s %s, oracle %s" % (cs["path"], key, ok, sorted(got), sorted(fails)))
        for name, val in cs["hyp"].items():
            agree[0] += 1
            if (name in got) != (not val):
                agree[1] += 1
                errors.append("A2 %s %s: check %s says %s, oracle %s" % (cs["path"], key, name, name not in got, val))
        if cs["fault"] and cs["fault"] in fails and cs["fault"] not in got:
            errors.append("A2 %s %s: planted fault not reported (%s)" % (cs["path"], key, sorted(got)))
        if ok:
            wsha = hashlib.sha256(open(wpath, "rb").read()).hexdigest()
            if not cover or csha != canon_sha(cs["X"]) or wsha != csha:
                errors.append("A3 %s %s: accepted, covering=%s" % (cs["path"], key, cover))
        if os.path.exists(wpath):
            os.remove(wpath)
        hyp_ok = all(cs["hyp"].values())
        if hyp_ok:
            theorem[0] += 1
            if not cover:
                theorem[1] += 1
                errors.append("A4 %s %s: hypotheses hold but the array is not covering" % (cs["path"], key))
        cs["cover"] = cover
        cs["baseline_ok"] = len(errors) == nerr
    print("  %d certificates, %.0f s" % (len(cases), time.time() - t0))
    print("  %-8s %-8s %6s %8s %8s" % ("case", "fault", "certs", "accepted", "covering"))
    for (label, fault), st in sorted(stats.items()):
        print("  %-8s %-8s %6d %8d %8d" % (label, fault, st[0], st[1], st[2]))
    hfail = {}
    for cs in cases:
        for f in cs["fails"]:
            hfail[f] = hfail.get(f, 0) + 1
    print("  hypotheses failing (oracle), cases: %s" % ", ".join("%s %d" % kv for kv in sorted(hfail.items())))
    print("  theorem: %d certificates satisfy every hypothesis; %d of their arrays not covering" % tuple(theorem))
    print("  checks compared with the oracle: %d, disagreements %d" % tuple(agree))

    mutants = [("disable:" + n, {n: disabled}) for n in all_check_names()] + [
        ("disable: cubic and points", {"cubic": disabled, "points": disabled}),
        ("disable: cubic and cphf", {"cubic": disabled, "cphf": disabled}),
        ("cphf: the same functional in G1 and G2 only", {"cphf": _cphf_same_functional, "cubic": disabled}),
        ("points: G1 only", {"points": _points_g1_only, "cubic": disabled}),
        ("dca: adjacent columns only", {"dca": _dca_adjacent}),
        ("last: C' alone, without E_D", {"last": _last_without_ED}),
        ("last: consecutive 3-sets only", {"last": _last_consecutive})]
    survivors = []
    print("mutation testing (%d mutants):" % len(mutants))
    for mname, repl in mutants:
        saved = install(repl)
        killed = unsound = 0
        try:
            for cs in cases:
                if not cs["baseline_ok"]:
                    continue
                ok, got, csha = run_checker(cs["path"])
                want = cs["fails"] - {n for n in repl if repl[n] is disabled}
                if ok != (not cs["fails"]) or any((n in got) != (n in want) for n in cs["hyp"] if n not in repl):
                    killed += 1
                if ok and not cs["cover"]:
                    unsound += 1
        finally:
            restore(saved)
        single = len(repl) == 1 and list(repl.values())[0] is disabled
        name = list(repl)[0]
        status = "KILLED" if killed else ("not killable here (%s)" % IMPLIED[name] if single and name in IMPLIED
                                          else "SURVIVED")
        if status == "SURVIVED" and single and name in ("points", "cphf"):
            status = "not killable alone (a primitive cubic implies it; see the mutant with cubic)"
        if status == "SURVIVED":
            survivors.append(mname)
        print("  %-46s %-34s by %3d cases; accepts a non-covering array: %d" % (mname, status, killed, unsound))
    print("mutants surviving: %d %s" % (len(survivors), survivors))
    if survivors:
        errors.append("%d mutant(s) survived: %s" % (len(survivors), survivors))
    if "--skip-real" not in args:
        part_real(work, errors)
    shutil.rmtree(work, ignore_errors=True)
    print("total %.0f s" % (time.time() - t0))
    if errors:
        print("ERRORS (%d):" % len(errors))
        for e in errors[:40]:
            print("  " + e)
        return 1
    print("ALL TESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
