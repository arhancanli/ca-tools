#!/usr/bin/env python3
"""Tests of tools/build_frame.py (table/ca_frame.csv) on small synthetic tables.

Each case writes a ca_table.csv (and, where needed, MANIFEST.csv and withdrawn_files.csv) into a
temporary directory and builds the frame there. Assertions: fuse and derive chains and their
workings, the tier of a derived step (its source row's), a derived size equal to a row is not a
derived step, no derived size from a CITED row with a DISPUTED row beside it or from a retracted
row, ids stable when rows are appended, prev_id for row steps and derived steps, the stair steps
(one line per step, dominated rows dropped), the headline among ties, get from MANIFEST and
withdrawn files, get lent by a tied VERIFIED row when the named row has none, workings in the
label form (source label, then :fuse/:derive; labels with colons and commas), the live
withdrawn_files.csv against withdrawn_fingerprints.csv, and --check.

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


def write_table(d, rows, manifest=(), withdrawn=()):
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
               test_label_with_colon_and_comma, test_get_from_tied_verified, test_live_withdrawn_list,
               test_get, test_text_and_check):
        fn()
    print("%d passed, %d failed" % (RESULTS["pass"], RESULTS["fail"]))
    return 1 if RESULTS["fail"] else 0


if __name__ == "__main__":
    sys.exit(main())
