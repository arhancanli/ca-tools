#!/usr/bin/env python3
"""Tests of strength-3 certificates past k = 100,000 columns (standard library only; needs a C compiler).

Usage: python3 tools/cphf/tests/test_wide.py [--family FILE q] [--no-derive]

Nothing in tools/check_certificates.py, tools/cphf_cert.py or tools/cphf/cphfcheck.c depends on
100,000; these tests run the parts that see the width. Works on temporary copies of table/.
  plan       the planner at the sizes of strength-3 families up to 408,135 columns (fullfast, the method
             of families without progression rows): one shard each, the deal of the shards covers the
             outer loop, the totals are the binomials, and six such families fit one submission
  light      a random affine family with 100,001 columns over GF(32): cphfcheck reads it as the identity
             does, estimates it, and the pull request check passes with an exact check planned in shards
  ladder     a counted row at k = 408,135 (strength 3, v = 25) in a copy of the table: tools/derive_table.py
             continues its ladder past 100,000 (fusing gives v = 24 there), every line passes the check of
             derived.csv in tools/consistency.py, and the pages give the rung and the ladder's end;
             without the row the ladder stops at 100,000 as before (skipped with --no-derive)
  family     with --family FILE q: the whole certificate route on a real family (light check, plan, every
             task, results, apply-result --apply, consistency), as the workflows run it on main
Prints PASS/FAIL per test; exit status 0 only if everything passed.
"""
import csv
import json
import math
import os
import random
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "tools"))
sys.path.insert(0, HERE)
import cphf_cert as cc  # noqa: E402
import check_certificates as ck  # noqa: E402
import consistency  # noqa: E402
from test_certificates import fresh, consistency_problems, table_rows, quiet  # noqa: E402

RESULTS = []
# strength-3 families of the size the route would see (q, rows n, columns k)
WIDE = [(16, 8, 322146), (25, 7, 408135), (27, 6, 108143), (29, 6, 135764), (31, 6, 167721), (32, 6, 184913)]


def record(name, ok, detail=""):
    RESULTS.append((name, ok))
    print("%s %s%s" % ("PASS" if ok else "FAIL", name, "" if ok else ": " + " ".join(str(detail).split())[-400:]),
          flush=True)


def cert(args):
    return quiet(ck.main, args)


def write_claims(sub, rows):
    with open(os.path.join(sub, "certificates.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(ck.HEADER)
        for r in rows:
            w.writerow(r)


def main():
    argv = sys.argv[1:]
    tmp = tempfile.mkdtemp(prefix="widetest-")
    try:
        run_all(tmp, argv)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    bad = [n for n, ok in RESULTS if not ok]
    print("%d tests, %d failed%s" % (len(RESULTS), len(bad), (": " + ", ".join(bad)) if bad else ""))
    return 1 if bad else 0


def run_all(tmp, argv):
    exe = ck.build(tmp)
    ck.build = lambda _tmp: exe

    # plan: the estimate of fullfast (cphfcheck's unit costs, mirrored by cc.unit_ns) and the plan
    budget = cc.MAX_SHARDS * cc.SHARD_HOURS * cc.RUNNER_THREADS
    total = 0.0
    for q, n, k in WIDE:
        units = math.comb(k, 2)
        est = dict(cheapest=dict(method="fullfast", core_seconds=units * cc.unit_ns("fullfast", 3, q, k, n) * 1e-9))
        p = cc.plan_claim(est, k, 3)
        total += p["core_hours"]
        load = cc.deal("fullfast", k, 3, 3)
        tot = cc.expected_totals("fullfast", k, 3)
        record("plan: CPHF(%d; %d, %d, 3): %s in %d shard, %.2f core-hours with the factor 2" % (
            n, k, q, p["method"], p["shards"], p["core_hours"]),
            p["exact"] and p["shards"] == 1 and sum(load) == math.comb(k, 2)
            and tot == dict(units=math.comb(k, 3), prefixes=k, candidates=math.comb(k, 2)), p)
    record("plan: the six fit one submission (%.1f of %g core-hours)" % (total, budget), total < budget)

    # light: a wide random affine family over GF(32), read and estimated by cphfcheck, planned in shards
    root = fresh(tmp); tdir = os.path.join(root, "table")
    sub = os.path.join(root, "submissions", "test-wide")
    os.makedirs(sub)
    rng = random.Random(3)
    q, n, k = 32, 10, 100001
    with open(os.path.join(sub, "wide.txt"), "w") as f:
        for _ in range(n):
            f.write(" ".join(str(q * q + rng.randrange(q * q)) for _ in range(k)) + "\n")
    write_claims(sub, [[3, q, k, n * (q ** 3 - q) + q, "wide.txt", "", "test", "test CPHF", "cphf-smc2006",
                        "Test Person", ""]])
    code, out = cert([sub, "--table-dir", tdir, "--light", "--out", os.path.join(root, "light")])
    rpath = os.path.join(root, "light", "report.md")
    rep = open(rpath).read() if os.path.exists(rpath) else out
    record("light: a family of %d columns is read, estimated and planned (fullfast), and the screen passes" % k,
           code == 0 and "estimate" in rep and "exact check with fullfast" in rep and "nothing uncovered" in rep,
           rep[-400:])

    # ladder: a counted row past 100,000 in a copy of the table
    if "--no-derive" not in argv:
        for wide in (False, True):
            root = fresh(tmp); tdir = os.path.join(root, "table")
            if wide:
                with open(os.path.join(tdir, "ca_table.csv"), "a", newline="") as f:
                    f.write('3,25,408135,109225,VERIFIED,S7,test,test-wide,%s,"cphfcheck test (CPHF certificate, exact)",'
                            '2026-11-07,credit: Test Person,,,test CPHF,cphf-smc2006,%s\r\n' % ("a" * 64, "b" * 64))
            der = os.path.join(tdir, "derived.csv")
            p = subprocess.run([sys.executable, os.path.join(REPO, "tools", "derive_table.py"), "--out", der],
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True,
                               env=dict(os.environ, CA_TABLE=os.path.join(tdir, "ca_table.csv")))
            lines = list(csv.DictReader(open(der))) if os.path.exists(der) else []
            past = [d for d in lines if d["t"] == "3" and int(d["k"]) > 100000]
            cwd = os.getcwd(); os.chdir(root)
            try:
                consistency.problems.clear()
                raw, rows, man = consistency.load()
                consistency.check_derived(rows)
                prob = list(consistency.problems)
            finally:
                os.chdir(cwd)
            if not wide:
                same = open(der).read() == open(os.path.join(REPO, "table", "derived.csv")).read()
                record("ladder: without a wider row it stops at 100,000 and derived.csv is unchanged",
                       p.returncode == 0 and not past and same, p.stdout[-300:])
                continue
            v24 = [d for d in past if d["v"] == "24" and d["k"] == "400000"]
            record("ladder: with a row at k = 408,135 it goes on past 100,000 (v = 24 at 400,000: %s)"
                   % (v24[0]["N"] + " by " + v24[0]["law"] if v24 else "none"),
                   p.returncode == 0 and v24 and v24[0]["N"] == "109223" and v24[0]["lookup_N"] == "", p.stdout[-300:])
            record("ladder: every line passes the check of derived.csv (%d past 100,000)" % len(past), not prob,
                   "; ".join(prob[:3]))
            pages = {}
            for tool, out in (("render_table.py", "index.html"), ("render_derived.py", "derived.html")):
                pr = subprocess.run([sys.executable, os.path.join(REPO, "tools", tool), "--table-dir", tdir, "--out",
                                     os.path.join(root, out)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    universal_newlines=True)
                pages[out] = open(os.path.join(root, out)).read() if pr.returncode == 0 else pr.stdout
            record("ladder: the pages give the rung 100,001 to 408,135 and the ladder's end",
                   "100001 to 408135" in pages["index.html"] and "past k = 10,000" in pages["index.html"]
                   and "to k = 400,000 for comparison" in pages["index.html"]
                   and "ladder of widths up to k = 400,000" in pages["derived.html"], pages["index.html"][-300:])

    # family: the whole route on a real family
    if "--family" in argv:
        fam, fq = argv[argv.index("--family") + 1], int(argv[argv.index("--family") + 2])
        fsha, fn, fk, affine = cc.family_identity(fam, fq, 3)
        N = fn * (fq ** 3 - fq) + fq if affine else fn * (fq ** 3 - 1) + 1
        root = fresh(tmp); tdir = os.path.join(root, "table")
        sub = os.path.join(root, "submissions", "test-family")
        os.makedirs(sub); shutil.copy(fam, os.path.join(sub, "family.txt"))
        write_claims(sub, [[3, fq, fk, N, "family.txt", "", "test", "test CPHF", "cphf-smc2006", "Test Person", ""]])
        code, out = cert([sub, "--table-dir", tdir, "--light", "--out", os.path.join(root, "light")])
        record("family: light check of CPHF(%d; %d, %d, 3)" % (fn, fk, fq), code == 0, out[-300:])
        plan = os.path.join(root, "plan.json")
        cert([sub, "--table-dir", tdir, "--plan", plan])
        doc = json.load(open(plan))
        for tk in doc["tasks"]:
            code, out = cert([sub, "--table-dir", tdir, "--run", plan, "--task", tk, "--out",
                              os.path.join(root, "tasks", tk)])
            print("  %s: %s" % (tk, out.strip().splitlines()[-1] if out.strip() else code), flush=True)
        res = os.path.join(root, "result")
        code, out = cert([sub, "--table-dir", tdir, "--results", plan, "--tasks", os.path.join(root, "tasks"),
                          "--out", res])
        rj = json.load(open(os.path.join(res, "result.json")))
        record("family: results %s" % (rj["claims"][0]["check"] if rj["claims"] else "none"),
               code == 0 and rj["claims"] and rj["claims"][0]["tier"] == "VERIFIED", out[-300:])
        code, out = cert([sub, "--table-dir", tdir, "--apply-result", res, "--apply", "--out", os.path.join(root, "o")])
        r = table_rows(root)[-1]
        record("family: entered as VERIFIED at k = %s" % r["k"], code == 0 and r["tier"] == "VERIFIED"
               and r["k"] == str(fk) and r["family_sha256"] == fsha, out[-300:])
        pr = consistency_problems(root)
        record("family: consistency", not pr, "; ".join(pr[:3]))


if __name__ == "__main__":
    sys.exit(main())
