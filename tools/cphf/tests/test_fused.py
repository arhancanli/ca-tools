#!/usr/bin/env python3
"""Tests of fused listings (certificates.csv with the column expansion, tools/check_certificates.py) and of
tools/cphf/fusestream.c (standard library only; needs a C compiler).

Usage: python3 tools/cphf/tests/test_fused.py

Works on temporary copies of table/ (without arrays/), never on the repository's own table. Tests:
  rule       cphf_cert.fuse_steps on the rules listed in the table, and its refusals (a step that does
             not remove the largest symbol, "fuse a>b" with b >= a, fewer than two symbols left);
             expansion_runs agrees with it on the number of symbols
  stream     fusestream equals fuse2.c, the reference of "+fuse2", on an expanded family (one step, and
             three chained steps against three chained runs of fuse2.c), and "fuse a b" equals the
             substitution; the two fused listings of CPHF_16_781_5_6.txt rebuild to their listed
             array_sha256
  covering   fused arrays of stored families are covering arrays (ca_verify, every t-set)
  malformed  fusestream refuses a ragged run, a symbol at or above q, too few runs and a bad step
  spot       its spot check passes on a fused family and catches a cut array
  claim      a fused listing of a family in the table: the light check, the local check with --apply, and
             the sharded form (plan, hash task, results, apply-result --apply), each followed by the
             consistency checks; the row carries the family's stamp, the listing names the family's file
             and records the spot check of the fused array
  refused    a family not in the table, a SCREENED family, a file in the submission, a mode, the wrong N,
             the wrong v, another base rule, a step that does not remove the largest symbol, a rule
             without steps, a listing already in the table, a listing named twice, an array above the
             hash threshold, a tampered result
Prints PASS/FAIL per test; exit status 0 only if everything passed.
"""
import csv
import hashlib
import json
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
import cphf_cert as cc  # noqa: E402
import check_certificates as ck  # noqa: E402
from test_certificates import fresh, consistency_problems, table_rows, quiet  # noqa: E402

RESULTS = []
CERTS = os.path.join(REPO, "table", "certificates")
HEADER = ck.HEADER + ["expansion"]


def record(name, ok, detail=""):
    RESULTS.append((name, ok))
    print("%s %s%s" % ("PASS" if ok else "FAIL", name, "" if ok else ": " + " ".join(str(detail).split())[-400:]),
          flush=True)


def cert(args):
    return quiet(ck.main, args)


def fused_claim(t, v, k, N, fname, rule, mode=""):
    return dict(t=t, v=v, k=k, N=N, file=fname, mode=mode, source_detail="test", construction="test fused CPHF",
                builds_on="cphf-smc2006", credit="Test Person", notes="", expansion=rule)


def write_claims(sub, claims, header=HEADER):
    os.makedirs(sub, exist_ok=True)
    with open(os.path.join(sub, "certificates.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        for c in claims:
            w.writerow([c.get(x, "") for x in header])


def cc_build(src, out, extra=()):
    subprocess.run(["cc", "-O2"] + list(extra) + ["-o", out, src], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out


def expand(exe, fam, t, q, affine, out):
    subprocess.run([exe, fam, str(t), str(q), "expand", out] + (["affine"] if affine else []), check=True,
                   stdout=subprocess.DEVNULL)


def fusestream(fz, src, q, steps, out=None):
    p = subprocess.run([fz, src, str(q)] + [x for s in steps for x in s], stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE)
    if out:
        with open(out, "wb") as f:
            f.write(p.stdout)
    return p.returncode, hashlib.sha256(p.stdout).hexdigest(), p.stderr.decode()


def fuse2_ref(f2, src, v, t, out):
    """fuse2.c: v the new number of symbols; no spot check (S = 0); returns the sha256 it prints"""
    with open(src, "rb") as f:
        p = subprocess.run([f2, str(v), str(t), "0", "1", out], stdin=f, stdout=subprocess.PIPE,
                           universal_newlines=True)
    m = re.search(r"sha256 ([0-9a-f]{64})", p.stdout)
    return m.group(1) if m and p.returncode == 0 else None


def sha(path):
    return ck.file_sha(path)


def main():
    tmp = tempfile.mkdtemp(prefix="fusetest-")
    try:
        run_all(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    bad = [n for n, ok in RESULTS if not ok]
    print("%d tests, %d failed%s" % (len(RESULTS), len(bad), (": " + ", ".join(bad)) if bad else ""))
    return 1 if bad else 0


def run_all(tmp):
    exe = ck.build(tmp)
    ck.build = lambda _tmp: exe
    fz = ck.build_fuse(tmp)
    f2 = cc_build(os.path.join(REPO, "tools", "cphf", "fuse2.c"), os.path.join(tmp, "fuse2"))
    cav = cc_build(os.path.join(REPO, "ca_verify.c"), os.path.join(tmp, "ca_verify"), ["-O3", "-pthread"])

    # rule
    listed = list(csv.DictReader(open(os.path.join(CERTS, "CERTIFICATES.csv"))))
    ok, why = True, ""
    for c in listed:
        m = re.match(r"CPHF\((\d+); (\d+), (\d+), (\d+)\)", c["family"]); n, k, q, t = map(int, m.groups())
        steps, v = cc.fuse_steps(c["expansion"], q)
        if v != int(c["v"]) or cc.expansion_runs(c["expansion"], n, q, t)[1] != v or (("fused" in c["family"]) != bool(steps)):
            ok, why = False, c["file"] + " " + c["expansion"]
    record("rule: every listed expansion reads, with its v", ok, why)
    record("rule: chained steps", cc.fuse_steps("smc-1-affine+fuse2 22+fuse2 21+fuse 20>3", 23)
           == ([["fuse2", "22"], ["fuse2", "21"], ["fuse", "20", "3"]], 20))
    for rule, q, what in (("smc-1+fuse2 3", 5, "not the largest symbol"), ("smc-1+fuse 4>4", 5, "b >= a"),
                          ("smc-1+fuse2 1", 2, "one symbol left"), ("smc-1+fuse2 4+fuse2 4", 5, "a removed twice"),
                          ("smc-2+fuse2 4", 5, "unknown base")):
        try:
            cc.fuse_steps(rule, q); got = False
        except cc.CertError:
            got = True
        record("rule refused: %s (%s)" % (rule, what), got)

    # stream
    fam23 = os.path.join(CERTS, "CPHF_2_48_23_4.txt")          # affine, q = 23, t = 4: 559,659 runs of 48
    big = os.path.join(tmp, "a23.txt"); expand(exe, fam23, 4, 23, True, big)
    code, h1, err = fusestream(fz, big, 23, [["fuse2", "22"]])
    ref1 = fuse2_ref(f2, big, 22, 4, os.path.join(tmp, "r1.txt"))
    record("stream: one fuse2 step equals fuse2.c", code == 0 and h1 == ref1, "%s %s %s" % (h1, ref1, err))
    ref2 = fuse2_ref(f2, os.path.join(tmp, "r1.txt"), 21, 4, os.path.join(tmp, "r2.txt"))
    ref3 = fuse2_ref(f2, os.path.join(tmp, "r2.txt"), 20, 4, os.path.join(tmp, "r3.txt"))
    code, h3, err = fusestream(fz, big, 23, [["fuse2", "22"], ["fuse2", "21"], ["fuse2", "20"]],
                               os.path.join(tmp, "s3.txt"))
    record("stream: three chained fuse2 steps equal three runs of fuse2.c", code == 0 and h3 == ref3 and
           sum(1 for _ in open(os.path.join(tmp, "s3.txt"))) == 559659 - 6, "%s %s %s" % (h3, ref3, err))
    with open(big, "rb") as f:
        sub = re.sub(rb"\b22\b", b"5", f.read())
    code, h, err = fusestream(fz, big, 23, [["fuse", "22", "5"]])
    record("stream: fuse a b is the substitution", code == 0 and h == hashlib.sha256(sub).hexdigest(), err)
    os.remove(big)
    for f in ("r1.txt", "r2.txt", "r3.txt", "s3.txt"):
        os.remove(os.path.join(tmp, f))
    fam5 = os.path.join(CERTS, "CPHF_16_781_5_6.txt")
    fifo = os.path.join(tmp, "x.fifo")
    for rule in ("smc-1+fuse 4>0", "smc-1+fuse2 4"):
        want = [c["array_sha256"] for c in listed if c["file"] == "CPHF_16_781_5_6.txt" and c["expansion"] == rule]
        rows, h = ck.stream_hash(exe, fam5, 6, 5, False, tmp, cc.fuse_steps(rule, 5)[0])
        record("stream: %s of CPHF_16_781_5_6.txt rebuilds to its listed array_sha256" % rule,
               len(want) == 1 and h == want[0] and rows == cc.expansion_runs(rule, 16, 5, 6)[0], h)

    # covering (a column subset of a CPHF is a CPHF; the first columns keep the check short)
    for name, t, q, affine, cols, steps, v in (
            ("CPHF_10_2876_4_3.txt", 3, 4, True, 2876, [["fuse2", "3"], ["fuse2", "2"]], 2),
            ("CPHF_10_2876_4_3.txt", 3, 4, True, 300, [["fuse2", "3"]], 3),
            ("CPHF_11_121_3_5.txt", 5, 3, False, 40, [["fuse2", "2"]], 2),
            ("CPHF_10_646_5_4.txt", 4, 5, True, 60, [["fuse2", "4"], ["fuse", "3", "1"]], 3)):
        fam = os.path.join(tmp, "fam.txt")
        with open(fam, "w") as f:
            f.write("".join(" ".join(r[:cols]) + "\n" for r in
                            ([x.split() for x in open(os.path.join(CERTS, name)) if x.strip() and not x.startswith("#")])))
        a = os.path.join(tmp, "a.txt"); expand(exe, fam, t, q, affine, a)
        out = os.path.join(tmp, "f.txt")
        code, h, err = fusestream(fz, a, q, steps, out)
        p = subprocess.run([cav, out, str(t), str(v), "2"], stdout=subprocess.PIPE, universal_newlines=True)
        record("covering: %s on %d columns, %s, is a CA(%d; %d, %d, %d) (ca_verify)"
               % (name, cols, " ".join(" ".join(x) for x in steps), sum(1 for _ in open(out)), t, cols, v),
               code == 0 and p.returncode == 0 and "VERIFIED" in p.stdout, p.stdout[-300:] + err)

    # malformed
    bad = os.path.join(tmp, "bad.txt")
    for text, q, steps, what in (("0 1 2\n1 2\n2 0 1\n", 3, [["fuse2", "2"]], "a ragged run"),
                                 ("0 1 3\n1 2 0\n2 0 1\n", 3, [["fuse2", "2"]], "a symbol at q"),
                                 ("0 1 2\n", 3, [["fuse2", "2"]], "too few runs"),
                                 ("0 1 2\n1 2 0\n2 0 1\n", 3, [["fuse2", "1"]], "a step that is not the largest"),
                                 ("0,1,2\n1,2,0\n2,0,1\n", 3, [["fuse2", "2"]], "commas")):
        open(bad, "w").write(text)
        code, h, err = fusestream(fz, bad, q, steps)
        record("malformed refused: %s" % what, code == 2 and err, err)

    # spot
    a = os.path.join(tmp, "a.txt"); expand(exe, os.path.join(CERTS, "CPHF_10_2876_4_3.txt"), 3, 4, True, a)
    cut = os.path.join(tmp, "cut.txt")
    with open(a) as f, open(cut, "w") as g:
        g.writelines(l for i, l in enumerate(f) if i < 300)
    for src, want, what in ((a, 0, "passes on the fused family"), (cut, 1, "catches a cut array (exit 1)")):
        p = subprocess.run([fz, src, "4", "fuse2", "3", "check", "3", "2000", "5"], stdout=subprocess.DEVNULL,
                           stderr=subprocess.PIPE, universal_newlines=True)
        record("spot: the check %s" % what, p.returncode == want and ("uncovered 0" in p.stderr) == (want == 0),
               p.stderr)

    # claim: a fused listing of a stored family, local and sharded
    for mode in ("local", "sharded"):
        root = fresh(tmp); tdir = os.path.join(root, "table")
        sub = os.path.join(root, "submissions", "test-fused-" + mode)
        write_claims(sub, [fused_claim(5, 2, 121, 2661, "table/certificates/CPHF_11_121_3_5.txt", "smc-1+fuse2 2"),
                           fused_claim(5, 2, 121, 2663, "table/certificates/CPHF_11_121_3_5.txt", "smc-1+fuse 2>0"),
                           fused_claim(3, 2, 2876, 600, "table/certificates/CPHF_10_2876_4_3.txt",
                                       "smc-1-affine+fuse2 3+fuse2 2")])
        before = len(table_rows(root))
        if mode == "local":
            code, out = cert([sub, "--table-dir", tdir, "--light", "--out", os.path.join(root, "light")])
            rep = open(os.path.join(root, "light", "report.md")).read()
            record("claim: light check passes and says no exact check runs", code == 0 and rep.count("no exact check") == 3
                   and "Result: PASS" in rep, rep[-400:])
            code, out = cert([sub, "--table-dir", tdir, "--threads", "2", "--apply"])
        else:
            plan = os.path.join(root, "plan.json")
            cert([sub, "--table-dir", tdir, "--plan", plan, "--threads", "2"])
            doc = json.load(open(plan))
            record("claim: the plan has one hash job per fused listing and no shard",
                   doc["tasks"] == ["c0-hash", "c1-hash", "c2-hash"], doc["tasks"])
            for tk in doc["tasks"]:
                cert([sub, "--table-dir", tdir, "--run", plan, "--task", tk, "--out", os.path.join(root, "tasks", tk)])
            res = os.path.join(root, "result")
            code, out = cert([sub, "--table-dir", tdir, "--results", plan, "--tasks", os.path.join(root, "tasks"),
                              "--out", res])
            rj = json.load(open(os.path.join(res, "result.json")))
            record("claim: results VERIFIED", code == 0 and [c["tier"] for c in rj["claims"]] == ["VERIFIED"] * 3, out[-300:])
            forged = os.path.join(root, "forged")
            shutil.copytree(res, forged)
            rj2 = json.load(open(os.path.join(forged, "result.json")))
            rj2["claims"][0]["stamp"] = "cphfcheck 000000000000 2026-01-01 forged (CPHF certificate, exact; x)"
            json.dump(rj2, open(os.path.join(forged, "result.json"), "w"))
            code, out = cert([sub, "--table-dir", tdir, "--apply-result", forged, "--apply", "--out",
                              os.path.join(root, "o1")])
            record("refused: a tampered result", code == 1 and len(table_rows(root)) == before, out[-200:])
            code, out = cert([sub, "--table-dir", tdir, "--apply-result", res, "--apply", "--out", os.path.join(root, "o")])
        rows = table_rows(root)
        new = rows[before:]
        base = {x["k"]: x["check"].split(": ", 1)[0] for x in listed
                if x["file"] in ("CPHF_11_121_3_5.txt", "CPHF_10_2876_4_3.txt") and "fused" not in x["family"]}
        stamps_ok = len(new) == 3 and all(r["verify_stamp"].startswith(base[r["k"]] + " (CPHF certificate, exact; ")
                                          for r in new)
        record("claim (%s): three VERIFIED rows on the families' stamps, builds_on with fuse-ckrs2010" % mode,
               code == 0 and len(new) == 3 and all(r["tier"] == "VERIFIED" and len(r["array_sha256"]) == 64
                                                   and r["builds_on"] == "cphf-smc2006;fuse-ckrs2010" for r in new)
               and stamps_ok, out[-300:])
        lst = list(csv.DictReader(open(os.path.join(tdir, "certificates", "CERTIFICATES.csv"))))[-3:]
        record("claim (%s): listings name the families' files, fused, with the rules" % mode,
               [x["file"] for x in lst] == ["CPHF_11_121_3_5.txt"] * 2 + ["CPHF_10_2876_4_3.txt"]
               and all(", fused: " in x["family"] for x in lst)
               and all(re.search(r"; fused array spot check: 10000 random \d-sets, uncovered 0, seed [0-9a-f]{16}$",
                                 x["check"]) for x in lst)
               and [x["expansion"] for x in lst] == ["smc-1+fuse2 2", "smc-1+fuse 2>0", "smc-1-affine+fuse2 3+fuse2 2"]
               and sorted(os.listdir(os.path.join(tdir, "certificates"))) == sorted(os.listdir(CERTS)), lst)
        pr = consistency_problems(root)
        record("claim (%s): consistency" % mode, not pr, "; ".join(pr[:3]))
        if mode == "local":
            a = os.path.join(tmp, "a.txt"); expand(exe, os.path.join(CERTS, "CPHF_11_121_3_5.txt"), 5, 3, False, a)
            code, h, err = fusestream(fz, a, 3, [["fuse2", "2"]])
            record("claim: array_sha256 is the hash of the fused array", new and new[0]["array_sha256"] == h, h)
            code, out = cert([sub, "--table-dir", tdir, "--threads", "2"])
            record("refused: a listing already in the table (after --apply)",
                   code == 1 and out.count("already in the table") == 3, out[-300:])

    # refused
    root = fresh(tmp); tdir = os.path.join(root, "table")
    sub = os.path.join(root, "submissions", "test-refused")
    os.makedirs(sub); shutil.copy(os.path.join(CERTS, "CPHF_11_121_3_5.txt"), os.path.join(sub, "fam.txt"))
    T = "table/certificates/CPHF_11_121_3_5.txt"
    cases = [("a family not in the table",
              fused_claim(5, 2, 121, 2661, "table/certificates/CPHF_1_2_3_4.txt", "smc-1+fuse2 2"), "not listed"),
             ("a file in the submission", fused_claim(5, 2, 121, 2661, "fam.txt", "smc-1+fuse2 2"),
              "by its file in the table"),
             ("a path out of the folder", fused_claim(5, 2, 121, 2661, "table/certificates/../ca_table.csv", "smc-1+fuse2 2"),
              "by its file in the table"),
             ("a mode", fused_claim(5, 2, 121, 2661, T, "smc-1+fuse2 2", "fullfast"), "takes no mode"),
             ("the wrong N", fused_claim(5, 2, 121, 2663, T, "smc-1+fuse2 2"), "gives CA(2661"),
             ("the wrong v", fused_claim(5, 3, 121, 2661, T, "smc-1+fuse2 2"), "gives CA(2661"),
             ("another base rule", fused_claim(5, 2, 121, 2661, T, "smc-1-affine+fuse2 2"), "must start with"),
             ("a step not removing the largest symbol", fused_claim(5, 2, 121, 2661, T, "smc-1+fuse2 1"), "largest symbol"),
             ("a rule without steps", fused_claim(5, 3, 121, 2663, T, "smc-1"), "no fusing step"),
             ("the wrong t", fused_claim(4, 2, 121, 2661, T, "smc-1+fuse2 2"), "the claim says t=4"),
             ("a listing already in the table", fused_claim(6, 4, 781, 249983, "table/certificates/CPHF_16_781_5_6.txt",
                                                            "smc-1+fuse2 4"), "already in the table")]
    for what, cl, want in cases:
        write_claims(sub, [cl])
        code, out = cert([sub, "--table-dir", tdir, "--light", "--out", os.path.join(root, "l")])
        record("refused: %s" % what, code == 1 and want in out, out[-300:])
    write_claims(sub, [fused_claim(5, 2, 121, 2661, T, "smc-1+fuse2 2"), fused_claim(5, 2, 121, 2661, T, "smc-1+fuse2 2")])
    code, out = cert([sub, "--table-dir", tdir, "--light", "--out", os.path.join(root, "l")])
    record("refused: a listing named twice", code == 1 and "named twice" in out, out[-300:])
    clist = os.path.join(tdir, "certificates", "CERTIFICATES.csv")
    text = open(clist).read()
    line = [l for l in text.splitlines() if l.startswith('"CPHF_11_121_3_5.txt"')][0]
    open(clist, "w").write(text.replace(line, line.replace(",\"repcheck", ",\"screened: repcheck").replace(
        ",\"cphfcheck", ",\"screened: cphfcheck")))
    write_claims(sub, [fused_claim(5, 2, 121, 2661, T, "smc-1+fuse2 2")])
    code, out = cert([sub, "--table-dir", tdir, "--light", "--out", os.path.join(root, "l")])
    record("refused: a family listed only as SCREENED", code == 1 and "with an exact check" in out, out[-300:])
    open(clist, "w").write(text)
    saved = cc.ARRAY_HASH_MAX_ENTRIES
    cc.ARRAY_HASH_MAX_ENTRIES = 1000
    try:
        code, out = cert([sub, "--table-dir", tdir, "--light", "--out", os.path.join(root, "l")])
    finally:
        cc.ARRAY_HASH_MAX_ENTRIES = saved
    record("refused: an array above the hash threshold", code == 1 and "not supported" in out, out[-300:])
    write_claims(sub, [dict(t=5, v=3, k=121, N=2663, file="fam.txt", mode="", source_detail="test",
                            construction="test CPHF", builds_on="cphf-smc2006", credit="Test Person", notes="")],
                 ck.HEADER)
    code, out = cert([sub, "--table-dir", tdir, "--light", "--out", os.path.join(root, "l")])
    record("unchanged: without the column, a family in the table is still a duplicate", code == 1 and "duplicate" in out,
           out[-300:])


if __name__ == "__main__":
    random.seed(1)
    sys.exit(main())
