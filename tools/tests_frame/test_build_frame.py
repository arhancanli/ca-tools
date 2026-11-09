#!/usr/bin/env python3
"""Tests of tools/build_frame.py (table/ca_frame.csv) on small synthetic tables.

Each case writes a ca_table.csv (and, where needed, MANIFEST.csv and withdrawn_files.csv) into a
temporary directory and builds the frame there. Assertions: fuse and derive chains and their
workings, the tier of a derived step (its source row's), a derived size equal to a row is not a
derived step, no derived size from a CITED row with a DISPUTED row beside it or from a retracted
row, ids stable when rows are appended, prev_id for row steps and derived steps, the stair steps
(one line per step, dominated rows dropped), the headline among ties, get from MANIFEST and
withdrawn files, get lent by a tied VERIFIED row when the named row has none, workings in the
label form (source label, then :fuse/:derive/:add1; labels with colons and commas), the comparison with
derived.csv past the counted range (issue #62: a fused size withheld where any size rule gives less, kept
where none does, the consistency.py check of it, prev_id of a past-range step below the widest counted
value, the live frame at (3, 2), (3, 3) and (3, 10), a strength-2 row CA(2425; 2, 100000, 25)), a row past the
baseline's range that derived.csv beats at its own width does not widen the counted range (version 1.4: on the
live table a CA(1000; 3, 100000, 2) lets in no derived line), add1 (CKRS 2010
Theorem 3.2: two inputs, the weaker tier, both rows in ids_all, chains, t = 3 with the trivial strength 1
ingredient, inside the counted range only, fuse before add1, a sound chain cut, a VERIFIED ingredient before
a CITED one of the same size, the consistency check of add1 workings), a .txt.gz path in a document and a
RETRACTED row with a SCREENED twin (consistency.py), Colbourn's 133 "Add 1 factors"
rows reproduced from their ingredients in the live table, the live withdrawn_files.csv against
withdrawn_fingerprints.csv, and --check.

Usage: test_build_frame.py   (prints PASS/FAIL lines and a summary; exit 1 on a failure)
"""
import csv
import gzip
import io
import os
import re
import sys
import tempfile
import contextlib

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "tools"))
import build_frame as bf  # noqa: E402

RESULTS = {"pass": 0, "fail": 0}
HEADER = ["t", "v", "k", "N", "tier", "source_id", "source_detail", "snapshot_id", "array_sha256",
          "verify_stamp", "entered", "notes", "lb", "lb_evidence", "construction", "builds_on", "family_sha256"]
SNAP = "colbourn-2024-11-ug"


def check(cond, what):
    RESULTS["pass" if cond else "fail"] += 1
    print("%s  %s" % ("PASS" if cond else "FAIL", what), flush=True)
    return cond


def row(t, v, k, n, tier="CITED", src="S1", snap=SNAP, sha="", entered="2026-08-23", con="", stamp=""):
    if tier == "VERIFIED" and not stamp:
        stamp = "ca_verify test 2026-11-01 Linux"
    return {"t": t, "v": v, "k": k, "N": n, "tier": tier, "source_id": src, "source_detail": "test " + (con or "row"),
            "snapshot_id": snap, "array_sha256": sha, "verify_stamp": stamp, "entered": entered, "notes": "",
            "lb": "", "lb_evidence": "", "construction": con or ("label %d-%d-%d" % (t, v, k)), "builds_on": "",
            "family_sha256": ""}


DERIVED_HEADER = ["t", "v", "k", "N", "lookup_N", "gain_pct", "law", "arithmetic", "round"]


def write_table(d, rows, manifest=(), withdrawn=(), derived=()):
    if derived:
        with open(os.path.join(d, "derived.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(DERIVED_HEADER)
            w.writerows([t, v, k, n, "", "", law, "test", 1] for t, v, k, n, law in derived)
    with open(os.path.join(d, "ca_table.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, HEADER, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    if manifest:
        with open(os.path.join(d, "MANIFEST.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(["file", "t", "v", "k", "N", "status", "sha256", "source_id", "source_detail",
                        "verify_stamp", "constant_rows"])
            w.writerows(manifest)
    if withdrawn:
        with open(os.path.join(d, "withdrawn_files.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(["file", "t", "v", "k", "N", "status", "sha256", "source_id", "source_detail",
                        "verify_stamp", "constant_rows", "withdrawn", "reason"])
            w.writerows(withdrawn)


def frame(rows, **kw):
    with tempfile.TemporaryDirectory() as d:
        write_table(d, rows, **kw)
        lines, stats, ctx = bf.build(d)
    return [dict(zip(bf.FRAME_HEADER, l)) for l in lines], stats


def at(fr, t, v):
    return [l for l in fr if (l["t"], l["v"]) == (str(t), str(v))]


def one(fr, t, v, k):
    x = [l for l in fr if (l["t"], l["v"], l["k"]) == (str(t), str(v), str(k))]
    return x[0] if len(x) == 1 else None


def test_fuse_chain():
    fr, _ = frame([row(3, 5, 20, 100, "VERIFIED", "S7", "", "a" * 64, "2026-11-01", con="RMScopiesCA")])
    l4, l2 = one(fr, 3, 4, 20), one(fr, 3, 2, 20)
    check(l4 and l4["N"] == "98" and l4["basis"] == "derived" and l4["construction"] == "RMScopiesCA:fuse",
          "fuse once: CA(100; 3, 20, 5) gives 98 at v = 4, working RMScopiesCA:fuse (the source's label)")
    check(l2 and l2["N"] == "94" and l2["construction"] == "RMScopiesCA:fuse:fuse:fuse"
          and l2["constructions_all"] == "RMScopiesCA:fuse:fuse:fuse",
          "fuse three times: 94 at v = 2, working RMScopiesCA:fuse:fuse:fuse")
    check(l4 and l4["tier"] == "VERIFIED" and l4["id"] == "" and l4["get"] == "none" and l4["get_ref"] == ""
          and l4["ids_all"] == "t3-v5-k20-1" and l4["entered"] == "2026-11-01",
          "a derived step from a VERIFIED row: tier VERIFIED, no id, get none, source in ids_all, its entry date")


def test_derive_chain():
    # counted rows wider than k = 21 at the target pairs keep the points in the counted range
    fr, _ = frame([row(4, 3, 21, 300), row(3, 3, 30, 900), row(3, 2, 30, 900), row(2, 3, 30, 900)])
    l = one(fr, 3, 3, 20)
    check(l and l["N"] == "100" and l["construction"] == "label 4-3-21:derive" and l["tier"] == "CITED"
          and l["ids_all"] == "t4-v3-k21-1",
          "derive: floor(300 / 3) = 100 at (3, 3, 20) from a CITED row, tier CITED")
    l = one(fr, 3, 2, 20)
    check(l and l["N"] == "98" and l["construction"] == "label 4-3-21:derive:fuse",
          "derive then fuse: 98 at (3, 2, 20), working label 4-3-21:derive:fuse")
    l = one(fr, 2, 3, 19)
    check(l and l["N"] == "33" and l["construction"] == "label 4-3-21:derive:derive",
          "derive twice: floor(100 / 3) = 33 at (2, 3, 19)")
    # fuse then derive is also tried: (4,3,21,300) -> (4,2,21,298) -> (3,2,20,149) is worse than 98
    l = one(fr, 3, 2, 20)
    check(l and l["constructions_all"] == "label 4-3-21:derive:fuse", "only the smallest working is listed")


def test_tier_of_weakest_and_ties():
    rows = [row(3, 5, 20, 100, con="cited label"),
            row(3, 5, 20, 100, "VERIFIED", "S7", "", "b" * 64, "2026-11-02", con="our label")]
    fr, _ = frame(rows)
    l = one(fr, 3, 4, 20)
    check(l and l["tier"] == "CITED" and l["construction"] == "cited label:fuse"
          and l["constructions_all"] == "cited label:fuse || our label:fuse"
          and l["ids_all"] == "t3-v5-k20-1;t3-v5-k20-2",
          "two sources reach the same derived size: the CITED source is named (section 9), both listed")
    l = one(fr, 3, 5, 20)
    check(l and l["basis"] == "row" and l["id"] == "t3-v5-k20-1" and l["ids_all"] == "t3-v5-k20-1;t3-v5-k20-2",
          "a CITED and a VERIFIED row tie: the CITED row is named, both in ids_all")


def test_equal_is_row():
    fr, _ = frame([row(3, 5, 20, 100), row(3, 4, 20, 98, "VERIFIED", "S7", "", "c" * 64)])
    l = one(fr, 3, 4, 20)
    check(l and l["basis"] == "row" and l["id"] == "t3-v4-k20-1",
          "a derived size equal to a counted row is not a derived step: the row is named")


def test_disputed_excluded():
    rows = [row(3, 6, 128, 762, con="cyclotomy"), row(3, 7, 50, 400),
            dict(row(3, 6, 128, 762, "DISPUTED", "S6", ""), notes="fails as published")]
    fr, _ = frame(rows)
    check(one(fr, 3, 6, 128) and one(fr, 3, 6, 128)["basis"] == "row",
          "the disputed CITED row stays a counted step")
    check(one(fr, 3, 5, 128) is None and not any("t3-v6-k128-1" in l["ids_all"] or "cyclotomy:" in
                                                  l["construction"] for l in fr if l["basis"] == "derived"),
          "no derived size from a CITED row with a DISPUTED row beside it")
    l = one(fr, 3, 6, 50)
    check(l and l["N"] == "398" and l["construction"] == "label 3-7-50:fuse" and l["ids_all"] == "t3-v7-k50-1",
          "other rows at the same (t, v) still give derived sizes")
    check(all(l["tier"] in ("CITED", "VERIFIED") for l in fr), "no DISPUTED line in the frame")


def test_retracted_excluded():
    sha = "d" * 64
    rows = [row(3, 5, 20, 100, "VERIFIED", "S7", "", sha),
            row(3, 5, 20, 100, "RETRACTED", "S7", "", sha), row(3, 5, 30, 200)]
    fr, _ = frame(rows)
    check(one(fr, 3, 5, 20) is None and one(fr, 3, 4, 20) is None,
          "a retracted VERIFIED row is neither a step nor an input")


def test_steps():
    rows = [row(2, 3, 5, 10), row(2, 3, 7, 10), row(2, 3, 6, 12), row(2, 3, 9, 15), row(2, 3, 4, 11)]
    fr, st = frame(rows)
    got = [(l["k"], l["N"]) for l in at(fr, 2, 3)]
    check(got == [("7", "10"), ("9", "15")],
          "one line per step: (k, N) with N smallest at k' >= k and k largest with it (got %s)" % got)
    # a derived size that dominates a row step removes it
    rows = [row(3, 4, 10, 60), row(3, 4, 12, 70), row(3, 5, 12, 66, "VERIFIED", "S7", "", "e" * 64)]
    fr, st = frame(rows)
    got = [(l["k"], l["N"], l["basis"]) for l in at(fr, 3, 4)]
    check(got == [("10", "60", "row"), ("12", "64", "derived")],
          "a derived step replaces the row step it beats (got %s)" % got)
    check(st["changed"] == st["derived"] and st["derived"] >= 1,
          "every step that differs from the Colbourn rule is a derived step (%d of %d)" % (st["changed"], st["derived"]))


def test_ids_stable():
    base = [row(3, 4, 10, 60), row(3, 4, 12, 70), row(2, 2, 5, 6)]
    fr1, _ = frame(base)
    more = base + [row(3, 4, 10, 59, "VERIFIED", "S7", "", "f" * 64, "2026-11-05"), row(3, 4, 12, 70, "VERIFIED", "S7", "",
                                                                                     "1" * 64, "2026-11-05")]
    fr2, _ = frame(more)
    check(bf.row_ids(base) == bf.row_ids(more)[:len(base)], "appending rows leaves every earlier id unchanged")
    check(bf.row_ids(more)[3:] == ["t3-v4-k10-2", "t3-v4-k12-2"], "new rows at known points get the next number")
    l1, l2 = one(fr1, 3, 4, 12), one(fr2, 3, 4, 12)
    check(l1["id"] == l2["id"] == "t3-v4-k12-1" and l2["ids_all"] == "t3-v4-k12-1;t3-v4-k12-2",
          "an unchanged step keeps its id; the tied newcomer is listed after it")
    l2 = one(fr2, 3, 4, 10)
    check(l2["id"] == "t3-v4-k10-2" and l2["prev_id"] == "t3-v4-k10-1", "an improved step names the new row")
    check(all(bf.ID_RE.match(l["id"]) for l in fr2 if l["id"]), "ids follow the grammar t3-v13-k197-1")


def test_prev_id():
    rows = [row(2, 3, 20, 15), row(2, 3, 10, 13), row(2, 3, 5, 11),       # baseline, in no order
            row(2, 3, 10, 12, "VERIFIED", "S7", "", "2" * 64, "2026-11-01"),
            row(2, 3, 10, 11, "VERIFIED", "S7", "", "3" * 64, "2026-11-02")]
    fr, _ = frame(rows)
    check(all(l["prev_id"] == "" for l in fr if l["id"] in ("t2-v3-k20-1",)),
          "a step set by the baseline has no prev_id (the baseline is one entry)")
    l = one(fr, 2, 3, 10)
    check(l and l["N"] == "11" and l["id"] == "t2-v3-k10-3" and l["prev_id"] == "t2-v3-k10-2",
          "prev_id is the best before the first row reaching N: the 12, not the baseline 13")
    check(one(fr, 2, 3, 5) is None, "the baseline 11 at k = 5 is no longer a step")
    rows = [row(3, 5, 30, 200), row(3, 4, 30, 205), row(3, 4, 40, 300)]
    fr, _ = frame(rows)
    l = one(fr, 3, 4, 30)
    check(l and l["basis"] == "derived" and l["N"] == "198" and l["prev_id"] == "t3-v4-k30-1",
          "a derived step's prev_id is the Colbourn-rule row it beats")
    fr, _ = frame([row(3, 5, 30, 200)])
    l = one(fr, 3, 4, 30)
    check(l and l["prev_id"] == "", "a derived step past every counted row has an empty prev_id")


def test_past_range_fuse_only():
    fr, _ = frame([row(3, 3, 40, 100)])
    check(one(fr, 2, 3, 39) is None, "past every counted row of its t and v, a derive step is left out")
    fr, _ = frame([row(3, 3, 40, 100), row(2, 3, 50, 40)])
    l = one(fr, 2, 3, 39)
    check(l and l["basis"] == "derived" and l["N"] == "33", "within the counted range a derive step counts")
    fr, _ = frame([row(3, 4, 40, 100), row(3, 3, 10, 30)])
    l = one(fr, 3, 3, 40)
    check(l and l["N"] == "98" and l["construction"].endswith(":fuse"),
          "past every counted row of its t and v, a fuse step counts")
    check(one(fr, 2, 3, 39) is None and one(fr, 2, 4, 39) is None, "and its derive steps there do not")


def test_past_range_veto():
    """issue #62, CONVENTIONS.md section 6 (version 1.3): past every counted row of its t and v a fused size counts
    only if no line of derived.csv at that t and v and a width k' >= k has a smaller N, whatever its rule"""
    import consistency as cc
    rows = [row(3, 4, 40, 100, "VERIFIED", "S7", "", "a4" * 32, "2026-11-01", con="S4"), row(3, 3, 10, 30)]
    fr, st = frame(rows)
    l = one(fr, 3, 3, 40)
    check(l and l["N"] == "98" and st["derived_vetoed"] == 0, "without a derived.csv nothing is withheld")
    fr, st = frame(rows, derived=[(3, 3, 50, 90, "PCT")])
    check(one(fr, 3, 3, 40) is None and st["derived_vetoed"] == 1 and [l["k"] for l in at(fr, 3, 3)] == ["10"],
          "beaten: an uncounted rule gives 90 at k' = 50 >= 40, so the fused 98 is withheld (derived_vetoed 1)")
    fr, st = frame(rows, derived=[(3, 3, 40, 97, "fuse")])
    check(one(fr, 3, 3, 40) is None, "a counted rule in derived.csv at the same width withholds it too")
    fr, st = frame(rows, derived=[(3, 3, 50, 98, "PCT"), (3, 3, 30, 50, "CK"), (3, 2, 60, 10, "DP2"),
                                  (2, 3, 60, 10, "DP2")])
    l = one(fr, 3, 3, 40)
    check(l and l["N"] == "98" and l["basis"] == "derived",
          "not beaten: an equal N at k' >= k, a smaller N only at k' < k, or a line at another t or v does not "
          "withhold it")
    check(at(fr, 3, 2) == [] and st["derived_vetoed"] == 2,
          "the fused 28 and 96 at (3, 2), with no counted row there, are withheld by DP2 10 at k' = 60")
    # inside the counted range nothing is withheld, however small the derived.csv line
    rows2 = rows + [row(3, 3, 60, 200)]
    fr, st = frame(rows2, derived=[(3, 3, 50, 5, "PCT")])
    check(one(fr, 3, 3, 40) and one(fr, 3, 3, 40)["N"] == "98" and st["derived_vetoed"] == 0,
          "inside the counted range a derived step is never withheld by derived.csv")
    # the consistency.py check on the committed files
    with tempfile.TemporaryDirectory() as d:
        write_table(d, rows, derived=[(3, 3, 50, 99, "PCT")])
        with contextlib.redirect_stdout(io.StringIO()):
            bf.main(["--table-dir", d])
        del cc.problems[:]
        n, bad = cc.check_frame_veto(rows, table_dir=d)
        check(n == 3 and bad == 0 and not cc.problems, "consistency.py: a frame built against derived.csv obeys it")
        write_table(d, rows, derived=[(3, 3, 50, 90, "PCT")])
        n, bad = cc.check_frame_veto(rows, table_dir=d)
        check(bad == 1 and len(cc.problems) == 1 and "3,3,40,98" in cc.problems[0],
              "consistency.py: a past-range line above a derived.csv line at k' >= k is a problem")
        del cc.problems[:]
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            n, bad = cc.check_frame_veto(rows, warn=True, table_dir=d)
        check(bad == 1 and not cc.problems and out.getvalue().count("::warning::") == 1,
              "with --guarantee-warn (table-page, after merge) it is a ::warning:: line")
    del cc.problems[:]


def test_past_range_prev_id():
    """a past-range step below the counted value at the widest counted width names that row as prev_id"""
    fr, _ = frame([row(3, 13, 30, 500, "VERIFIED", "S7", "", "d3" * 32, "2026-11-08"), row(3, 12, 20, 600),
                   row(3, 12, 20, 650)])
    l = one(fr, 3, 12, 30)
    check(l and l["N"] == "498" and l["prev_id"] == "t3-v12-k20-1",
          "CA(498; 3, 30, 12) past the counted range lowers the 600 at k = 20: prev_id names that row")
    fr, _ = frame([row(3, 13, 30, 500, "VERIFIED", "S7", "", "d3" * 32, "2026-11-08"), row(3, 12, 20, 400)])
    l = one(fr, 3, 12, 30)
    check(l and l["N"] == "498" and l["prev_id"] == "", "one not below the widest counted value: prev_id empty")


def _live_counted_kmax():
    sys.path.insert(0, os.path.join(REPO, "table"))
    from ca_table import counted
    rows = list(csv.DictReader(open(os.path.join(REPO, "table", "ca_table.csv"), newline="", encoding="utf-8")))
    kmax = {}
    for r in counted(rows):
        tv = (int(r["t"]), int(r["v"]))
        kmax[tv] = max(kmax.get(tv, 0), int(r["k"]))
    return rows, kmax


def test_live_past_range():
    """the committed frame (issue #62): no (3, 2) or (3, 3) line past the counted range, the ten #54 alphabets
    kept (CA(11889; 3, 100000, 10)), the prev_id of CA(13115; 3, 11288, 12)"""
    rows, kmax = _live_counted_kmax()
    fr = list(csv.DictReader(open(os.path.join(REPO, "table", "ca_frame.csv"), newline="", encoding="utf-8")))
    past = [l for l in fr if (l["t"], l["v"]) in (("3", "2"), ("3", "3"))
            and int(l["k"]) > kmax[(3, int(l["v"]))]]
    check(kmax[(3, 2)] == kmax[(3, 3)] == 10000 and not past,
          "no frame line at (3, 2) or (3, 3) past the counted range (k > 10,000; got %d)" % len(past))
    l = one(fr, 3, 10, 100000)
    check(l and l["N"] == "11889" and l["basis"] == "derived", "CA(11889; 3, 100000, 10) is in the frame")
    kept = sorted({int(l["v"]) for l in fr if l["t"] == "3" and l["basis"] == "derived"
                   and int(l["k"]) > kmax.get((3, int(l["v"])), 0)})
    check(kept == [6, 10, 12, 14, 15, 18, 20, 21, 22, 24],
          "past the counted range at t = 3 the frame keeps exactly the ten #54 alphabets (got %s)" % kept)
    l = one(fr, 3, 12, 11288)
    check(l and l["N"] == "13115" and l["prev_id"] == "t3-v12-k10000-1",
          "CA(13115; 3, 11288, 12) lowers the 13,151 at k = 10,000 and names that row as prev_id")
    import consistency as cc
    del cc.problems[:]
    n, bad = cc.check_frame_veto(rows, table_dir=os.path.join(REPO, "table"))
    check(n > 0 and bad == 0 and not cc.problems,
          "consistency.py: the committed frame obeys the comparison with the committed derived.csv (%d lines)" % n)


def test_strength2_row_past_range():
    """a synthetic VERIFIED CA(2425; 2, 100000, 25) on the live table and derived.csv: the row counts at v = 25,
    its 23 fused sizes at v = 2 to 24 are withheld wherever DP2 or another rule in derived.csv gives less"""
    live = os.path.join(REPO, "table")
    rows = list(csv.DictReader(open(os.path.join(live, "ca_table.csv"), newline="", encoding="utf-8")))
    new = {c: "" for c in rows[0]}
    new.update(t="2", v="25", k="100000", N="2425", tier="VERIFIED", source_id="S7", source_detail="test row",
               array_sha256="ab" * 32, verify_stamp="ca_verify test 2026-11-09 Linux", entered="2026-11-09",
               construction="test strength-2 row")
    with tempfile.TemporaryDirectory() as d:
        for f in ("MANIFEST.csv", "EXTERNAL.csv", "withdrawn_files.csv", "derived.csv", "certificates", "constructions"):
            os.symlink(os.path.join(live, f), os.path.join(d, f))
        with open(os.path.join(d, "ca_table.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, list(rows[0]), lineterminator="\n")
            w.writeheader()
            w.writerows(rows + [new])
        lines, st, _ = bf.build(d)
        floor = bf.derived_floor(d)
    fr = [dict(zip(bf.FRAME_HEADER, l)) for l in lines]
    l = one(fr, 2, 25, 100000)
    check(l and l["basis"] == "row" and l["N"] == "2425" and bf.floor_at(floor, (2, 25), 100000) == 2448,
          "the row counts at v = 25 (a row is never withheld; DP2 gives 2448 there)")
    beaten = [v for v in range(2, 25) if bf.floor_at(floor, (2, v), 100000) < 2425 - 2 * (25 - v)]
    fused = [v for v in range(2, 25) if any(x["construction"].startswith("test strength-2 row:") for x in at(fr, 2, v))]
    check(beaten == list(range(2, 25)) and not fused,
          "derived.csv gives less at all 23 alphabets v = 2 to 24, and none of the fused sizes is in the frame")


def test_weak_row_range():
    """CONVENTIONS.md section 6 (version 1.4): a counted row past the baseline's column range that derived.csv beats at
    its own width counts, but does not widen the counted range, so the add1 sizes it would let in stay out"""
    base = [row(3, 2, 4, 8), row(3, 2, 10, 12)]
    weak = row(3, 2, 12, 64, "VERIFIED", "S7", "", "c4" * 32, "2026-11-09")
    fr, st = frame(base + [weak], derived=[(3, 2, 15, 30, "PCT")])
    check([(l["k"], l["N"], l["basis"]) for l in at(fr, 3, 2) if int(l["k"]) > 10] == [("12", "64", "row")]
          and st["range_rows_left_out"] == 1,
          "a row above PCT 30 at k' = 15 counts at k = 12, and the add1 sizes 16 and 20 at k = 11 and 12 stay out")
    fr, st = frame(base + [weak], derived=[(3, 2, 15, 70, "PCT")])
    check([(l["k"], l["N"]) for l in at(fr, 3, 2) if int(l["k"]) > 10] == [("11", "16"), ("12", "20")]
          and st["range_rows_left_out"] == 0,
          "a row not beaten at k' >= k widens the range: CA(16; 3, 11, 2) and CA(20; 3, 12, 2) by add1 count")
    inside = row(3, 2, 9, 64, "VERIFIED", "S7", "", "c5" * 32, "2026-11-09")
    fr, st = frame(base + [inside, row(3, 3, 12, 300)], derived=[(3, 2, 15, 5, "PCT")])
    check(st["range_rows_left_out"] == 0, "a row inside the baseline's column range always widens it")
    # the live table with a VERIFIED CA(1000; 3, 100000, 2) (the gap left by version 1.3: 231 lines of 80 to 996)
    live = os.path.join(REPO, "table")
    rows = list(csv.DictReader(open(os.path.join(live, "ca_table.csv"), newline="", encoding="utf-8")))
    new = {c: "" for c in rows[0]}
    new.update(t="3", v="2", k="100000", N="1000", tier="VERIFIED", source_id="S7", source_detail="test row",
               array_sha256="ab" * 32, verify_stamp="ca_verify test 2026-11-09 Linux", entered="2026-11-09",
               construction="test weak row")
    with tempfile.TemporaryDirectory() as d:
        for f in ("MANIFEST.csv", "EXTERNAL.csv", "withdrawn_files.csv", "derived.csv", "certificates", "constructions"):
            os.symlink(os.path.join(live, f), os.path.join(d, f))
        with open(os.path.join(d, "ca_table.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, list(rows[0]), lineterminator="\n")
            w.writeheader()
            w.writerows(rows + [new])
        lines, st, _ = bf.build(d)
    fr = [dict(zip(bf.FRAME_HEADER, l)) for l in lines]
    past = [l for l in at(fr, 3, 2) if int(l["k"]) > 10000]
    check([(l["k"], l["N"], l["basis"]) for l in past] == [("100000", "1000", "row")] and st["range_rows_left_out"] == 2,
          "live: CA(1000; 3, 100000, 2) counts as a row, and no derived line at (3, 2) past k = 10,000 enters "
          "(left out of the range: it and t6-v2-k10051-1)")


def test_label_with_colon_and_comma():
    lab = "CPHF(2; 32, 23, 6): affine expansion, deleted columns"
    rows = [row(4, 7, 40, 5000, "VERIFIED", "S7", "", "7" * 64, con=lab), row(3, 6, 60, 900), row(3, 7, 39, 9000)]
    fr, _ = frame(rows)
    l = one(fr, 3, 6, 39)
    check(l and l["construction"] == lab + ":derive:fuse" and l["ids_all"] == "t4-v7-k40-1",
          "a label with a colon and commas is kept whole, the steps follow it")
    with tempfile.TemporaryDirectory() as d:
        write_table(d, rows)
        with contextlib.redirect_stdout(io.StringIO()):
            bf.main(["--table-dir", d])
        back = [dict(zip(bf.FRAME_HEADER, x)) for x in csv.reader(open(os.path.join(d, "ca_frame.csv"), newline=""))][1:]
    b = [x for x in back if (x["t"], x["v"], x["k"]) == ("3", "6", "39")]
    check(b and b[0]["construction"] == lab + ":derive:fuse", "the CSV quoting reads back to the same working")
    w = l["construction"]
    m = re.search(r"(:(fuse|derive))+$", w)
    check(m and w[:m.start()] == lab and m.group(0)[1:].split(":") == ["derive", "fuse"],
          "splitting off the trailing :fuse/:derive pieces gives the label and the steps")
    import consistency
    ids = dict(zip(bf.row_ids(rows), rows))
    check(consistency.frame_workings_ok(l, ids), "consistency.py accepts the working")
    bad = dict(l, construction="t4-v7-k40-1:derive:fuse", constructions_all="t4-v7-k40-1:derive:fuse")
    check(not consistency.frame_workings_ok(bad, ids), "consistency.py refuses an id in place of the label")
    bad = dict(l, construction=lab + ":fuse", constructions_all=lab + ":fuse")
    check(not consistency.frame_workings_ok(bad, ids), "consistency.py refuses a wrong number of steps")


def test_add1():
    import consistency
    rows = [row(4, 3, 20, 200, "VERIFIED", "S7", "", "a1" * 32, "2026-11-01", con="mainlab"),
            row(2, 3, 30, 15, entered="2026-08-23", con="inglab"), row(4, 3, 25, 2000)]
    fr, st = frame(rows)
    l = one(fr, 4, 3, 21)
    check(l and l["N"] == "290" and l["basis"] == "derived" and l["construction"] == "mainlab:add1"
          and l["ids_all"] == "t4-v3-k20-1+t2-v3-k30-1",
          "add1: CA(200; 4, 20, 3) and CA(15; 2, 30, 3) give 200 + 3 x 2 x 15 = 290 at k = 21, both rows in ids_all")
    check(l and l["tier"] == "CITED" and l["entered"] == "2026-11-01" and l["get"] == "none" and l["id"] == "",
          "an add1 step has the weaker tier of its two inputs (CITED) and the later entry date")
    l = one(fr, 4, 3, 23)
    check(l and l["N"] == "470" and l["construction"] == "mainlab:add1:add1:add1"
          and l["ids_all"] == "t4-v3-k20-1+t2-v3-k30-1+t2-v3-k30-1+t2-v3-k30-1",
          "add1 repeated: one ':add1' and one ingredient id per added column")
    l = one(fr, 4, 3, 25)
    check(l and l["N"] == "650" and l["prev_id"] == "t4-v3-k25-1", "a chain may end below a row at its width")
    check(st["derived_add1"] == 5, "five add1 steps (k = 21 to 25)")
    ids = dict(zip(bf.row_ids(rows), rows))
    l = one(fr, 4, 3, 22)
    check(consistency.frame_workings_ok(l, ids), "consistency.py accepts the add1 working, its N, tier and date")
    for what, bad in (("a wrong N", dict(l, N="381")),
                      ("a missing ingredient id", dict(l, ids_all="t4-v3-k20-1+t2-v3-k30-1")),
                      ("a wrong tier", dict(l, tier="VERIFIED")),
                      ("an ingredient that is too narrow", dict(l, ids_all="t4-v3-k20-1+t2-v3-k30-1+t4-v3-k25-1")),
                      ("a step missing from the working", dict(l, construction="mainlab:add1",
                                                                constructions_all="mainlab:add1"))):
        check(not consistency.frame_workings_ok(bad, ids), "consistency.py refuses an add1 working with " + what)


def test_add1_t3():
    """t = 3: the strength 1 ingredient is the trivial CA(v; 1, k - 1, v) (v constant rows), so a step adds v(v-1)v
    and names no ingredient row"""
    import consistency
    rows = [row(3, 3, 20, 100, "VERIFIED", "S7", "", "c3" * 32, "2026-11-01", con="m3"), row(3, 3, 25, 900)]
    fr, st = frame(rows)
    l = one(fr, 3, 3, 21)
    check(l and l["N"] == "118" and l["basis"] == "derived" and l["construction"] == "m3:add1"
          and l["ids_all"] == "t3-v3-k20-1" and l["tier"] == "VERIFIED" and l["entered"] == "2026-11-01",
          "add1 at t = 3: CA(100; 3, 20, 3) + 3 x 2 x 3 (the trivial CA(3; 1, 19, 3)) = 118 at k = 21; no ingredient id")
    l = one(fr, 3, 3, 25)
    check(l and l["N"] == "190" and l["construction"] == "m3" + ":add1" * 5 and l["ids_all"] == "t3-v3-k20-1"
          and l["prev_id"] == "t3-v3-k25-1", "five t = 3 steps: 100 + 5 x 18 = 190 below the row 900 at k = 25")
    ids = dict(zip(bf.row_ids(rows), rows))
    check(consistency.frame_workings_ok(l, ids), "consistency.py accepts a t = 3 add1 working (adds v(v-1)v per step)")
    for what, bad in (("a wrong N", dict(l, N="191")),
                      ("an ingredient row named", dict(l, ids_all="t3-v3-k20-1+t3-v3-k25-1"))):
        check(not consistency.frame_workings_ok(bad, ids), "consistency.py refuses a t = 3 add1 working with " + what)
    # a t = 3 add1 step after a derive: (4, 3, 21, 330) -> (3, 3, 20, 110) -> 128 at k = 21
    rows = [row(4, 3, 21, 330, con="m4"), row(3, 3, 25, 900)]
    fr, _ = frame(rows)
    l = one(fr, 3, 3, 21)
    check(l and l["N"] == "128" and l["construction"] == "m4:derive:add1"
          and consistency.frame_workings_ok(l, dict(zip(bf.row_ids(rows), rows))),
          "derive then a t = 3 add1 step: floor(330 / 3) + 18 = 128, accepted by consistency.py")
    # past every counted row of (3, v) no t = 3 add1 step counts (fuse alone counts there)
    fr, _ = frame([row(3, 3, 20, 100)])
    check(one(fr, 3, 3, 21) is None, "no t = 3 add1 step past every counted row of its t and v")


def test_add1_chain_cut_sound():
    """the add1 chain cut keeps every chain that can still land below a row (red team repros A and B)"""
    def r(t, v, k, n, tier="CITED", entered="2026-08-23", con="x"):
        return row(t, v, k, n, tier, "S1" if tier == "CITED" else "S7", SNAP if tier == "CITED" else "", "",
                   entered, con)
    # with t = 3 steps these tables go lower still (A: 14, B: 10 at (2, 2, 8)); they test the cut at t >= 4 alone
    tmin, bf.ADD1_TMIN = bf.ADD1_TMIN, 4
    try:
        _chain_cut_cases(r)
    finally:
        bf.ADD1_TMIN = tmin
    fr, _ = frame([r(2, 2, 8, 4, con="A"), r(2, 2, 9, 26, "VERIFIED", "2026-11-01", "B"), r(4, 2, 6, 16, con="C")])
    l = one(fr, 2, 2, 9)
    check(l and l["N"] == "14" and l["construction"] == "C:add1:add1:add1:add1:derive:add1:derive",
          "with t = 3 steps: 48 at (4, 2, 10), derived to 24, + 2 x 1 x 2 = 28 at (3, 2, 10), derived to 14 at (2, 2, 9)")


def _chain_cut_cases(r):
    # A: (4, 2, 6, 16) + add1 x 5 (ingredients (2, 2, 8, 4), then (2, 2, 9, 26)) = 100 at k = 11, derived twice
    # = 25 at (2, 2, 9), below the row 26; the chain passes widths where the stair at k - 2 is lower
    fr, _ = frame([r(2, 2, 8, 4, con="A"), r(2, 2, 9, 26, "VERIFIED", "2026-11-01", "B"), r(4, 2, 6, 16, con="C")])
    l = one(fr, 2, 2, 9)
    check(l and l["N"] == "25" and l["construction"] == "C:add1:add1:add1:add1:add1:derive:derive",
          "a chain is not cut while it can still land below a row at a wider point (repro A: 25 < 26 at (2, 2, 9))")
    # B: (4, 2, 8, 74) -> 90 -> 122 at k = 10 is above the row 66 at k = 15 of its own (t, v), yet derived twice it
    # gives 30 at (2, 2, 8), below the row 38 (the row 66 derives past the counted range of (2, 2))
    fr, _ = frame([r(4, 2, 8, 74, con="P"), r(4, 2, 15, 66, "VERIFIED", "2026-10-15", "Q"),
                   r(3, 2, 8, 17, "VERIFIED", con="R"), r(2, 2, 9, 38, con="S")])
    l = one(fr, 2, 2, 8)
    check(l and l["N"] == "30" and l["construction"] == "P:add1:add1:derive:derive",
          "a size above a wider value of its own (t, v) still continues its chain (repro B: 30 at (2, 2, 8))")


def test_add1_ingredient_tier():
    """among add1 ingredients of equal size a VERIFIED row is named first (red team repro C)"""
    rows = [row(4, 3, 20, 200, "VERIFIED", "S7", "", "d4" * 32, "2026-10-01", con="main"),
            row(2, 3, 30, 15, "VERIFIED", "S7", "", "d2" * 32, "2026-09-01", con="ingV"),
            row(2, 3, 30, 15, "CITED", "S1", "", "", "2026-11-01", con="ingC"), row(4, 3, 25, 2000)]
    fr, _ = frame(rows)
    l = one(fr, 4, 3, 21)
    check(l and l["tier"] == "VERIFIED" and l["entered"] == "2026-10-01" and l["ids_all"] == "t4-v3-k20-1+t2-v3-k30-1",
          "a VERIFIED ingredient beats a CITED one of the same size: the step stays VERIFIED")


def test_ci_checks():
    """consistency.py: a plain path to a gzipped array resolves; a RETRACTED row may retract a VERIFIED row and
    its SCREENED twin together"""
    import consistency as cc
    m = cc.PLAIN.search("see table/arrays/CA_8176_3_258_16.txt.gz for the array")
    check(m and m.group(1) == "table/arrays/CA_8176_3_258_16.txt.gz", "a plain path ending in .txt.gz is read whole")
    sha = "e" * 64
    def srow(*a):
        return {c: str(x) for c, x in row(*a).items()}
    scr = srow(3, 4, 10, 60, "SCREENED", "S7", "", sha, "2026-11-01")
    ver = srow(3, 4, 10, 60, "VERIFIED", "S7", "", sha, "2026-11-02")
    ret = dict(srow(3, 4, 10, 60, "RETRACTED", "S7", "", sha, "2026-11-05"), notes="found not covering")
    del cc.problems[:]
    cc.check_retracted([scr, ver, ret])
    check(not cc.problems, "a RETRACTED row matching a VERIFIED row and its SCREENED twin is accepted")
    del cc.problems[:]
    cc.check_retracted([scr, ver, dict(ret, N="61")])
    check(len(cc.problems) == 1 and "matches no" in cc.problems[0], "a RETRACTED row matching no row is refused")
    del cc.problems[:]


def test_add1_scope():
    # past every counted row of its t and v an add1 step does not count
    fr, _ = frame([row(4, 3, 20, 200), row(2, 3, 30, 15)])
    check(one(fr, 4, 3, 21) is None, "past every counted row of its t and v, an add1 step is left out")
    # no ingredient wide enough: no add1 (the row at k = 25, derived twice, gives (2, 3, 23, 55), but
    # 200 + 6 x 55 = 530 is not below the 500 of that row)
    fr, _ = frame([row(4, 3, 20, 200), row(2, 3, 18, 15), row(4, 3, 25, 500)])
    check(one(fr, 4, 3, 21) is None, "no add1 step without an ingredient of width k - 2 or more")
    fr, _ = frame([row(4, 3, 20, 200), row(2, 3, 18, 15), row(4, 3, 25, 2000)])
    l = one(fr, 4, 3, 21)
    check(l and l["N"] == str(200 + 6 * 222) and l["ids_all"] == "t4-v3-k20-1+t4-v3-k25-1",
          "a derived ingredient: (4, 3, 25, 2000) derived twice gives (2, 3, 23, 222), credited by its row")
    # fuse, then add1 with a fused ingredient: (4,4,20,200) -> (4,3,20,198); ingredient (2,4,30,20) -> 18
    rows = [row(4, 4, 20, 200, con="m4"), row(2, 4, 30, 20, con="i4"), row(4, 3, 30, 5000)]
    fr, _ = frame(rows)
    l = one(fr, 4, 3, 21)
    check(l and l["N"] == str(198 + 6 * 18) and l["construction"] == "m4:fuse:add1"
          and l["ids_all"] == "t4-v4-k20-1+t2-v4-k30-1",
          "fuse then add1, the ingredient itself fused: 198 + 3 x 2 x 18 = 306, ingredient credited by its row")
    check(one(fr, 4, 4, 21) is None, "and no add1 step at (4, 4, 21), past every counted row of (4, 4)")
    import consistency
    check(consistency.frame_workings_ok(l, dict(zip(bf.row_ids(rows), rows))),
          "consistency.py accepts it (the ingredient's own fuse steps recomputed from its row)")
    # a CITED row with a DISPUTED row beside it is neither the main input nor the ingredient of add1
    rows = [row(4, 3, 20, 200), row(2, 3, 30, 15, con="cyclotomy"),
            dict(row(2, 3, 30, 15, "DISPUTED", "S6", ""), notes="fails"), row(4, 3, 25, 500)]
    fr, _ = frame(rows)
    check(one(fr, 4, 3, 21) is None, "no add1 step with a disputed-partner row as ingredient")


def test_colbourn_add1_rows():
    """Colbourn's "Add 1 factors" rows (CKRS 2010 Theorem 3.2) from their ingredients in his own rows (S1)"""
    import derive_laws as L
    look = L.load(sources={"S1"})
    e = L.mk_ecan(look)
    a1 = [r for r in L.rows if r["source_id"] == "S1" and r["construction"] == "Add 1 factors"]
    ok = [r for r in a1 if L.law_add1(e, int(r["t"]), int(r["v"]), int(r["k"]))
          == (int(r["N"]), ())]
    check(len(a1) == 133 and len(ok) == 133,
          "the 133 'Add 1 factors' rows are CAN(t, k-1, v) + v(v-1) CAN(t-2, k-2, v) over Colbourn's rows (%d of %d)"
          % (len(ok), len(a1)))
    check(all(r["t"] in ("5", "6") for r in a1), "all of them have t = 5 or 6")


def test_get_from_tied_verified():
    sha = "8" * 64
    rows = [row(2, 5, 12, 40, con="cited label"), row(2, 5, 12, 40, "VERIFIED", "S7", "", sha, "2026-11-02", con="ours"),
            row(2, 5, 14, 44)]
    fr, _ = frame(rows, manifest=[["CA_40_2_12_5.txt", 2, 5, 12, 40, "equals_best", sha, "S7", "", "", 2]])
    l = one(fr, 2, 5, 12)
    check(l and l["id"] == "t2-v5-k12-1" and l["tier"] == "CITED" and l["construction"] == "cited label"
          and l["get"] == "file" and l["get_ref"] == "table/arrays/CA_40_2_12_5.txt" and l["constant_rows"] == ""
          and l["ids_all"] == "t2-v5-k12-1;t2-v5-k12-2",
          "a CITED named row with get none takes get and get_ref from the tied VERIFIED row; id stays the CITED row")
    l = one(fr, 2, 5, 14)
    check(l and l["get"] == "none" and l["get_ref"] == "", "a CITED row with no tied array: get none")


def test_live_withdrawn_list():
    path = os.path.join(REPO, "table", "withdrawn_files.csv")
    w = list(csv.DictReader(open(path, newline="", encoding="utf-8")))
    fp = [x["file"] for x in csv.DictReader(open(os.path.join(REPO, "table", "withdrawn_fingerprints.csv"),
                                                    newline="", encoding="utf-8"))]
    import withdrawn_fingerprints as wf
    old = [x["file"] for x in w if x["withdrawn"] == wf.WITHDRAWN_ON]
    later = [(x["t"], x["v"], x["k"], x["N"]) for x in w if x["withdrawn"] != wf.WITHDRAWN_ON]
    check(old == fp and len(old) == 137,
          "withdrawn_fingerprints.py reads exactly the 137 files withdrawn on 2026-10-27 (those in its output)")
    check(later == [("4", "2", "338", "177"), ("4", "2", "354", "178"), ("4", "2", "358", "179")],
          "the three never stored TJ2level arrays are the only later lines")


def test_get():
    sha1, sha2, sha3 = "4" * 64, "5" * 64, "6" * 64
    rows = [row(2, 4, 10, 30, "VERIFIED", "S7", "", sha1), row(2, 4, 12, 33, "VERIFIED", "S6", "", sha2),
            row(2, 4, 14, 35), row(2, 4, 16, 37, "VERIFIED", "S4", "", sha3, con="IPOG-F")]
    rows[3]["source_detail"] = "math.nist.gov/coveringarrays ipof ca.2.4^16.txt.zip via CAs::nistCA, CAs 0.24"
    fr, _ = frame(rows, manifest=[["CA_30_2_10_4.txt", 2, 4, 10, 30, "equals_best", sha1, "S7", "", "", 3]],
                  withdrawn=[["CA_33_2_12_4.txt", 2, 4, 12, 33, "equals_best", sha2, "S6", "", "", 1, "2026-10-27", "x"]])
    g = {l["k"]: (l["get"], l["get_ref"], l["constant_rows"], l["constant_rows_basis"]) for l in at(fr, 2, 4)}
    check(g.get("10") == ("file", "table/arrays/CA_30_2_10_4.txt", "3", "exact"),
          "an array in MANIFEST.csv: get file, its path, exact constant rows")
    check(g.get("12") == ("none", "", "", ""), "a withdrawn array file: get none")
    check(g.get("14") == ("none", "", "", ""), "a CITED row: get none")
    check(g.get("16") == ("url", "https://math.nist.gov/coveringarrays/ipof/cas/t=2/v=4/ca.2.4^16.txt.zip", "", ""),
          "a NIST row without a stored file: get url, built as CAs::nistCA builds it")


def test_text_and_check():
    rows = [row(3, 5, 20, 100, con="a label, with a comma"), row(2, 2, 4, 5)]
    with tempfile.TemporaryDirectory() as d:
        write_table(d, rows)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc_w = bf.main(["--table-dir", d])
            rc_c = bf.main(["--table-dir", d, "--check"])
        fr = list(csv.reader(open(os.path.join(d, "ca_frame.csv"), newline="")))
        gz1 = open(os.path.join(d, "ca_table.csv.gz"), "rb").read()
        with contextlib.redirect_stdout(out):
            bf.main(["--table-dir", d])
        gz2 = open(os.path.join(d, "ca_table.csv.gz"), "rb").read()
        check(rc_w == 0 and rc_c == 0, "write, then --check passes")
        check(fr[0] == bf.FRAME_HEADER and all(len(l) == len(bf.FRAME_HEADER) for l in fr),
              "the header of CONVENTIONS.md section 7, every line complete")
        check(gz1 == gz2 and gzip.decompress(gz1) == open(os.path.join(d, "ca_table.csv"), "rb").read(),
              "ca_table.csv.gz: the same bytes on a rerun, and it decompresses to ca_table.csv")
        check(gz1[4:8] == b"\0\0\0\0" and not (gz1[3] & 8), "the gzip header has no time and no file name")
        with open(os.path.join(d, "ca_frame.csv"), "a") as f:
            f.write("2,2,9,9,row,CITED,,,,none,,x,,x,,,,\n")
        with contextlib.redirect_stdout(out):
            rc = bf.main(["--table-dir", d, "--check"])
        check(rc == 1, "--check fails on an edited frame file")
        check(any(l[11] == "a label, with a comma" for l in fr), "a construction with a comma is quoted and read back")


def test_guarantee():
    import consistency as cc
    rows = [row(3, 4, 10, 60), row(3, 4, 20, 80),
            row(3, 4, 15, 85, "SCREENED", "S7", "", "7" * 64), row(3, 4, 10, 60, "DISPUTED", "S6", "")]
    del cc.problems[:]
    n, bad = cc.check_guarantee(rows)
    check(n == 2 and bad == 0 and not cc.problems, "the section 4 guarantee holds: uncounted rows at or above the counted best")
    rows.append(row(3, 4, 18, 75, "SCREENED", "S7", "", "8" * 64))
    rows.append(row(3, 4, 30, 99, "SCREENED", "S7", "", "9" * 64))
    del cc.problems[:]
    cc.check_guarantee(rows)
    check(len(cc.problems) == 2 and "3,4,18,75" in cc.problems[0] and "(none)" in cc.problems[1],
          "a SCREENED row below the counted best, or past every counted row, is reported")
    del cc.problems[:]
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        n, bad = cc.check_guarantee(rows, warn=True)
    check(bad == 2 and not cc.problems and out.getvalue().count("::warning::") == 2,
          "with warn (table-page), a break is a ::warning:: line and not a problem")


def main():
    for fn in (test_guarantee, test_fuse_chain, test_derive_chain, test_tier_of_weakest_and_ties, test_equal_is_row,
               test_disputed_excluded, test_retracted_excluded, test_steps, test_ids_stable, test_prev_id, test_past_range_fuse_only,
               test_past_range_veto, test_past_range_prev_id, test_live_past_range, test_strength2_row_past_range,
               test_weak_row_range,
               test_label_with_colon_and_comma, test_add1, test_add1_t3, test_add1_chain_cut_sound,
               test_add1_ingredient_tier, test_ci_checks, test_add1_scope, test_colbourn_add1_rows,
               test_get_from_tied_verified, test_live_withdrawn_list,
               test_get, test_text_and_check):
        fn()
    print("%d passed, %d failed" % (RESULTS["pass"], RESULTS["fail"]))
    return 1 if RESULTS["fail"] else 0


if __name__ == "__main__":
    sys.exit(main())
