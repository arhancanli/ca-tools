#!/usr/bin/env python3
"""Tests of tools/auto_upgrade.py on a small synthetic table (no arrays needed).

Cases: a SCREENED row of the submission is queued with the row's credit; a row with a VERIFIED
twin, a row already named by an upgrade.csv, a row of another submission, a VERIFIED row and a
row without a credit are not; a second run queues nothing; an existing <slug>-exact folder is
left alone; --dry-run writes nothing; a bad slug is refused (exit 2).

Usage: test_auto_upgrade.py   (prints PASS/FAIL lines; exit 1 on a failure)
"""
import csv
import io
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "..", "auto_upgrade.py")
COLS = ["t", "v", "k", "N", "tier", "source_id", "source_detail", "snapshot_id", "array_sha256",
        "verify_stamp", "entered", "notes", "lb", "lb_evidence", "construction", "builds_on", "family_sha256"]
fails = 0


def check(name, ok):
    global fails
    print(("PASS " if ok else "FAIL ") + name)
    fails += 0 if ok else 1


def row(tier, sha, notes, k="10"):
    r = dict.fromkeys(COLS, "")
    r.update(t="3", v="2", k=k, N="12", tier=tier, array_sha256=sha, notes=notes)
    return r


def run(root, *args):
    p = subprocess.run([sys.executable, TOOL, "--table-dir", os.path.join(root, "table"),
                        "--submissions", os.path.join(root, "submissions")] + list(args),
                       capture_output=True, text=True)
    return p.returncode, p.stdout.split()


def main():
    with tempfile.TemporaryDirectory() as root:
        os.makedirs(os.path.join(root, "table"))
        os.makedirs(os.path.join(root, "submissions", "hand"))
        A, B, C, D, E, F = ("a" * 64, "b" * 64, "c" * 64, "d" * 64, "e" * 64, "f" * 64)
        rows = [
            row("SCREENED", A, "credit: Jane Smith; SCREENED, not exhaustively verified; submission s1; x"),
            row("SCREENED", B, "credit: Jane Smith; submission s1"),
            row("VERIFIED", B, "credit: Jane Smith; exact check of the SCREENED row"),
            row("SCREENED", C, "credit: Jane Smith; submission s1"),
            row("SCREENED", D, "credit: Ann Lee; submission s10"),
            row("VERIFIED", E, "credit: Jane Smith; submission s1"),
            row("SCREENED", F, "submission s1"),
        ]
        with open(os.path.join(root, "table", "ca_table.csv"), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=COLS); w.writeheader(); w.writerows(rows)
        with open(os.path.join(root, "submissions", "hand", "upgrade.csv"), "w") as f:
            f.write("kind,sha256,credit,notes\narray,%s,Bob Roe,\n" % C)

        rc, out = run(root, "--dry-run", "s1")
        check("dry run names the request", rc == 0 and out == ["s1-exact"])
        check("dry run writes nothing", not os.path.exists(os.path.join(root, "submissions", "s1-exact")))

        rc, out = run(root, "s1")
        p = os.path.join(root, "submissions", "s1-exact", "upgrade.csv")
        check("request written", rc == 0 and out == ["s1-exact"] and os.path.isfile(p))
        recs = list(csv.DictReader(open(p))) if os.path.isfile(p) else []
        check("only the SCREENED row without VERIFIED twin, request or missing credit",
              [r["sha256"] for r in recs] == [A])
        check("credit of the row", recs and recs[0]["credit"] == "Jane Smith" and recs[0]["kind"] == "array")
        check("slug match is exact (s10 not taken for s1)", all(r["sha256"] != D for r in recs))

        rc, out = run(root, "s1")
        check("second run queues nothing", rc == 0 and out == [])

        os.makedirs(os.path.join(root, "submissions", "s10-exact"))
        rc, out = run(root, "s10")
        check("existing folder left alone", rc == 0 and out == []
              and not os.listdir(os.path.join(root, "submissions", "s10-exact")))

        rc, out = run(root, "x;y")
        check("bad slug refused", rc == 2)
    print("%d failure(s)" % fails)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
