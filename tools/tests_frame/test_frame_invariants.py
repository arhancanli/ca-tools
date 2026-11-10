#!/usr/bin/env python3
"""Invariants of the live frame file table/ca_frame.csv: what must hold however the table grows.

These tests read the live table/ but assert no size, id or count of it. A new row can make any value of the
frame smaller and add lines; none of that can make these tests fail. (Tests that assert particular values
read the fixed fixture table in tools/tests_frame/fixtures instead; test_no_live_pins.py checks that.)

  I1 regeneration: tools/build_frame.py rebuilds table/ca_frame.csv and table/ca_table.csv.gz byte for
     byte from the committed table (as consistency.py checks on main); with --slow also table/derived.csv
     (tools/derive_table.py --check, several minutes)
  I2 no lookup gets worse: for every line (t, v, k, N) of the frame at a base commit, the frame's lookup now
     at (t, v, k) (the smallest N of a line at the same t and v with k' >= k) exists and is at most N. Only
     sizes are compared, so the "generated" column and changes of credit or wording never count. A loss
     decided on purpose (a retracted array, a rule withdrawn) is listed in
     tools/tests_frame/allowed_frame_regressions.csv (t, v, k, N_before, N_after, reason, decided_by, date).
     The base is --base COMMIT, else FRAME_BASE, else the first parent of HEAD; skipped (with a note)
     when the base has no frame or is not in the clone.
  I3 a stair step: at each t and v the lines have strictly increasing k and strictly increasing N, so the
     lookup never goes down as k grows (and never goes up as k shrinks)
  I4 the frame is never above the counted rows: at the width of every counted row the lookup is at most
     its N
  I5 past the counted range (CONVENTIONS.md section 6, versions 1.3 and 1.4): no derived line has a line of
     derived.csv below it at a width k' >= k by any rule (consistency.py check_frame_veto), and no line, row
     or derived, is above a line of derived.csv by a counted rule (fuse, derive, add1) unless it is a row
     listed in table/above_rule_rows.csv
  I6 every id, prev_id and every id in ids_all (split at ";" and "+") is the id of a row of ca_table.csv

Usage: test_frame_invariants.py [--base COMMIT] [--slow]   (PASS/FAIL lines and a summary; exit 1 on a failure)
"""
import argparse
import bisect
import collections
import contextlib
import csv
import io
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
TABLE = os.path.join(REPO, "table")
sys.path.insert(0, os.path.join(REPO, "tools"))
sys.path.insert(0, TABLE)
import build_frame as bf  # noqa: E402
from ca_table import counted  # noqa: E402

ALLOWED = os.path.join(HERE, "allowed_frame_regressions.csv")
ALLOWED_HEADER = ["t", "v", "k", "N_before", "N_after", "reason", "decided_by", "date"]
COUNTED_LAWS = ("fuse", "derive", "add1")     # the size rules the frame counts (CONVENTIONS.md section 6)
RESULTS = {"pass": 0, "fail": 0}


def check(cond, what, detail=()):
    RESULTS["pass" if cond else "fail"] += 1
    print("%s  %s" % ("PASS" if cond else "FAIL", what), flush=True)
    if not cond:
        for d in list(detail)[:20]:
            print("      %s" % (d,))
    return cond


def note(what):
    print("NOTE  %s" % what, flush=True)


def read(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def git(*args):
    return subprocess.run(["git", "-C", REPO] + list(args), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)


def lookup_table(lines):
    """{(t, v): (ks, suf)}: the frame's stair step lookup (smallest N at k' >= k)"""
    pts = collections.defaultdict(dict)
    for l in lines:
        tv, k, n = (int(l["t"]), int(l["v"])), int(l["k"]), int(l["N"])
        pts[tv][k] = min(n, pts[tv].get(k, bf.INF))
    out = {}
    for tv, p in pts.items():
        ks = sorted(p)
        suf, m = [0] * len(ks), bf.INF
        for i in range(len(ks) - 1, -1, -1):
            m = min(m, p[ks[i]])
            suf[i] = m
        out[tv] = (ks, suf)
    return out


def look(lk, tv, k):
    ks, suf = lk.get(tv, ((), ()))
    i = bisect.bisect_left(ks, k)
    return suf[i] if i < len(ks) else None


def test_regeneration(slow):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = bf.main(["--table-dir", TABLE, "--check"])
    check(rc == 0, "I1 tools/build_frame.py rebuilds table/ca_frame.csv and table/ca_table.csv.gz byte for byte",
          out.getvalue().splitlines())
    if slow:
        p = subprocess.run([sys.executable, os.path.join(REPO, "tools", "derive_table.py"), "--check"],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        check(p.returncode == 0, "I1 tools/derive_table.py rebuilds table/derived.csv byte for byte",
              p.stdout.splitlines()[-3:])


def allowed_regressions():
    if not os.path.exists(ALLOWED):
        return {}, ["%s is missing" % ALLOWED]
    raw = open(ALLOWED, encoding="utf-8").read().splitlines()
    bad = [] if raw and raw[0] == ",".join(ALLOWED_HEADER) else ["%s: header is not %s" % (ALLOWED, ",".join(ALLOWED_HEADER))]
    out = {}
    for i, a in enumerate(read(ALLOWED), 2):
        if not all((a.get(c) or "").strip() for c in ("t", "v", "k", "N_before", "reason", "decided_by", "date")) \
                or not re.match(r"^\d{4}-\d\d-\d\d$", a["date"]):
            bad.append("%s line %d: t, v, k, N_before, reason, decided_by and a date YYYY-MM-DD are required" % (ALLOWED, i))
            continue
        out[(int(a["t"]), int(a["v"]), int(a["k"]), int(a["N_before"]))] = a["N_after"].strip()
    return out, bad


def worse_list(old, lines, allowed):
    """the lines of the old frame whose lookup in lines is worse or gone, less the allowed ones"""
    lk = lookup_table(lines)
    worse = []
    for l in old:
        t, v, k, n = int(l["t"]), int(l["v"]), int(l["k"]), int(l["N"])
        now = look(lk, (t, v), k)
        if now is None or now > n:
            a = allowed.get((t, v, k, n))
            if a is not None and (a == "" or (now is not None and a == str(now))):
                continue
            worse.append("t=%d v=%d k=%d: %d at the base, %s now" % (t, v, k, n, "no value" if now is None else now))
    return worse


def test_no_worse(lines, base):
    allowed, bad = allowed_regressions()
    check(not bad, "I2 the list of allowed regressions is well formed", bad)
    if base is None:
        p = git("rev-parse", "--verify", "-q", "HEAD^")
        base = p.stdout.decode().strip() if p.returncode == 0 else None
    if not base:
        note("I2 skipped: no base commit (a clone with one commit; pass --base)")
        return
    p = git("show", "%s:table/ca_frame.csv" % base)
    if p.returncode != 0:
        note("I2 skipped: no table/ca_frame.csv at the base %s (or the base is not in this clone)" % base)
        return
    old = list(csv.DictReader(io.StringIO(p.stdout.decode("utf-8"))))
    worse = worse_list(old, lines, allowed)
    check(not worse, "I2 no frame lookup is worse than at the base %s or gone (%d base lines compared, %d worse)"
          % (base[:12], len(old), len(worse)), worse)


def stair_bad(lines):
    by = collections.defaultdict(list)
    for l in lines:
        by[(int(l["t"]), int(l["v"]))].append((int(l["k"]), int(l["N"])))
    bad = []
    for tv, lst in sorted(by.items()):
        for (k1, n1), (k2, n2) in zip(lst, lst[1:]):
            if not (k2 > k1 and n2 > n1):
                bad.append("t=%d v=%d: k=%d N=%d then k=%d N=%d" % (tv + (k1, n1, k2, n2)))
    return bad, by


def test_stair(lines):
    bad, by = stair_bad(lines)
    check(not bad, "I3 at every t and v, k and N strictly increase down the frame (%d pairs (t, v))" % len(by), bad)


def test_not_above_rows(lines, rows):
    lk = lookup_table(lines)
    bad = []
    for r in counted(rows):
        t, v, k, n = int(r["t"]), int(r["v"]), int(r["k"]), int(float(r["N"]))
        now = look(lk, (t, v), k)
        if now is None or now > n:
            bad.append("t=%d v=%d k=%d: counted row N=%d, frame %s" % (t, v, k, n, now))
    check(not bad, "I4 at the width of every counted row the frame's lookup is at most its N", bad)


def test_past_range(lines, rows):
    import consistency as cc
    del cc.problems[:]
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        n, bad = cc.check_frame_veto(rows, table_dir=TABLE)
    check(bad == 0 and not cc.problems, "I5 consistency.py: past the counted range no derived line is above derived.csv "
          "(%d lines checked)" % n, cc.problems)
    del cc.problems[:]
    # by a counted rule: every line, row or derived
    pts = collections.defaultdict(dict)
    for d in read(os.path.join(TABLE, "derived.csv")):
        if d["law"] in COUNTED_LAWS:
            tv, k, x = (int(d["t"]), int(d["v"])), int(d["k"]), int(d["N"])
            pts[tv][k] = min(x, pts[tv].get(k, bf.INF))
    floor = {}
    for tv, p in pts.items():
        ks = sorted(p)
        suf, m = [0] * len(ks), bf.INF
        for i in range(len(ks) - 1, -1, -1):
            m = min(m, p[ks[i]])
            suf[i] = m
        floor[tv] = (ks, suf)
    kmax, _ = bf.counted_range(rows, counted(rows), bf.derived_floor(TABLE))
    listed = {a["id"] for a in read(os.path.join(TABLE, "above_rule_rows.csv"))} \
        if os.path.exists(os.path.join(TABLE, "above_rule_rows.csv")) else set()
    bad, n = [], 0
    for l in lines:
        tv, k, x = (int(l["t"]), int(l["v"])), int(l["k"]), int(l["N"])
        if k <= kmax[tv]:
            continue
        n += 1
        low = bf.floor_at(floor, tv, k)
        if low < x and not (l["basis"] == "row" and l["id"] in listed):
            bad.append("t=%d v=%d k=%d N=%d (%s %s): a counted rule in derived.csv gives %d at a width k' >= k"
                       % (tv + (k, x, l["basis"], l["id"] or l["construction"], low)))
    check(not bad, "I5 past the counted range no frame line is above a counted rule (fuse, derive, add1) of "
          "derived.csv, except rows listed in table/above_rule_rows.csv (%d lines past the range)" % n, bad)


def ids_bad(lines, rows):
    ids = set(bf.row_ids(rows))
    bad = []
    for l in lines:
        named = [l["id"], l["prev_id"]] + [x for part in l["ids_all"].split(";") for x in part.split("+")]
        for x in named:
            if x and x not in ids:
                bad.append("t=%s v=%s k=%s: %s is not a row id" % (l["t"], l["v"], l["k"], x))
        if l["basis"] == "row" and not l["id"]:
            bad.append("t=%s v=%s k=%s: a row line without an id" % (l["t"], l["v"], l["k"]))
        if not l["ids_all"]:
            bad.append("t=%s v=%s k=%s: ids_all is empty" % (l["t"], l["v"], l["k"]))
    return bad


def test_ids(lines, rows):
    bad = ids_bad(lines, rows)
    check(not bad, "I6 every id, prev_id and id in ids_all of the frame is a row of ca_table.csv (%d lines)" % len(lines), bad)


def test_selftest(lines, rows):
    """the checks above catch a planted fault (on copies; the files are not touched)"""
    import copy
    i = max(range(len(lines)), key=lambda j: int(lines[j]["N"]) if lines[j]["basis"] == "row" else -1)
    worse = copy.deepcopy(lines)
    worse[i]["N"] = str(int(worse[i]["N"]) + 1)
    gone = [l for j, l in enumerate(lines) if j != i]
    w1, w2 = worse_list(lines, worse, {}), worse_list(lines, gone, {})
    l = lines[i]
    allowed = {(int(l["t"]), int(l["v"]), int(l["k"]), int(l["N"])): str(int(l["N"]) + 1)}
    check(len(w1) == 1 and len(w2) >= 1 and worse_list(lines, worse, allowed) == []
          and worse_list(lines, lines, {}) == [],
          "selftest: I2 catches a lookup made worse by one and a line removed, and honours the allowed list")
    j = next(j for j in range(1, len(lines)) if (lines[j]["t"], lines[j]["v"]) == (lines[j - 1]["t"], lines[j - 1]["v"]))
    flat = copy.deepcopy(lines)
    flat[j]["N"] = flat[j - 1]["N"]
    check(len(stair_bad(flat)[0]) == 1, "selftest: I3 catches two lines with the same N")
    bogus = copy.deepcopy(lines)
    bogus[i]["ids_all"] += ";t9-v2-k1-1"
    check(len(ids_bad(bogus, rows)) == 1, "selftest: I6 catches an id in ids_all that is no row")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--base", default=os.environ.get("FRAME_BASE") or None)
    ap.add_argument("--slow", action="store_true", help="also regenerate table/derived.csv (several minutes)")
    a = ap.parse_args(argv)
    rows = read(os.path.join(TABLE, "ca_table.csv"))
    lines = read(os.path.join(TABLE, "ca_frame.csv"))
    test_regeneration(a.slow)
    test_no_worse(lines, a.base)
    test_stair(lines)
    test_not_above_rows(lines, rows)
    test_past_range(lines, rows)
    test_ids(lines, rows)
    test_selftest(lines, rows)
    print("%d passed, %d failed" % (RESULTS["pass"], RESULTS["fail"]))
    return 1 if RESULTS["fail"] else 0


if __name__ == "__main__":
    sys.exit(main())
