#!/usr/bin/env python3
"""Tests of the construction powercz-2 of tools/construction_cert.py (Power CZ with a column
relabelling per block and the constant tuples proved by exact enumeration, tools/CONSTRUCTION_CERT.md).

Part 1, the real certificate submissions/smolen-2026-11-powercz10201/CA_1400_5_10201_2.cert.json:
it passes and rebuilds the array of sha256 049f3a68...; with the identity relabelling it is rejected
by the enumeration with 20873 uncovered 5-sets for weight 0 and for weight 5; planted faults (a
relabel that is not a permutation, a wrong ingredient hash, a family row removed, an extra declared
weight, a wrong e, a repeated point, a weight missing from enumerate_weights, a weight of tau > 0 in
enumerate_weights, powercz-1 keys) are rejected by the check they target; without the C helper, or
with a helper source of another sha256, the certificate is rejected (the Python fallback refuses work
above its limit, it never passes).

Part 2, the C helper against the Python fallback on random binary arrays (t = 2..6): the same number
of missing (t-set, tuple) pairs and the same first miss for the quilting check, and the same bad-set
counts for z = 0 and 1.

Part 3, random small certificates (t = 3, 4; q = 5, 7; e = 2; 3 to 6 rows, forbidden values,
column limits) against an independent oracle: its own Reed-Solomon evaluation (direct powers), its
own relabelling and assembly, and a brute-force count over every t-set of the assembled array.
  A1 every accepted certificate gives a covering array of strength t (brute force), with the
     independently computed sha256
  A2 whenever the enumeration runs, its survivor count for weight 0 (weight t) equals the
     brute-force number of t-sets of array columns with no row constant 0 (constant 1)
  A3 the C helper and the Python fallback give the same verdict, the same failures and the same
     enumeration counts
  A4 (completeness of the rule) every case whose declared weights are true, whose species rule
     holds, whose ingredients have no bad set below t, and whose array has no t-set missing a
     constant tuple, is accepted
  A5 planted faults on accepted cases are rejected by the check they target (an over-declared
     weight: quilting; a relabel that is not a permutation: relabel; a wrong sha256: sha256 only)
Then two mutants: the enumeration check disabled, and the condition "no bad set below t" dropped
(Python path). Each must accept some certificate whose array is not covering.

Usage: test_powercz2.py [--cases N] [--seed S] [--skip-real]   (exit 1 on any violation)
"""
import argparse
import copy
import hashlib
import itertools
import json
import os
import random
import shutil
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import construction_cert as cc  # noqa: E402

SUB = os.path.join(ROOT, "submissions", "smolen-2026-11-powercz10201")
REAL = "CA_1400_5_10201_2.cert.json"
REAL_SHA = "049f3a6878cf9a73eae8b73a0267dadbc279cea6ea5cceb1ded0301dbed0d1ad"
IDENTITY_SURVIVORS = 20873

errors = []
stats = {}


def bump(key, n=1):
    stats[key] = stats.get(key, 0) + n


def run(path, helper=True):
    cc.Helper.disabled = not helper
    try:
        r = cc.run(path)
        return r["ok"], {f[0] for f in r["failures"]}, r
    except cc.CertError as ex:
        return False, {"malformed"}, {"malformed": str(ex)}
    finally:
        cc.Helper.disabled = False


def expect(label, ok, got, want_check):
    bump("real: " + label)
    if ok or want_check not in got:
        errors.append("%s: ok=%s failures=%s (wanted a rejection by %s)" % (label, ok, sorted(got), want_check))
    print("%-44s %s by %s" % (label, "ACCEPTED" if ok else "rejected", ", ".join(sorted(got))))


# ---------------------------------------------------------------------------------------------
# part 1: the real certificate

def part_real(work):
    d = os.path.join(work, "real")
    shutil.copytree(SUB, d)
    p = os.path.join(d, REAL)
    t0 = time.time()
    ok, got, r = run(p)
    print("real certificate: ok=%s N=%s k=%s sha256=%s enumeration=%s (%.1f s)"
          % (ok, r.get("N"), r.get("k"), r.get("sha256"),
             {w: (x.get("survivors"), x.get("candidates")) for w, x in r.get("enumeration", {}).items()},
             time.time() - t0))
    if not ok or r["sha256"] != REAL_SHA or (r["N"], r["k"]) != (1400, 10201):
        errors.append("the real certificate: ok=%s failures=%s sha256=%s" % (ok, r.get("failures"), r.get("sha256")))
    base = json.load(open(p))

    def variant(label, mutate, want, extra_file=None):
        c = copy.deepcopy(base)
        mutate(c)
        q = os.path.join(d, "variant.cert.json")
        json.dump(c, open(q, "w"))
        ok, got, r = run(q)
        expect(label, ok, got, want)
        return r

    # identity relabelling: 20873 uncovered 5-sets per weight
    r = variant("identity relabelling", lambda c: [x.pop("relabel") for x in c["family"]["rows"]], "enumeration")
    surv = {w: x.get("survivors") for w, x in r.get("enumeration", {}).items()}
    print("  identity relabelling: survivors %s (expected %d for both weights)" % (surv, IDENTITY_SURVIVORS))
    if surv != {0: IDENTITY_SURVIVORS, 5: IDENTITY_SURVIVORS}:
        errors.append("identity relabelling: survivors %s, expected %d per weight" % (surv, IDENTITY_SURVIVORS))

    def badperm(c):
        pi = c["family"]["rows"][3]["relabel"]
        pi[0] = pi[1]
    variant("relabel not a permutation (repeat)", badperm, "relabel")
    variant("relabel one column short", lambda c: c["family"]["rows"][2]["relabel"].pop(), "relabel")
    variant("relabel entry out of range", lambda c: c["family"]["rows"][5]["relabel"].__setitem__(7, 101), "relabel")
    variant("wrong ingredient hash", lambda c: c["ingredients"]["S14_101"].__setitem__("sha256", "0" * 64),
            "ingredient_hash")
    variant("a family row removed", lambda c: (c["family"]["rows"].pop(), c["expected"].__setitem__("N", 1200)),
            "species")
    variant("weight 5 declared by S14 (extra weight)",
            lambda c: c["ingredients"]["S14_101"].__setitem__("covers", {"weights": [1, 5]}), "quilting")
    variant("wrong e (e = 3)", lambda c: c.__setitem__("e", 3), "malformed")
    variant("wrong e (e = 1)", lambda c: c.__setitem__("e", 1), "malformed")
    variant("repeated point", lambda c: c["family"]["rows"][6].__setitem__("point", 0), "agreement")
    variant("weight 5 not in enumerate_weights", lambda c: c.__setitem__("enumerate_weights", [0]), "species")
    variant("weight 2 in enumerate_weights", lambda c: c.__setitem__("enumerate_weights", [0, 2, 5]), "malformed")
    variant("enumerate_weights in a powercz-1 certificate",
            lambda c: (c.__setitem__("construction", "powercz-1"), [x.pop("relabel") for x in c["family"]["rows"]]),
            "malformed")
    variant("relabel in a powercz-1 certificate",
            lambda c: (c.__setitem__("construction", "powercz-1"), c.pop("enumerate_weights")), "malformed")

    def minus_row(c):
        rows = open(os.path.join(d, "S14_101.txt")).read().splitlines()
        text = "\n".join(rows[:-1]) + "\n"
        open(os.path.join(d, "S14_minus.txt"), "w").write(text)
        c["ingredients"]["S14_101"].update(file="S14_minus.txt", sha256=hashlib.sha256(text.encode()).hexdigest())
    variant("ingredient with one row removed", minus_row, "quilting")

    # without the helper the Python fallback must refuse (never pass)
    ok, got, r = run(p, helper=False)
    expect("no C helper (Python fallback over its limit)", ok, got, "quilting")
    if "enumeration" not in got:
        errors.append("no C helper: the enumeration should also refuse, failures %s" % sorted(got))
    # a helper source that is not the recorded one is not used
    saved = cc.HELPER_SHA256, cc.Helper.tried, cc.Helper.path
    cc.HELPER_SHA256, cc.Helper.tried, cc.Helper.path = "0" * 64, False, None
    try:
        ok, got, r = run(p)
        expect("helper source of another sha256", ok, got, "quilting")
        if "sha256" not in (cc.Helper.why or ""):
            errors.append("helper source hash: reason %r" % cc.Helper.why)
    finally:
        cc.HELPER_SHA256, cc.Helper.tried, cc.Helper.path = saved


# ---------------------------------------------------------------------------------------------
# part 2: helper against the Python fallback on random binary arrays

def part_helper(rng, work, n):
    if not cc.Helper.get():
        errors.append("the C helper could not be built: %s" % cc.Helper.why)
        return
    for i in range(n):
        t = rng.choice([2, 3, 4, 5, 6])
        w = rng.randint(t, 12 if t < 6 else 10)
        R = rng.randint(1, 70)
        p1 = rng.choice([0.5, 0.5, 0.2, 0.8])
        rows = [[1 if rng.random() < p1 else 0 for _ in range(w)] for _ in range(R)]
        path = os.path.join(work, "h.txt")
        with open(path, "w") as f:
            for r in rows:
                f.write(" ".join(map(str, r)) + "\n")
        wts = sorted(rng.sample(range(t + 1), rng.randint(1, t + 1)))
        res = cc.Helper.run(["quilt", path, t, sum(1 << x for x in wts)]).split()
        miss = int(res[2])
        first = (list(map(int, res[4:4 + t])), int(res[5 + t])) if miss else None
        pm, pf = cc.py_quilt_missing(rows, t, set(wts))
        bump("helper/python quilting comparisons")
        if (miss, first) != (pm, pf):
            errors.append("quilt t=%d w=%d R=%d weights %s: helper %s %s, python %s %s" % (t, w, R, wts, miss, first, pm, pf))
        for z in (0, 1):
            hc = {}
            for line in cc.Helper.run(["bad", path, t, z]).splitlines():
                f = line.split()
                hc[int(f[1])] = int(f[2])
            pc = cc.py_bad(rows, t, z)[0]
            bump("helper/python bad-set comparisons")
            if hc != pc:
                errors.append("bad t=%d w=%d R=%d z=%d: helper %s, python %s" % (t, w, R, z, hc, pc))


# ---------------------------------------------------------------------------------------------
# part 3: random certificates against an independent oracle

def rs_values(q, e, pts, forb, limit):
    """the columns kept: for each coefficient tuple (c_0 most significant) the values at the points
    (direct powers mod q, prime q; "inf" the top coefficient), without forbidden values"""
    cols = []
    for co in itertools.product(range(q), repeat=e):
        vals = [co[e - 1] if x == "inf" else sum(cj * pow(x, j, q) for j, cj in enumerate(co)) % q for x in pts]
        if all(vals[i] not in forb[i] for i in range(len(pts))):
            cols.append(vals)
    return cols[:limit] if limit else cols


def assemble(q, e, pts, forb, limit, ings, rel):
    cols = rs_values(q, e, pts, forb, limit)
    A = []
    for i, Q in enumerate(ings):
        allowed = [s for s in range(q) if s not in forb[i]]
        rank = {s: n for n, s in enumerate(allowed)}
        for row in Q:
            A.append([row[rel[i][rank[cv[i]]]] for cv in cols])
    return A, len(cols)


def brute(A, t, k):
    """(t-sets missing some tuple, t-sets with no row constant 0, ... constant 1)"""
    cols = [tuple(r[j] for r in A) for j in range(k)]
    m0 = [sum(1 << i for i, x in enumerate(c) if x == 0) for c in cols]
    m1 = [sum(1 << i for i, x in enumerate(c) if x == 1) for c in cols]
    miss_any, miss0, miss1 = 0, 0, 0
    for cs in itertools.combinations(range(k), t):
        if len(set(zip(*[cols[j] for j in cs]))) < 2 ** t:
            miss_any += 1
        x0, x1 = -1, -1
        for j in cs:
            x0 &= m0[j]
            x1 &= m1[j]
        miss0 += x0 == 0
        miss1 += x1 == 0
    return miss_any, miss0, miss1


def covers_weight(Q, t, wt):
    w = len(Q[0])
    for cs in itertools.combinations(range(w), t):
        seen = {tuple(r[j] for j in cs) for r in Q}
        for tp in itertools.product((0, 1), repeat=t):
            if sum(tp) == wt and tp not in seen:
                return False
    return True


def small_bad(Q, t):
    """does some s-set, s < t, of columns have no row constant 0, or none constant 1"""
    w = len(Q[0])
    for z in (0, 1):
        for cs in itertools.combinations(range(w), t - 1):
            if not any(all(r[j] == z for j in cs) for r in Q):
                return True
    return False


def make_ingredient(rng, w, t):
    """rows of weight 1..w-1, thinned while weights 1..t-1 stay covered, then rows constant z on a
    random part of the (t-1)-sets and t-sets (so bad sets of each size occur)"""
    rows = [list(v) for v in itertools.product((0, 1), repeat=w) if 0 < sum(v) < w]
    rng.shuffle(rows)
    keep = list(rows)
    for r in rows:
        if len(keep) > 4 and rng.random() < 0.85:
            trial = [x for x in keep if x is not r]
            if all(covers_weight(trial, t, x) for x in range(1, t)):
                keep = trial
    frac = rng.choice([0.0, 0.0, 0.15, 0.4])
    small = rng.random() < 0.2
    for z in (0, 1):
        for S in itertools.combinations(range(w), t - 1):
            if not small or rng.random() < 0.9:
                keep.append([z if j in S else 1 - z for j in range(w)])
        for S in itertools.combinations(range(w), t):
            if rng.random() < frac:
                keep.append([z if j in S else 1 - z for j in range(w)])
    rng.shuffle(keep)
    return keep


def canon_sha(A):
    return hashlib.sha256("".join(" ".join(map(str, r)) + "\n" for r in A).encode()).hexdigest()


def write(work, name, cert):
    p = os.path.join(work, name)
    with open(p, "w") as f:
        json.dump(cert, f)
    return p


def part_random(rng, work, cases):
    for case in range(cases):
        t, q = rng.choice([(3, 5), (4, 5), (3, 7)])
        M = rng.choice([3, 3, 4, 5, 6])
        pts = rng.sample(list(range(q)) + ["inf"], M)
        forb = [[] for _ in range(M)]
        if rng.random() < 0.3:
            forb[-1] = [rng.randrange(q)]
        kept = len(rs_values(q, 2, pts, forb, None))
        limit = rng.choice([None, None, None, rng.randint(t + 2, kept - 1)])
        pool = {}
        names, ings = [], []
        for i in range(M):
            w = q - len(forb[i])
            key = (w, rng.choice("ab"))
            if key not in pool:
                pool[key] = ("Q%d" % len(pool), make_ingredient(rng, w, t))
            names.append(pool[key][0])
            ings.append(pool[key][1])
        rel = []
        for i in range(M):
            pi = list(range(q - len(forb[i])))
            if rng.random() < 0.8:
                rng.shuffle(pi)
            rel.append(pi)
        ing_def = {}
        for nm, Q in pool.values():
            cw = [x for x in range(t + 1) if covers_weight(Q, t, x)]
            if rng.random() < 0.8:
                cw = [x for x in cw if 0 < x < t]       # usually leave the constant tuples to the enumeration
            ing_def[nm] = {"rows": Q, "covers": {"species": [[t - x, x] for x in cw]}}
        ew = rng.choice([[0, t], [0, t], [0, t], [0], [t], []])
        A, k = assemble(q, 2, pts, forb, limit, ings, rel)
        fam = {"type": "reed-solomon", "rows": [{"point": pts[i], "forbidden": forb[i], "ingredient": names[i],
                                                 "relabel": rel[i]} for i in range(M)]}
        if limit:
            fam["column_limit"] = limit
        cert = {"format": "construction-cert-1", "construction": "powercz-2", "t": t, "v": 2, "e": 2,
                "field": {"q": q, "p": q, "m": 1}, "family": fam, "ingredients": ing_def, "enumerate_weights": ew,
                "expected": {"N": len(A), "k": k, "array_sha256": canon_sha(A)}}
        p = write(work, "c.json", cert)
        miss_any, miss0, miss1 = brute(A, t, k)
        okC, gotC, rC = run(p, helper=True)
        okP, gotP, rP = run(p, helper=False)
        bump("random certificates")
        if "malformed" in gotC:
            errors.append("case %d malformed: %s" % (case, rC))
            continue
        # A3
        enum_c = {w: {x: y for x, y in v.items() if x != "method"} for w, v in rC["enumeration"].items()}
        enum_p = {w: {x: y for x, y in v.items() if x != "method"} for w, v in rP["enumeration"].items()}
        if okC != okP or rC["failures"] != rP["failures"] or enum_c != enum_p:
            errors.append("A3 case %d: helper %s %s %s / python %s %s %s" % (case, okC, rC["failures"], enum_c,
                                                                          okP, rP["failures"], enum_p))
        bump("A3 helper = python")
        # A1
        if okC:
            bump("accepted")
            if miss_any:
                errors.append("A1 case %d: accepted, but %d t-sets miss a tuple" % (case, miss_any))
            if rC["sha256"] != canon_sha(A):
                errors.append("A1 case %d: sha256 differs from the independent one" % case)
        else:
            bump("rejected")
            bump("rejected, covering anyway" if not miss_any else "rejected, not covering")
        # A2
        for w, rep in rC["enumeration"].items():
            if "survivors" in rep:
                want = miss0 if w == 0 else miss1
                bump("A2 survivor counts compared")
                if rep["survivors"]:
                    bump("A2 nonzero survivor counts")
                if rep["survivors"] != want:
                    errors.append("A2 case %d weight %d: %d survivors, brute force %d" % (case, w, rep["survivors"], want))
        # A4
        decl_true = all(covers_weight(d["rows"], t, sp[1]) for d in ing_def.values() for sp in map(tuple, d["covers"]["species"]))
        nsb = not any(small_bad(d["rows"], t) for d in ing_def.values())
        const_ok = all((miss0 if w == 0 else miss1) == 0 for w in ew)
        if decl_true and "species" not in gotC and (nsb or not ew) and const_ok:
            bump("A4 cases")
            if not okC:
                errors.append("A4 case %d: rejected %s" % (case, rC["failures"]))
        if ew and not nsb:
            bump("cases with a bad set below t")
        # A5
        if okC and case % 2 == 0:
            for label, mutate, want in [
                    ("over-declared weight", None, "quilting"),
                    ("relabel not a permutation", lambda c: c["family"]["rows"][0].__setitem__(
                        "relabel", [0] * len(c["family"]["rows"][0]["relabel"])), "relabel"),
                    ("wrong sha256", lambda c: c["expected"].__setitem__("array_sha256", "0" * 64), "sha256")]:
                c2 = copy.deepcopy(cert)
                if mutate is None:
                    nm = names[0]
                    have = [sp[1] for sp in c2["ingredients"][nm]["covers"]["species"]]
                    extra = [x for x in range(t + 1) if x not in have and not covers_weight(ing_def[nm]["rows"], t, x)]
                    if not extra:
                        continue
                    c2["ingredients"][nm]["covers"]["species"].append([t - extra[0], extra[0]])
                else:
                    mutate(c2)
                ok2, got2, _ = run(write(work, "f.json", c2))
                bump("A5 planted faults")
                if ok2 or want not in got2 or (want == "sha256" and got2 != {"sha256"}):
                    errors.append("A5 case %d %s: ok=%s %s" % (case, label, ok2, sorted(got2)))


def mutant_runs(p):
    """(accepted with the enumeration check disabled, accepted with the condition on bad sets below t
    dropped); the second runs the Python path with py_bad reporting no bad set below t"""
    saved = cc.CHECKS2
    cc.CHECKS2 = [x for x in saved if x[0] != "enumeration"]
    try:
        ok_enum = run(p)[0]
    finally:
        cc.CHECKS2 = saved
    saved_bad = cc.py_bad

    def no_small(rows, tt, z, listing=False):
        w = len(rows[0])
        bad = [cs for cs in itertools.combinations(range(w), tt)
               if not any(all(r[j] == z for j in cs) for r in rows)]
        counts = {s: 0 for s in range(1, tt)}
        counts[tt] = len(bad)
        return counts, (bad if listing else [])
    cc.py_bad = no_small
    try:
        ok_coll = run(p, helper=False)[0]
    finally:
        cc.py_bad = saved_bad
    return ok_enum, ok_coll


def part_mutants(rng, work, cases):
    """targeted cases for the two mutants.
    E (random): one ingredient with bad t-sets and the identity relabelling in every block, so that
    the constant polynomials give an uncovered t-set; the enumeration must reject it.
    C (fixed): t = 3, an explicit family of 3 columns and 5 rows. Rows 0..2 use an ingredient P on
    4 columns (weights 1, 2, no bad set below t, bad 3-sets {0,1,2} and {1,2,3} for z = 0), rows 3, 4
    an ingredient R on 3 columns (weight 2, no row 00 on the columns {0, 1}). The three array columns
    have the images {0,1,2} in rows 0..2 and collapse onto {0, 1} in rows 3 and 4, so they miss 000.
    R has the fewest bad 3-sets, so the enumeration reconstructs from rows 3 and 4, where the
    collapsed t-set cannot be seen: only the condition on bad sets below t rejects it."""
    kill = {"E": 0, "C": 0}
    t, q = 3, 5
    for case in range(cases):
        M = rng.choice([3, 4, 5])
        P = None
        while P is None or small_bad(P, t) or not all(covers_weight(P, t, x) for x in range(1, t)):
            P = make_ingredient(rng, q, t)
        A, k = assemble(q, 2, list(range(M)), [[] for _ in range(M)], None, [P] * M, [list(range(q))] * M)
        cert = {"format": "construction-cert-1", "construction": "powercz-2", "t": t, "v": 2, "e": 2,
                "field": {"q": q, "p": q, "m": 1},
                "family": {"type": "reed-solomon", "rows": [{"point": i, "forbidden": [], "ingredient": "P"}
                                                            for i in range(M)]},
                "ingredients": {"P": {"rows": P, "covers": {"weights": [1, t - 1]}}}, "enumerate_weights": [0, t],
                "expected": {"N": len(A), "k": k, "array_sha256": canon_sha(A)}}
        p = write(work, "m.json", cert)
        miss_any, miss0, miss1 = brute(A, t, k)
        ok, got, r = run(p)
        bump("mutant scenario E")
        for w, rep in r.get("enumeration", {}).items():
            if "survivors" in rep:
                bump("A2 survivor counts compared")
                bump("A2 nonzero survivor counts", rep["survivors"] > 0)
                if rep["survivors"] != (miss0 if w == 0 else miss1):
                    errors.append("A2 scenario E case %d weight %d: %d survivors, brute force %d"
                                  % (case, w, rep["survivors"], miss0 if w == 0 else miss1))
        if ok and miss_any:
            errors.append("A1 mutant scenario E case %d: accepted, not covering" % case)
        if miss_any and not ok:
            kill["E"] += mutant_runs(p)[0]
    # scenario C
    X = [(0, 1, 2), (1, 2, 3)]
    P = [list(v) for v in itertools.product((0, 1), repeat=4) if 0 < sum(v) < 4
         and not any(all(v[j] == 0 for j in S) for S in X)] + [[1, 1, 1, 1]]
    R = [[1, 1, 0], [1, 0, 1], [0, 1, 1], [1, 1, 1], [0, 1, 0], [1, 0, 0]]
    vals = [[0, 1, 2], [0, 1, 2], [0, 1, 2], [0, 0, 1], [1, 0, 0]]
    ings = [P, P, P, R, R]
    A = [[Q[i][vals[r][c]] for c in range(3)] for r, Q in enumerate(ings) for i in range(len(Q))]
    cert = {"format": "construction-cert-1", "construction": "powercz-2", "t": 3, "v": 2, "e": 2,
            "family": {"type": "explicit", "rows": [{"width": len(ings[r][0]), "values": vals[r],
                                                     "ingredient": "P" if r < 3 else "R"} for r in range(5)]},
            "ingredients": {"P": {"rows": P, "covers": {"weights": [1, 2]}}, "R": {"rows": R, "covers": {"weights": [2, 2]}}},
            "enumerate_weights": [0, 3], "expected": {"N": len(A), "k": 3, "array_sha256": canon_sha(A)}}
    p = write(work, "c.json", cert)
    miss_any, miss0, _ = brute(A, 3, 3)
    ok, got, r = run(p)
    okP = run(p, helper=False)[0]
    ok_enum, ok_coll = mutant_runs(p)
    print("collapse example: %d t-set misses 000 (brute force); checker %s by %s; python %s; mutant without the "
          "condition on bad sets below t: %s" % (miss0, "accepts" if ok else "rejects", sorted(got),
                                                 "accepts" if okP else "rejects", "accepts" if ok_coll else "rejects"))
    if miss0 != 1 or ok or okP or "enumeration" not in got or not ok_coll:
        errors.append("collapse example: miss0=%d ok=%s python=%s failures=%s mutant=%s" % (miss0, ok, okP, sorted(got), ok_coll))
    kill["C"] += ok_coll and miss_any > 0
    stats["mutant enumeration disabled: non-covering arrays accepted"] = kill["E"]
    stats["mutant no bad set below t required: non-covering arrays accepted"] = kill["C"]
    for m, label in (("E", "the enumeration check disabled"), ("C", "the condition on bad sets below t dropped")):
        if not kill[m]:
            errors.append("the mutant with %s survives" % label)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", type=int, default=60)
    ap.add_argument("--seed", type=int, default=20261103)
    ap.add_argument("--skip-real", action="store_true")
    a = ap.parse_args(argv)
    rng = random.Random(a.seed)
    work = tempfile.mkdtemp(prefix="powercz2_")
    t0 = time.time()
    try:
        if not a.skip_real:
            part_real(work)
        part_helper(rng, work, max(20, a.cases))
        part_random(rng, work, a.cases)
        part_mutants(rng, work, max(20, a.cases // 2))
    finally:
        shutil.rmtree(work, ignore_errors=True)
    print("seed %d, %.0f s" % (a.seed, time.time() - t0))
    for kv in sorted(stats.items()):
        print("  %s: %s" % kv)
    if errors:
        print("ERRORS:")
        for e in errors:
            print("  " + e)
        return 1
    print("ALL POWERCZ-2 TESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
