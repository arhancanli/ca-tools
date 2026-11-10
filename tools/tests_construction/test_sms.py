#!/usr/bin/env python3
"""Tests of the constructions sms51-1 and sms65-1 of tools/construction_cert.py (Shokri, Moura and
Stevens, arXiv:2510.13122v3, Theorems 5.1 and 6.2; tools/CONSTRUCTION_CERT.md).

Part 1, the scripts. For q = 3, 5, 7, 9 (9 = 3^2, a prime power) tools/sms_theorem51.py and
sms_theorem62.py write their array and its certificate (--certificate); the checker accepts the
certificate, and the array it writes with --write is byte for byte the script's. ca_verify checks
every array exactly (every 4-set of columns).

Part 2, random certificates over prime q = 3, 5, 7 with an independent oracle. The certificates
have random multipliers, p, quartics (primitive or not), ingredients (the orthogoval recipe with
random cubics and points, or an inline array ingredient, sometimes with an entry changed) and
planted faults. Independently of the checker, this file computes alpha^e by its own polynomial
arithmetic (powers by squaring), decides every hypothesis by its definition with integer
determinants mod q (every 4-set and 3-set, no hyperplanes, no shift), rebuilds the array with numpy
(U @ G mod q) and checks it with ca_verify.
  A1 the checker accepts exactly when the oracle finds every hypothesis true and the expected
     N, k and sha256 are the rebuilt array's
  A2 each check agrees with the oracle's verdict on its hypothesis (when the quartic is primitive,
     and for the ingredient checks when the cubic is primitive); a planted fault is reported by the
     check it targets
  A3 every accepted certificate gives a covering array (ca_verify) with the oracle's sha256, and the
     file the checker writes has that sha256
  A4 (the theorems) every case whose hypotheses hold gives a covering array
Then mutation testing: each check is disabled in turn, and three boundary mutants are applied
(actm also over 4-sets with a repeated x, too strict; caps for H2 only; orthogoval without the
3-sets that repeat a point). A mutant is killed when A1 or A2 fails on
some case. hyperplanes and lines cannot fail when quartic and cubic pass (Singer's theorem); they are
kept because the checker's proof uses them and not that theorem, and they are reported, not counted
as survivors.

Part 3, the real certificates of table/constructions/smolen-2026-11-sms-certificates/ (or of the
submission folder before they are entered), when present (--skip-real to leave out): each passes and rebuilds the sha256 in its expected, and planted faults on
the q = 13 and 17 certificates are rejected by the intended check.

Usage: test_sms.py [--cases N] [--seed S] [--skip-real] [--quick (part 1 for q = 3, 5 only)]   (exit 1 on any violation or surviving mutant)
"""
import copy
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
sys.path.insert(0, os.path.join(ROOT, "tools"))
import construction_cert as cc  # noqa: E402

# the real certificates: in the submission folder, and in table/constructions/ once they are entered
REALS = [os.path.join(ROOT, "table", "constructions", "smolen-2026-11-sms-certificates"),
         os.path.join(ROOT, "submissions", "smolen-2026-11-sms-certificates")]
REAL = next((d for d in REALS if os.path.isdir(d)), REALS[-1])


# ---------------------------------------------------------------------------------------------
# the oracle (prime q only): integer polynomials mod (f, q), determinants mod q

def pmul(a, b, f, q):
    m = len(f) - 1
    r = [0] * (2 * m - 1)
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            r[i + j] += x * y
    for d in range(2 * m - 2, m - 1, -1):
        c = r[d] % q
        r[d] = 0
        for k in range(m):
            r[d - m + k] -= c * f[k]
    return tuple(x % q for x in r[:m])


def ppow(e, f, q):
    m = len(f) - 1
    res, base = tuple([1] + [0] * (m - 1)), tuple([0, 1] + [0] * (m - 2))
    while e:
        if e & 1:
            res = pmul(res, base, f, q)
        base = pmul(base, base, f, q)
        e >>= 1
    return res


def primes_of(n):
    out, d = [], 2
    while d * d <= n:
        if n % d == 0:
            out.append(d)
            while n % d == 0:
                n //= d
        d += 1
    return out + ([n] if n > 1 else [])


def primitive(f, q):
    m = len(f) - 1
    one = tuple([1] + [0] * (m - 1))
    order = q ** m - 1
    return ppow(order, f, q) == one and all(ppow(order // r, f, q) != one for r in primes_of(order))


def det_mod(M, q):
    """determinants mod q of a batch of square integer matrices (shape S x r x r, r = 3 or 4)"""
    M = M.astype(np.int64)
    if M.shape[1] == 3:
        d = (M[:, 0, 0] * (M[:, 1, 1] * M[:, 2, 2] - M[:, 1, 2] * M[:, 2, 1])
             - M[:, 0, 1] * (M[:, 1, 0] * M[:, 2, 2] - M[:, 1, 2] * M[:, 2, 0])
             + M[:, 0, 2] * (M[:, 1, 0] * M[:, 2, 1] - M[:, 1, 1] * M[:, 2, 0]))
        return d % q
    d = np.zeros(M.shape[0], dtype=np.int64)
    for j in range(4):
        minor = np.delete(np.delete(M, 0, axis=1), j, axis=2)
        d += (-1) ** j * M[:, 0, j] * det_mod(minor, q)
    return d % q


def indep3_in4(V, q):
    """V: S x 4 x 3 (3 column vectors in F_q^4): independent iff some 3 x 3 minor is nonzero"""
    nz = np.zeros(V.shape[0], dtype=bool)
    for drop in range(4):
        nz |= det_mod(np.delete(V, drop, axis=1), q) != 0
    return nz


class Case:
    def __init__(self, kind, q):
        self.kind, self.q = kind, q
        self.fault = None
        self.cert = None


def vec(f, q, e):
    return np.array(ppow(e, f, q), dtype=np.int64)


def oracle(c, build=True):
    """every hypothesis by its definition, the rebuilt array and its sha256; returns (hyp dict, rows)"""
    q, cert = c.q, c.cert
    f = cert["quartic"]
    half, K = (q * q + 1) // 2, q * q + 1
    l1, l2, l3 = cert.get("multipliers", [1, 2, 4])
    nn = q ** 4 - 1
    hyp = {"quartic": primitive(f, q)}
    G = {j: np.stack([vec(f, q, (l * (q + 1) * col) % nn) for col in range(K)], axis=1)
         for j, l in ((1, l1), (2, l2), (3, l3))}
    # actm: every 4-set of the full ovoid with distinct x
    sets = [s for s in itertools.combinations(range(K), 4) if len({x % half for x in s}) == 4]
    S = np.array(sets, dtype=np.int64)
    dep = [det_mod(np.transpose(G[j][:, S], (1, 0, 2)), q) == 0 for j in (1, 2, 3)]
    allbad = dep[0] & dep[1] & dep[2]
    hyp["actm"] = not bool(np.any(allbad))
    c.actm_p0 = not bool(np.any(allbad & np.all(S < half, axis=1)))
    if c.kind == "sms65-1":
        ok = True
        T = np.array(list(itertools.combinations(range(half), 3)), dtype=np.int64)
        for j in (2, 3):
            H = G[j][:, :half]
            ok &= bool(np.all(indep3_in4(np.transpose(H[:, T], (1, 0, 2)), q)))
        hyp["caps"] = ok
        c.caps_h2 = bool(np.all(indep3_in4(np.transpose(G[2][:, :half][:, T], (1, 0, 2)), q)))
        P = np.array([(x, x + half, y, y + half) for x, y in itertools.combinations(range(half), 2)], dtype=np.int64)
        hyp["pairs"] = bool(np.all(det_mod(np.transpose(G[1][:, P], (1, 0, 2)), q) != 0))
    if not build:
        return hyp, None
    # the array
    U = np.array(list(itertools.product(range(q), repeat=4)), dtype=np.int64)
    if c.kind == "sms51-1":
        p = [int(ch) for ch in cert["p"]]
        cols = [i + p[i] * half for i in range(half)]
        blocks = [(U @ G[j][:, cols]) % q for j in (1, 2, 3)]
        rows = np.vstack([blocks[0], blocks[1][1:], blocks[2][1:]])
    else:
        R = ingredient_oracle(c, hyp)
        c.incomplete = R is None          # the ingredient cannot be built: no array
        H2, H4 = G[2][:, :half], G[3][:, :half]
        parts = [(U @ G[1]) % q, np.hstack([(U @ H2) % q] * 2), np.hstack([(U @ H4) % q, (U @ H4 + 1) % q])]
        if R is not None:
            for r in range(1, q - 1):
                parts.append(np.hstack([R, (R + r + 1) % q]))
        rows = np.vstack(parts)
    return hyp, rows


def ingredient_oracle(c, hyp):
    q, cert = c.q, c.cert
    half = (q * q + 1) // 2
    ing = cert["ingredient"]
    if "rows" in ing:
        R = np.array(ing["rows"], dtype=np.int64)
        okshape = R.ndim == 2 and R.shape[1] == half and R.min() >= 0 and R.max() < q
        hyp["shape"] = okshape
        hyp["ingredient_ca"] = covers3(R, q) if okshape else None
        return R if okshape else None
    og = ing["orthogoval"]
    g = og["cubic"]
    hyp["cubic"] = primitive(g, q)
    n3 = q ** 3 - 1
    v1 = [ppow(j % n3, g, q) for j in og["points"]]
    v2 = [ppow((-j) % n3, g, q) for j in og["points"]]
    hyp["points"] = all(a[0] and b[0] for a, b in zip(v1, v2))
    if not hyp["points"]:
        hyp["orthogoval"] = None
        return None
    sc = lambda v: [(x * pow(v[0], q - 2, q)) % q for x in v]
    G1 = np.array([sc(v) for v in v1], dtype=np.int64).T
    G2 = np.array([sc(v) for v in v2], dtype=np.int64).T
    T = np.array(list(itertools.combinations(range(half), 3)), dtype=np.int64)
    d1 = det_mod(np.transpose(G1[:, T], (1, 0, 2)), q) == 0
    d2 = det_mod(np.transpose(G2[:, T], (1, 0, 2)), q) == 0
    hyp["orthogoval"] = not bool(np.any(d1 & d2))
    U3 = np.array(list(itertools.product(range(q), repeat=3)), dtype=np.int64)
    A1, A2 = (U3 @ G1) % q, (U3 @ G2) % q
    keep = [i for i in range(q ** 3) if i % (q * q) != 0]
    return np.vstack([A1, A2[keep]])


def covers3(R, q):
    k = R.shape[1]
    for cols in itertools.combinations(range(k), 3):
        if len({tuple(r) for r in R[:, cols].tolist()}) != q ** 3:
            return False
    return True


def canon(rows):
    return "".join(" ".join(map(str, r)) + "\n" for r in rows.tolist())


# ---------------------------------------------------------------------------------------------
# random certificates

def first_primitive(m, q):
    for co in itertools.product(range(q), repeat=m):
        if co[0] and primitive(list(co) + [1], q):
            return list(co) + [1]


def random_primitive(rng, m, q):
    while True:
        f = [rng.randrange(1, q)] + [rng.randrange(q) for _ in range(m - 1)] + [1]
        if primitive(f, q):
            return f


def even_mult(rng, n):
    return rng.randrange(1, (n - 1) // 2 + 1) * 2


def build_case(rng, kind, q):
    c = Case(kind, q)
    half = (q * q + 1) // 2
    n = (q ** 4 - 1) // (q - 1)
    f = random_primitive(rng, 4, q) if rng.random() < 0.8 else \
        [rng.randrange(1, q)] + [rng.randrange(q) for _ in range(3)] + [1]
    cert = {"format": "construction-cert-1", "construction": kind, "t": 4, "v": q,
            "field": {"q": q, "p": q, "m": 1}, "quartic": f}
    r = rng.random()
    if r < (0.45 if kind == "sms51-1" else 0.6):
        pass                                            # default multipliers
    elif kind == "sms51-1":
        cert["multipliers"] = [rng.randrange(1, n) for _ in range(3)]
    else:
        cert["multipliers"] = [rng.randrange(1, n), even_mult(rng, n), even_mult(rng, n)]
    if kind == "sms51-1":
        cert["p"] = "".join(rng.choice("01") for _ in range(half)) if rng.random() < 0.7 else "0" * half
    else:
        g = random_primitive(rng, 3, q) if rng.random() < 0.85 else \
            [rng.randrange(1, q)] + [rng.randrange(q) for _ in range(2)] + [1]
        n3 = q ** 3 - 1
        good = [j for j in range(q * q + q + 1) if ppow(j % n3, g, q)[0] and ppow((-j) % n3, g, q)[0]]
        u = rng.random()
        if u < 0.5 and len(good) >= half:
            pts = good[:half]
        elif u < 0.8 and len(good) >= half:
            pts = sorted(rng.sample(good, half))
        else:
            pts = [rng.randrange(n3) for _ in range(half)]
        cert["ingredient"] = {"orthogoval": {"cubic": g, "points": pts}}
        if rng.random() < 0.15 and q <= 5:
            c.cert = cert
            hyp = {}
            R = ingredient_oracle(c, hyp)
            if R is not None:
                R = R.tolist()
                if rng.random() < 0.5:
                    i, j = rng.randrange(len(R)), rng.randrange(half)
                    R[i][j] = (R[i][j] + 1) % q
                cert["ingredient"] = {"rows": R}
    c.cert = cert
    return c


FAULTS = {"sms51-1": ["N", "k", "sha256", "quartic"],
          "sms65-1": ["N", "k", "sha256", "quartic", "cubic", "points", "shape"]}


def plant(rng, c, fault):
    cert = c.cert
    c.fault = fault
    if fault == "N":
        cert["expected"]["N"] += rng.choice([-1, 1])
    elif fault == "k":
        cert["expected"]["k"] += 1
    elif fault == "sha256":
        s = cert["expected"]["array_sha256"]
        cert["expected"]["array_sha256"] = s[:-1] + ("0" if s[-1] != "0" else "1")
    elif fault == "quartic":        # a quartic with a root (x - a): never primitive
        q = c.q
        a = rng.randrange(1, q)
        g = random_primitive(rng, 3, q)    # (x - a) g(x)
        f = [0] * 5
        for i, x in enumerate(g):
            f[i + 1] += x
            f[i] -= a * x
        cert["quartic"] = [x % q for x in f]
    elif fault == "cubic":
        if "orthogoval" not in cert["ingredient"]:
            c.fault = None
            return
        q = c.q
        a = rng.randrange(1, q)
        b = [rng.randrange(1, q), rng.randrange(q), 1]   # (x - a) (x^2 + b1 x + b0)
        f = [0] * 4
        for i, x in enumerate(b):
            f[i + 1] += x
            f[i] -= a * x
        cert["ingredient"]["orthogoval"]["cubic"] = [x % q for x in f]
    elif fault == "shape":
        ing = cert["ingredient"]
        if "rows" not in ing:
            c.fault = None
            return
        ing["rows"] = [r[:-1] for r in ing["rows"]]
    elif fault == "points":
        og = cert["ingredient"].get("orthogoval")
        if not og:
            c.fault = None
            return
        g, q = og["cubic"], c.q
        n3 = q ** 3 - 1
        zero = [j for j in range(n3) if ppow(j, g, q)[0] == 0]
        og["points"][rng.randrange(len(og["points"]))] = rng.choice(zero)


def targeted(rng):
    """cases in which one hypothesis fails alone (so that disabling its check is seen), found with the
    oracle: multipliers for actm, caps, pairs and caps of H4 only; a repeated point (orthogoval: the
    planes beta^j and beta^-j are orthogoval on all points, so only a repeated point or a cubic that is
    not primitive makes it fail); a point with first coordinate 0 (points); an inline ingredient
    with one entry changed so that it stops covering (ingredient_ca) or one column short (shape)"""
    out = []
    want = {"actm": None, "caps": None, "pairs": None, "caps_h4": None}
    for q in (5, 3):
        n = (q ** 4 - 1) // (q - 1)
        f = first_primitive(4, q)
        tries = 0
        while any(v is None for v in want.values()) and tries < 600:
            tries += 1
            kind = "sms65-1"
            mult = [rng.randrange(1, n), even_mult(rng, n), even_mult(rng, n)]
            if rng.random() < 0.5:
                mult[0] = 1
            c = Case(kind, q)
            g = first_primitive(3, q)
            n3 = q ** 3 - 1
            good = [j for j in range(q * q + q + 1) if ppow(j % n3, g, q)[0] and ppow((-j) % n3, g, q)[0]]
            c.cert = {"format": "construction-cert-1", "construction": kind, "t": 4, "v": q,
                      "field": {"q": q, "p": q, "m": 1}, "quartic": f, "multipliers": mult,
                      "ingredient": {"orthogoval": {"cubic": g, "points": good[:(q * q + 1) // 2]}}}
            hyp, _ = oracle(c, build=False)
            bad = {k for k in ("actm", "caps", "pairs") if not hyp[k]}
            if len(bad) == 1:
                b = bad.pop()
                if want[b] is None:
                    want[b] = c
                if b == "caps" and c.caps_h2 and want["caps_h4"] is None:
                    want["caps_h4"] = c
    for k, c in want.items():
        if c is not None:
            c.label = "only " + k
            out.append(c)
    q = 7
    f, g = first_primitive(4, q), first_primitive(3, q)
    n3 = q ** 3 - 1
    half = (q * q + 1) // 2
    good = [j for j in range(q * q + q + 1) if ppow(j % n3, g, q)[0] and ppow((-j) % n3, g, q)[0]]
    zero = [j for j in range(n3) if ppow(j, g, q)[0] == 0]
    base = {"format": "construction-cert-1", "construction": "sms65-1", "t": 4, "v": q,
            "field": {"q": q, "p": q, "m": 1}, "quartic": f,
            "ingredient": {"orthogoval": {"cubic": g, "points": good[:half]}}}
    c = Case("sms65-1", q)
    c.cert = copy.deepcopy(base)
    c.cert["ingredient"]["orthogoval"]["points"][4] = c.cert["ingredient"]["orthogoval"]["points"][3]
    c.label = "point repeated"
    out.append(c)
    c = Case("sms65-1", q)
    c.cert = copy.deepcopy(base)
    c.cert["ingredient"]["orthogoval"]["points"][2] = zero[0]
    c.fault = c.label = "points"
    out.append(c)
    c0 = Case("sms65-1", q)
    c0.cert = copy.deepcopy(base)
    R = ingredient_oracle(c0, {}).tolist()
    while True:
        R2 = [list(r) for r in R]
        i, j = rng.randrange(len(R2)), rng.randrange(half)
        R2[i][j] = (R2[i][j] + 1) % q
        if not covers3(np.array(R2), q):
            break
    for label, rows, fault in (("ingredient broken", R2, None), ("ingredient short", [r[:-1] for r in R], "shape")):
        c = Case("sms65-1", q)
        c.cert = copy.deepcopy(base)
        c.cert["ingredient"] = {"rows": rows}
        c.label, c.fault = label, fault
        out.append(c)
    return out


def evaluate(c):
    """the oracle's set of failed hypotheses (names of the checker), and the rebuilt rows"""
    cert = c.cert
    hyp, rows = oracle(c)
    fails = {k for k, v in hyp.items() if v is False}
    if not getattr(c, "incomplete", False):
        exp = cert["expected"]
        if exp["N"] != rows.shape[0]:
            fails.add("N")
        if exp["k"] != rows.shape[1]:
            fails.add("k")
        if exp["array_sha256"] != hashlib.sha256(canon(rows).encode()).hexdigest():
            fails.add("sha256")
    return hyp, fails, rows


# ---------------------------------------------------------------------------------------------
# mutants

def disabled(c):
    return []


def _actm_repeated_x(c):              # the 4-sets with a repeated x counted as well (too strict)
    q, half = c["q"], c["half"]
    K = q * q + 1
    M = [cc.sms_masks(c, l, range(K), lambda x: x) for l in c["mult"]]
    for t in itertools.combinations(range(1, K), 3):
        if all(Mj[0] & Mj[t[0]] & Mj[t[1]] & Mj[t[2]] for Mj in M):
            return ["bad %s" % ((0,) + t,)]
    return []


def _caps_h2_only(c):
    saved = c["mult"]
    c2 = dict(c)
    c2["mult"] = [saved[0], saved[1], saved[1]]
    return cc.check_caps(c2)


def _ortho_distinct_only(c):           # 3-sets with a repeated point (in plane 1) skipped
    cc.sms_ortho(c)
    q, n3, D3mask, full = c["q"], c["n3"], c["D3mask"], c["full3"]
    D3set = set(c["D3"])
    P1 = [j % n3 for j in c["points"]]
    M2 = [cc.rot(D3mask, (-j) % n3, n3, full) for j in c["points"]]
    for s in range(n3):
        Y = [i for i in range(len(P1)) if (P1[i] + s) % n3 in D3set]
        for a, b, d in itertools.combinations(Y, 3):
            if len({P1[a], P1[b], P1[d]}) == 3 and M2[a] & M2[b] & M2[d]:
                return ["bad"]
    return []


IMPLIED = {"hyperplanes": "implied by quartic", "lines": "implied by cubic",
           "field": "q prime here; part 1 plants a reducible modulus",
           "symbols": "every sms array has a zero row", "alphabet": "the entries are field labels",
           "ingredient_hash": "no file ingredient here; shared code, test_kinds.py"}


def check_lists():
    return [cc.SMS_CHECKS["sms51-1"], cc.SMS_CHECKS["sms65-1"], cc.SMS_ORTHO_CHECKS, cc.SMS_ARRAY_CHECKS,
            cc.POST_CHECKS, cc.KIND_POST_CHECKS, cc.TABLE_CHECKS]


def all_check_names():
    names = set()
    for lst in check_lists():
        names |= {n for n, _ in lst}
    return sorted(names - {"ingredient_table"})


def install(name, fn):
    saved = [list(lst) for lst in check_lists()]
    for lst in check_lists():
        lst[:] = [(n, fn if n == name else f) for n, f in lst]
    return saved


def restore(saved):
    for lst, old in zip(check_lists(), saved):
        lst[:] = old


def run_checker(path, write=None):
    try:
        r = cc.run(path, write)
        return r["ok"], {f[0] for f in r["failures"]}, r["sha256"]
    except cc.CertError as e:
        return False, {"malformed: %s" % e}, None


# ---------------------------------------------------------------------------------------------

def part_scripts(work, cav, errors, qs=(3, 5, 7, 9)):
    print("part 1: the scripts and the checker, q = %s" % ", ".join(map(str, qs)))
    for q in qs:
        for script, kind in (("sms_theorem51.py", "sms51-1"), ("sms_theorem62.py", "sms65-1")):
            arr = os.path.join(work, "s%s_%d.txt" % (kind, q))
            cert = os.path.join(work, "s%s_%d.json" % (kind, q))
            with open(arr, "wb") as f:
                subprocess.check_call([sys.executable, os.path.join(ROOT, "tools", script), str(q), "--certificate", cert],
                                      stdout=f, stderr=subprocess.DEVNULL)
            ok, got, sha = run_checker(cert, arr + ".chk")
            same = open(arr, "rb").read() == open(arr + ".chk", "rb").read()
            t0 = time.time()
            ver = subprocess.run([cav, arr, "4", str(q), "2"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                 universal_newlines=True)
            verified = ver.returncode == 0 and "VERIFIED" in ver.stdout
            print("  %s q=%d: checker %s, rebuild %s the script's array, ca_verify %s (%.0f s)"
                  % (kind, q, "accepts" if ok else "REJECTS %s" % sorted(got), "equals" if same else "DIFFERS from",
                     "VERIFIED" if verified else "NOT VERIFIED", time.time() - t0))
            if not (ok and same and verified):
                errors.append("part 1: %s q=%d ok=%s same=%s verified=%s" % (kind, q, ok, same, verified))
            for x in (arr, arr + ".chk"):
                os.remove(x)
            if q == 9:                      # a reducible modulus (y^2) is reported by the field check
                bad = json.load(open(cert))
                bad["field"]["modulus"] = [0, 0, 1]
                json.dump(bad, open(cert, "w"))
                ok, got, sha = run_checker(cert)
                print("  %s q=9 with the reducible modulus y^2: %s %s" % (kind, "accepted" if ok else "rejected by",
                                                                         sorted(got)))
                if ok or "field" not in got:
                    errors.append("part 1: reducible modulus not reported by field (%s)" % kind)


def part_real(work, errors):
    if not os.path.isdir(REAL):
        print("part 3: %s not present, skipped" % REAL)
        return
    print("part 3: the real certificates")
    certs = sorted(x for x in os.listdir(REAL) if x.endswith(".json"))
    for name in certs:
        path = os.path.join(REAL, name)
        t0 = time.time()
        ok, got, sha = run_checker(path)
        exp = json.load(open(path))["expected"]["array_sha256"]
        print("  %s: %s, sha256 %s (%.0f s)" % (name, "valid" if ok else "REJECTED %s" % sorted(got),
                                               "as expected" if sha == exp else "DIFFERS", time.time() - t0))
        if not ok or sha != exp:
            errors.append("part 3: %s" % name)
    plants = []
    for name in certs:
        cert = json.load(open(os.path.join(REAL, name)))
        if cert["v"] not in (13, 17):
            continue
        q = cert["v"]
        n = (q ** 4 - 1) // (q - 1)
        bad = copy.deepcopy(cert)
        bad["quartic"] = [0, 0, 0, 0, 1]
        plants.append((name, "quartic x^4", bad, "quartic"))
        bad = copy.deepcopy(cert)
        bad["multipliers"] = [1, 2, 2]
        plants.append((name, "multipliers [1, 2, 2]", bad, "actm"))
        bad = copy.deepcopy(cert)
        bad["expected"]["N"] += 1
        plants.append((name, "N + 1", bad, "N"))
        if cert["construction"] == "sms65-1":
            bad = copy.deepcopy(cert)
            bad["multipliers"] = [2, 2, 4]
            plants.append((name, "multipliers [2, 2, 4]", bad, "pairs"))
            bad = copy.deepcopy(cert)
            bad["multipliers"] = [1, 2 * (q * q + 1), 4]
            plants.append((name, "multipliers [1, 2(q^2+1), 4]", bad, "caps"))
            og = bad["ingredient"]["orthogoval"]
            bad = copy.deepcopy(cert)
            bad["ingredient"]["orthogoval"]["points"][3] = bad["ingredient"]["orthogoval"]["points"][2]
            plants.append((name, "a point repeated", bad, "orthogoval"))
            bad = copy.deepcopy(cert)
            bad["ingredient"]["orthogoval"]["cubic"] = [0, 0, 0, 1]
            plants.append((name, "cubic x^3", bad, "cubic"))
        else:
            bad = copy.deepcopy(cert)
            bad["p"] = bad["p"][:-1]
            plants.append((name, "p one bit short", bad, "malformed"))
        del n
    for name, label, bad, want in plants:
        path = os.path.join(work, "plant.json")
        json.dump(bad, open(path, "w"))
        ok, got, sha = run_checker(path)
        hit = (want == "malformed" and any(g.startswith("malformed") for g in got)) or want in got
        print("  %s, %s: %s %s" % (name, label, "accepted" if ok else "rejected by", "" if ok else sorted(got)))
        if ok or not hit:
            errors.append("part 3: %s %s not rejected by %s" % (name, label, want))


def main():
    args = sys.argv[1:]
    ncases = int(args[args.index("--cases") + 1]) if "--cases" in args else 60
    seed = int(args[args.index("--seed") + 1]) if "--seed" in args else 20261110
    rng = random.Random(seed)
    t0 = time.time()
    work = tempfile.mkdtemp(prefix="casms-")
    cav = os.path.join(work, "ca_verify")
    subprocess.check_call(["cc", "-O2", "-pthread", "-o", cav, os.path.join(ROOT, "ca_verify.c")])
    errors = []
    part_scripts(work, cav, errors, (3, 5) if "--quick" in args else (3, 5, 7, 9))

    print("part 2: random certificates, seed %d" % seed)
    cases = []
    for idx in range(ncases):
        kind = ("sms51-1", "sms65-1")[idx % 2]
        q = rng.choice((3, 5, 5, 7)) if kind == "sms51-1" else rng.choice((3, 5, 5, 7))
        c = build_case(rng, kind, q)
        hyp, rows = oracle(c)
        c.cert["expected"] = {"N": int(rows.shape[0]), "k": int(rows.shape[1]),
                              "array_sha256": hashlib.sha256(canon(rows).encode()).hexdigest()}
        if idx % 3:
            plant(rng, c, rng.choice(FAULTS[kind]))
        hyp, fails, rows = evaluate(c)
        path = os.path.join(work, "case%04d.json" % idx)
        json.dump(c.cert, open(path, "w"))
        cases.append((c, path, hyp, fails, rows))
    for c in targeted(rng):
        idx += 1
        fault, c.fault = c.fault, None
        hyp, rows = oracle(c)
        c.cert["expected"] = {"N": int(rows.shape[0]), "k": int(rows.shape[1]),
                              "array_sha256": hashlib.sha256(canon(rows).encode()).hexdigest()}
        c.fault = fault
        hyp, fails, rows = evaluate(c)
        path = os.path.join(work, "case%04d.json" % idx)
        json.dump(c.cert, open(path, "w"))
        cases.append((c, path, hyp, fails, rows))
    stats = {}
    theorem = [0, 0]
    agree = [0, 0]
    for c, path, hyp, fails, rows in cases:
        key = (c.kind, getattr(c, "label", None) or c.fault or "valid")
        st = stats.setdefault(key, [0, 0, 0])
        st[0] += 1
        nerr = len(errors)
        wpath = path + ".out"
        ok, got, csha = run_checker(path, wpath)
        apath = path + ".ind"
        with open(apath, "w") as f:
            f.write(canon(rows))
        cover = not getattr(c, "incomplete", False) and subprocess.run(
            [cav, apath, "4", str(c.q), "1"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
        os.remove(apath)
        if ok:
            st[1] += 1
        if cover:
            st[2] += 1
        if ok != (not fails):
            errors.append("A1 %s %s: checker ok=%s %s, oracle %s" % (path, key, ok, sorted(got), sorted(fails)))
        # A2: each check against the oracle's hypothesis
        for name, val in hyp.items():
            if val is None:
                continue
            if name in ("actm", "caps", "pairs") and not hyp["quartic"]:
                continue
            if name in ("orthogoval", "points") and not hyp.get("cubic", True):
                continue
            agree[0] += 1
            if (name in got) != (not val):
                agree[1] += 1
                errors.append("A2 %s %s: check %s says %s, oracle %s" % (path, key, name, name not in got, val))
        if c.fault and c.fault in fails and c.fault not in got:
            errors.append("A2 %s %s: planted fault not reported (%s)" % (path, key, sorted(got)))
        if ok:
            wsha = hashlib.sha256(open(wpath, "rb").read()).hexdigest()
            osha = hashlib.sha256(canon(rows).encode()).hexdigest()
            if not cover or csha != osha or wsha != csha:
                errors.append("A3 %s %s: accepted, covering=%s" % (path, key, cover))
        if os.path.exists(wpath):
            os.remove(wpath)
        if not fails:
            theorem[0] += 1
            if not cover:
                theorem[1] += 1
                errors.append("A4 %s %s: hypotheses hold but the array is not covering" % (path, key))
        c.cover = cover
        c.baseline_ok = len(errors) == nerr and ok == (not fails)
    print("  %d certificates, %.0f s" % (len(cases), time.time() - t0))
    print("  %-8s %-18s %6s %8s %8s" % ("kind", "case", "certs", "accepted", "covering"))
    for (kind, label), st in sorted(stats.items()):
        print("  %-8s %-18s %6d %8d %8d" % (kind, label, st[0], st[1], st[2]))
    hfail = {}
    for c, path, hyp, fails, rows in cases:
        for f in fails:
            hfail[f] = hfail.get(f, 0) + 1
    print("  hypotheses failing (oracle), cases: %s" % ", ".join("%s %d" % kv for kv in sorted(hfail.items())))
    print("  theorem: %d certificates satisfy every hypothesis; %d of their arrays not covering" % tuple(theorem))
    print("  checks compared with the oracle: %d, disagreements %d" % tuple(agree))

    mutants = [("disable:" + n, n, disabled) for n in all_check_names()] + [
        ("actm: 4-sets with a repeated x included", "actm", _actm_repeated_x),
        ("caps: H2 only", "caps", _caps_h2_only),
        ("orthogoval: 3-sets with a repeated point skipped", "orthogoval", _ortho_distinct_only)]
    survivors = []
    print("mutation testing (%d mutants):" % len(mutants))
    for mname, name, fn in mutants:
        saved = install(name, fn)
        killed = unsound = 0
        try:
            for c, path, hyp, fails, rows in cases:
                if not c.baseline_ok:
                    continue
                ok, got, csha = run_checker(path)
                if (ok != (not fails)) or (c.fault and c.fault in fails and c.fault not in got):
                    killed += 1
                if ok and not c.cover:
                    unsound += 1
        finally:
            restore(saved)
        status = "KILLED" if killed else ("not killable here (%s)" % IMPLIED[name]
                                          if name in IMPLIED and fn is disabled else "SURVIVED")
        if status == "SURVIVED":
            survivors.append(mname)
        print("  %-48s %-30s by %4d cases; accepts a non-covering array: %d" % (mname, status, killed, unsound))
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
