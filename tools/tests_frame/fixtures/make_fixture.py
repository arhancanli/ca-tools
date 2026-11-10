#!/usr/bin/env python3
"""Write the fixed fixture tables of the frame tests from one commit of this repository.

The rule tests of tools/build_frame.py and tools/consistency.py (fuse, derive, add1, the counted range
of CONVENTIONS.md section 6, versions 1.3 and 1.4) used to read the live table/ and assert sizes in it.
The live table grows every day, so those tests broke when a new row moved a value they named. They now
read a fixed copy of the table as it was at one commit, made by this script and kept in git. It is never
regenerated to make a test pass: a new fixture is a new folder, made on purpose, and the tests that use
it name it.

  table_<commit>/        a table directory that tools/build_frame.py can build from
    ca_table.csv.gz      the rows at t = 2 and 3, and at t = 6, v = 2, in their order at that commit
                         (so the row ids are the same); the columns notes, builds_on, lb and lb_evidence
                         are emptied (no tool of the frame reads them)
    derived.csv          the lines of table/derived.csv at the same t and v
    above_rule_rows.csv  as at that commit
    MANIFEST.csv, EXTERNAL.csv, withdrawn_files.csv, certificates/CERTIFICATES.csv,
    constructions/CONSTRUCTIONS.csv   the header only (no stored arrays)
  colbourn_add1_<commit>.csv.gz   Colbourn's rows (source S1) labelled "Add 1 factors" and, for each, the
                         S1 rows that answer its two lookups CAN(t, k-1, v) and CAN(t-2, k-2, v)
  withdrawn_files_<commit>.csv.gz table/withdrawn_files.csv at that commit (the list is append-only)

Usage: python3 tools/tests_frame/fixtures/make_fixture.py COMMIT   (run from the repository root)
"""
import bisect
import csv
import gzip
import io
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
KEEP_TV = lambda t, v: t in (2, 3) or (t, v) == (6, 2)  # noqa: E731
BLANK = ("notes", "builds_on", "lb", "lb_evidence")
EMPTY = ("MANIFEST.csv", "EXTERNAL.csv", "withdrawn_files.csv", "certificates/CERTIFICATES.csv",
         "constructions/CONSTRUCTIONS.csv")


def show(commit, path):
    return subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (commit, path)], check=True,
                          stdout=subprocess.PIPE).stdout.decode("utf-8")


def gz(text):
    buf = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=buf, compresslevel=9, mtime=0) as g:
        g.write(text.encode("utf-8"))
    return buf.getvalue()


def csv_text(header, rows):
    s = io.StringIO()
    w = csv.DictWriter(s, header, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return s.getvalue()


def main(argv):
    commit = subprocess.run(["git", "-C", REPO, "rev-parse", "--short=7", argv[0]], check=True,
                            stdout=subprocess.PIPE, universal_newlines=True).stdout.strip()
    out = os.path.join(HERE, "table_" + commit)
    os.makedirs(os.path.join(out, "certificates"), exist_ok=True)
    os.makedirs(os.path.join(out, "constructions"), exist_ok=True)
    table = list(csv.DictReader(io.StringIO(show(commit, "table/ca_table.csv"))))
    header = list(table[0])
    keep = []
    for r in table:
        if KEEP_TV(int(r["t"]), int(r["v"])):
            r = dict(r)
            for c in BLANK:
                r[c] = ""
            keep.append(r)
    open(os.path.join(out, "ca_table.csv.gz"), "wb").write(gz(csv_text(header, keep)))
    der = show(commit, "table/derived.csv").splitlines(True)
    open(os.path.join(out, "derived.csv"), "w", encoding="utf-8", newline="").write(
        der[0] + "".join(l for l in der[1:] if KEEP_TV(*map(int, l.split(",")[:2]))))
    open(os.path.join(out, "above_rule_rows.csv"), "w", encoding="utf-8", newline="").write(
        show(commit, "table/above_rule_rows.csv"))
    for name in EMPTY:
        open(os.path.join(out, name), "w", encoding="utf-8", newline="").write(
            show(commit, "table/" + name).splitlines(True)[0])
    # Colbourn's "Add 1 factors" rows and the S1 rows that answer their lookups (stair step: the smallest N
    # of a counted S1 row at the same t and v with k' >= k; ties to the narrowest such row)
    sys.path.insert(0, os.path.join(REPO, "table"))
    from ca_table import counted
    s1 = [r for r in counted(table) if r["source_id"] == "S1"]
    by_tv = {}
    for r in s1:
        by_tv.setdefault((int(r["t"]), int(r["v"])), []).append(r)
    for lst in by_tv.values():
        lst.sort(key=lambda r: int(r["k"]))

    def answer(t, v, k):
        lst = by_tv.get((t, v), [])
        ks = [int(r["k"]) for r in lst]
        i = bisect.bisect_left(ks, k)
        best = min(lst[i:], key=lambda r: (int(float(r["N"])), int(r["k"])), default=None)
        return best

    a1 = [r for r in s1 if r["construction"] == "Add 1 factors"]
    need = {id(r) for r in a1}
    for r in a1:
        t, v, k = int(r["t"]), int(r["v"]), int(r["k"])
        for x in (answer(t, v, k - 1), answer(t - 2, v, k - 2) if t > 3 else None):
            if x is not None:
                need.add(id(x))
    rows = [dict(r, **{c: "" for c in BLANK}) for r in table if id(r) in need]
    open(os.path.join(HERE, "colbourn_add1_%s.csv.gz" % commit), "wb").write(gz(csv_text(header, rows)))
    open(os.path.join(HERE, "withdrawn_files_%s.csv.gz" % commit), "wb").write(
        gz(show(commit, "table/withdrawn_files.csv")))
    print("%s: %d rows, %d derived lines in all; colbourn_add1: %d rows (%d labelled Add 1 factors)"
          % (out, len(keep), len(der) - 1, len(rows), len(a1)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
