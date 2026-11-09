#!/usr/bin/env python3
"""Tests of the check of a new counted row against table/derived.csv (CONVENTIONS.md section 6, version 1.4):
tools/check_submission.py flags a claim past the baseline's column range of its t and v that sets a new counted value
above a line of derived.csv at a width k' >= k ("above a published size rule"), lists it in the credit-check
section, and says how many frame lines a claim past the counted range would let in; tools/consistency.py reports
every such row, on every run, as a ::warning:: (never a problem) unless table/above_rule_rows.csv lists it.

Cases: an end-to-end submission on a small synthetic table (a flagged claim passes, with the flag in the summary,
the details and the credit check, and lets in no frame line; the same claim not beaten lets in two add1 lines; an
ordinary claim inside the range is not flagged); on the live table, the synthetic rows CA(1000; 3, 100000, 2) and
CA(2400; 2, 100000, 3) are flagged and let in no frame line; the one existing row above a size rule
(t6-v2-k10051-1) is on the list and does not warn; a pull request adding CA(1000; 3, 100000, 2) warns; a regenerated
derived.csv that comes to beat an existing row warns without --base; the list's format is checked; the frame line
count is the same with a relative --table-dir; past FRAME_EFFECT_MAX claims the count is not computed.

Usage: test_above_rule.py   (prints PASS/FAIL lines and a summary; exit 1 on a failure)
"""
import contextlib
import csv
import io
import os
import random
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "tools"))
import check_submission as cs  # noqa: E402
import consistency as cc  # noqa: E402
import build_frame as bf  # noqa: E402

RESULTS = {"pass": 0, "fail": 0}
LIVE = os.path.join(REPO, "table")
SNAP = "colbourn-2024-11-ug"


def check(cond, what):
    RESULTS["pass" if cond else "fail"] += 1
    print("%s  %s" % ("PASS" if cond else "FAIL", what), flush=True)
    return cond


def quiet(fn, *args):
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        try:
            return fn(*args)
        except SystemExit as e:
            return e.code if isinstance(e.code, int) else 2


def trow(t, v, k, n, tier="CITED", src="S1", snap=SNAP, sha="", entered="2026-08-23", con=""):
    r = {h: "" for h in cs.TABLE_HEADER}
    r.update(t=str(t), v=str(v), k=str(k), N=str(n), tier=tier, source_id=src, source_detail="test row",
             snapshot_id=snap, array_sha256=sha, entered=entered, construction=con or "label %d-%d-%d" % (t, v, k))
    if tier == "VERIFIED":
        r["verify_stamp"] = "ca_verify test 2026-11-09 Linux"
    return r


def small_table(d, derived):
    """a copy of table/ without the arrays, with a ca_table.csv of two baseline rows at (3, 2) (k = 4 and 10), an
    empty MANIFEST.csv and the given derived.csv lines"""
    for name in os.listdir(LIVE):
        p = os.path.join(LIVE, name)
        if name in ("arrays", "ca_table.csv", "MANIFEST.csv", "derived.csv") or name.endswith(".md"):
            continue
        (shutil.copytree if os.path.isdir(p) else shutil.copyfile)(p, os.path.join(d, name))
    os.makedirs(os.path.join(d, "arrays"))
    with open(os.path.join(d, "ca_table.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, cs.TABLE_HEADER, lineterminator="\r\n")
        w.writeheader()
        w.writerows([trow(3, 2, 4, 8), trow(3, 2, 10, 12)])
    with open(os.path.join(d, "MANIFEST.csv"), "w", encoding="utf-8", newline="") as f:
        f.write(",".join('"%s"' % h for h in cs.MANIFEST_HEADER) + "\n")
    with open(os.path.join(d, "derived.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(cc.DERIVED_HEADER)
        w.writerows([t, v, k, n, "", "", law, "test", 1] for t, v, k, n, law in derived)


def random_ca(rng, cav, N, t, k, v, tmp):
    path = os.path.join(tmp, "try.txt")
    while True:
        rows = [[rng.randrange(v) for _ in range(k)] for _ in range(N)]
        with open(path, "w") as f:
            f.write(cs.canon_serialize(rows))
        if subprocess.run([cav, path, str(t), str(v), "2"], stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL).returncode == 0:
            return rows


def submit(W, TD, cav, name, arrays, cwd=None):
    """a submission directory with one claim per (t, v, k, N, rows); returns (rc, report text, summary)"""
    S = os.path.join(W, name)
    os.makedirs(S)
    open(os.path.join(S, "HOW.md"), "w").write("Construction: test array\nBuilt from: nothing\nProgram: this test\n")
    with open(os.path.join(S, "claims.csv"), "w") as f:
        f.write(",".join(cs.CLAIMS_HEADER) + "\n")
        for i, (t, v, k, N, rows) in enumerate(arrays):
            fn = "a%d.txt" % i
            with open(os.path.join(S, fn), "w") as g:
                g.write(cs.canon_serialize(rows))
            f.write("%d,%d,%d,%d,%s,test recipe,random search test,new https://example.org/x,Test Person,\n"
                    % (t, v, k, N, fn))
    out = os.path.join(W, name + "-out")
    old = os.getcwd()
    if cwd:
        os.chdir(cwd)
    try:
        rc = quiet(cs.main, [S, "--table-dir", TD, "--ca-verify", cav, "--threads", "2", "--out", out,
                             "--credit-offline", "--date", "2026-11-09"])
    finally:
        os.chdir(old)
    import json
    return rc, open(os.path.join(out, "report.md")).read(), json.load(open(os.path.join(out, "summary.json")))


def test_submission_small():
    rng = random.Random(20261109)
    with tempfile.TemporaryDirectory(prefix="carule-") as W:
        cav = os.path.join(W, "ca_verify")
        subprocess.run(["cc", "-O3", "-pthread", "-o", cav, os.path.join(REPO, "ca_verify.c")], check=True)
        A = random_ca(rng, cav, 64, 3, 12, 2, W)        # past the baseline's range (k = 10) of (3, 2)
        B = random_ca(rng, cav, 40, 3, 8, 2, W)         # inside it
        TD = os.path.join(W, "t1")
        os.makedirs(TD)
        small_table(TD, [(3, 2, 15, 30, "PCT")])
        rc, rep, sm = submit(W, TD, cav, "s1", [(3, 2, 12, 64, A)])
        c = sm["claims"][0]
        check(rc == 0 and sm["passed"] and c["above_rule"] == [30, 15, "PCT"],
              "CA(64; 3, 12, 2) past the baseline's range, above PCT 30 at k' = 15: flagged, and the check still "
              "passes (a flag, not a failure)")
        check("**Result: PASS.** 1 of 1 claims passed. 1 claim flagged: above a published size rule" in rep,
              "the result line counts the flagged claim")
        check("above a size rule" in rep and "**above a published size rule: 64 vs PCT value 30 at k' = 15**, "
              "flagged for the maintainer" in rep,
              "the report shows the flag in the summary table and in the details")
        cred = rep[rep.index("### Credit check"):rep.index("### Details")]
        check("CA(64; 3, 12, 2)" in cred and "**above a published size rule**" in cred,
              "the credit-check section lists it")
        check(c["frame_effect"]["lines"] == 0 and "the counted range is not widened by it" in rep,
              "it lets in no frame line: the counted range is not widened (section 6, version 1.4)")
        rc, _, sm1 = submit(W, "t1", cav, "s1rel", [(3, 2, 12, 64, A)], cwd=W)
        check(rc == 0 and sm1["claims"][0]["frame_effect"]["lines"] == 0,
              "the same with a relative --table-dir, as the workflows pass it: no frame line (got %s)"
              % sm1["claims"][0]["frame_effect"])
        TD2 = os.path.join(W, "t2")
        os.makedirs(TD2)
        small_table(TD2, [(3, 2, 15, 70, "PCT"), (3, 2, 11, 14, "CK")])
        rc, rep, sm = submit(W, TD2, cav, "s2", [(3, 2, 12, 64, A)])
        c = sm["claims"][0]
        fe = c["frame_effect"]
        check(rc == 0 and c["above_rule"] is None and fe["lines"] == 2 and fe["N"] == [16, 20] and fe["above"] == 1
              and fe["derived"] == [14, 70],
              "not beaten at k' >= 12 (PCT 70): not flagged, and the report counts the 2 add1 lines it lets in (16 "
              "and 20), 1 of them above derived.csv (CK 14 at k' = 11)")
        rc, rep2, sm2 = submit(W, "t2", cav, "s2rel", [(3, 2, 12, 64, A)], cwd=W)
        fe2 = sm2["claims"][0]["frame_effect"]
        check(rc == 0 and fe2 == fe, "a relative --table-dir (as the workflows pass it) gives the same frame line "
              "count (%s)" % fe2)
        check("flagged" not in rep[:rep.index("Checked ")], "the result line has no flag when no claim is flagged")
        check("the frame gains 2 derived lines (N 16 to 20 at t = 3, v = 2), 1 of them above a line of "
              "table/derived.csv" in rep, "the report says so")
        rc, rep, sm = submit(W, TD, cav, "s3", [(3, 2, 8, 40, B)])
        c = sm["claims"][0]
        check(rc == 0 and c["above_rule"] is None and not c.get("frame_effect") and "above a published" not in rep,
              "an ordinary claim inside the range is not flagged and gets no frame line count")
        ctx = dict(table_rows=list(csv.DictReader(open(os.path.join(TD, "ca_table.csv"), newline=""))), table_dir=TD)
        check(cs.above_rule_flag(ctx, 3, 2, 8, 11) is None and cs.above_rule_flag(ctx, 3, 2, 11, 31) == (30, 15, "PCT"),
              "inside the baseline's range never flagged (even below derived.csv's width); past it, above it is")


def live_claim(t, v, k, N):
    return dict(passed=True, comparison="exceeds_table", previous_best=None, t=t, v=v, k=k, N=N, sha256="ab" * 32,
                raw=dict(construction="test row", file="x.txt"), line=2)


def test_submission_live():
    rows = list(csv.DictReader(open(os.path.join(LIVE, "ca_table.csv"), newline="", encoding="utf-8")))
    ctx = dict(table_rows=rows, table_dir=LIVE, slug="test", stamp="ca_verify test", date="2026-11-09")
    w1 = cs.above_rule_flag(ctx, 3, 2, 100000, 1000)
    w2 = cs.above_rule_flag(ctx, 2, 3, 100000, 2400)
    w3 = cs.above_rule_flag(ctx, 2, 25, 100000, 2425)
    check(w1 and w1[0] < 100 and w2 and w2[0] < 60 and w3 is None,
          "live: CA(1000; 3, 100000, 2) (%s) and CA(2400; 2, 100000, 3) (%s) are flagged; CA(2425; 2, 100000, 25) "
          "is not (DP2 gives 2448)" % (w1, w2))
    cl = [live_claim(3, 2, 100000, 1000), live_claim(2, 3, 100000, 2400)]
    for c, w in zip(cl, (w1, w2)):
        c["above_rule"] = w
    cs.frame_effect(cl, ctx)
    check([c["frame_effect"]["lines"] for c in cl] == [0, 0],
          "live: neither lets a derived line into the frame (version 1.3 let in 231 lines of 80 to 996, and 8 of "
          "209 to 266)")


def test_consistency():
    rows = list(csv.DictReader(open(os.path.join(LIVE, "ca_table.csv"), newline="", encoding="utf-8")))
    ab = cc.above_rule_rows(rows, LIVE)
    check([x[1] for x in ab] == ["t6-v2-k10051-1"] and ab[0][2][:2] == (6555, 11000),
          "live: one counted row past the baseline's range is above a size rule: CA(6580; 6, 10051, 2), PCT 6555 "
          "at k' = 11000 (got %s)" % [(x[1], x[2]) for x in ab])
    pos = ab[0][0]
    del cc.problems[:]
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        r = cc.check_above_rule(rows, pos, LIVE)
    check(r == (0, 1) and "::warning::" not in out.getvalue() and not cc.problems,
          "the listed row (table/above_rule_rows.csv) does not warn, even when counted as added")
    with contextlib.redirect_stdout(out):
        r0 = cc.check_above_rule(rows, None, LIVE)
    check(r0 == (0, 1) and not cc.problems, "without --base every row is checked; the listed row does not warn")
    new = dict(trow(3, 2, 100000, 1000, "VERIFIED", "S7", "", "ab" * 32, "2026-11-09"))
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        r = cc.check_above_rule(rows + [new], len(rows), LIVE)
    w = [l for l in out.getvalue().splitlines() if l.startswith("::warning::")]
    check(r == (1, 1) and len(w) == 1 and "t3-v2-k100000-1" in w[0] and "1000 vs PCT value" in w[0] and not cc.problems,
          "a pull request adding CA(1000; 3, 100000, 2) gets one ::warning:: and no problem")
    with tempfile.TemporaryDirectory() as d:
        for f in ("derived.csv",):
            os.symlink(os.path.join(LIVE, f), os.path.join(d, f))
        with contextlib.redirect_stdout(io.StringIO()) as o:
            r = cc.check_above_rule(rows, pos, d)
        check(r == (1, 0) and not cc.problems, "without the list, the same row warns")
        with contextlib.redirect_stdout(io.StringIO()) as o:
            r = cc.check_above_rule(rows, None, d)
        check(r == (1, 0) and "::warning::" in o.getvalue() and "added row" not in o.getvalue() and not cc.problems,
              "without --base too (every run on main), named as a row, not an added row")
        with open(os.path.join(d, "above_rule_rows.csv"), "w") as f:
            f.write("id,reason,decided_by,date\nt9-v2-k1-1,x,y,2026-11-09\nt6-v2-k10051-1,,y,2026\n")
        with contextlib.redirect_stdout(io.StringIO()):
            cc.check_above_rule(rows, pos, d)
        check(len(cc.problems) == 2 and "not the id of a row" in cc.problems[0] and "required" in cc.problems[1],
              "the list's format is checked: an unknown id, a missing reason or a bad date is a problem")
    del cc.problems[:]
    # drift: a regenerated derived.csv with a line beating an existing wide row
    wide = [x for x in rows if (x["t"], x["v"], x["k"]) == ("3", "4", "100000")]
    with tempfile.TemporaryDirectory() as d:
        shutil.copyfile(os.path.join(LIVE, "derived.csv"), os.path.join(d, "derived.csv"))
        shutil.copyfile(os.path.join(LIVE, "above_rule_rows.csv"), os.path.join(d, "above_rule_rows.csv"))
        n = min(int(x["N"]) for x in wide) if wide else None
        with open(os.path.join(d, "derived.csv"), "a", newline="") as f:
            csv.writer(f, lineterminator="\n").writerow([3, 4, 100000, (n or 2) - 1, "", "", "PCT", "test", 1])
        with contextlib.redirect_stdout(io.StringIO()) as o:
            r = cc.check_above_rule(rows, None, d)
        check(wide and r[0] >= 1 and "::warning::" in o.getvalue() and not cc.problems,
              "drift: a derived.csv line below the existing CA(%s; 3, 100000, 4) warns on a run without --base" % n)
    del cc.problems[:]


def test_frame_effect_cap():
    rows = list(csv.DictReader(open(os.path.join(LIVE, "ca_table.csv"), newline="", encoding="utf-8")))
    ctx = dict(table_rows=rows, table_dir=LIVE, slug="test", stamp="ca_verify test", date="2026-11-09")
    old = cs.FRAME_EFFECT_MAX
    cs.FRAME_EFFECT_MAX = 1
    try:
        cl = [live_claim(3, 2, 100000, 1000), live_claim(2, 3, 100000, 2400)]
        cs.frame_effect(cl, ctx)
    finally:
        cs.FRAME_EFFECT_MAX = old
    check(cl[0]["frame_effect"].get("lines") == 0 and "more than 1 claims" in cl[1]["frame_effect"].get("error", "")
          and "not computed" in cs.frame_effect_text(cl[1]),
          "past FRAME_EFFECT_MAX claims the frame line count is not computed, and the report says so")


def main():
    for fn in (test_consistency, test_submission_live, test_frame_effect_cap, test_submission_small):
        fn()
    print("%d passed, %d failed" % (RESULTS["pass"], RESULTS["fail"]))
    return 1 if RESULTS["fail"] else 0


if __name__ == "__main__":
    sys.exit(main())
