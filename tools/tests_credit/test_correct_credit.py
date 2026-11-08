"""Tests of tools/correct_credit.py on a temporary copy of the table.

Run: python3 tools/tests_credit/test_correct_credit.py   (a few seconds)

A correction changes exactly one line of ca_table.csv and appends one log line; a
dry run changes nothing; the log check accepts logged corrections and refuses a
credit field changed by hand, before or after a logged correction.
"""
import csv
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "tools"))
import correct_credit as cr  # noqa: E402

ok = 0


def check(cond, what):
    global ok
    if not cond:
        raise SystemExit("FAIL  " + what)
    ok += 1
    print("PASS  " + what)


def rows_of(d):
    with open(os.path.join(d, "ca_table.csv"), newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


tmp = tempfile.mkdtemp(prefix="credit-")
try:
    td = os.path.join(tmp, "table")
    os.makedirs(td)
    for n in ("ca_table.csv", "references.csv"):
        shutil.copy(os.path.join(REPO, "table", n), td)
    # the test adds postop-nck2013 to CA(6228; 3, 196, 12); the real table has carried that id
    # since the correction of 2026-11-07 (issue #47), so take it out of the copy first
    p = os.path.join(td, "ca_table.csv")
    lines = open(p, encoding="utf-8", newline="").read().split("\n")
    for i, ln in enumerate(lines):
        if ln.startswith("3,12,196,6228,"):
            lines[i] = ln.replace(";postop-nck2013", "")
    open(p, "w", encoding="utf-8", newline="").write("\n".join(lines))
    before = open(os.path.join(td, "ca_table.csv"), "rb").read()
    old_rows = rows_of(td)
    target = next(r for r in old_rows if (r["t"], r["v"], r["k"], r["N"]) == ("3", "12", "196", "6228"))
    sha = target["array_sha256"][:12]

    # dry run
    rc = cr.main(["--table-dir", td, "--row", "3,12,196,6228", "--sha", sha, "--field", "builds_on",
                  "--add", "postop-nck2013", "--reason", "r", "--requested-by", "x"])
    check(rc == 0 and open(os.path.join(td, "ca_table.csv"), "rb").read() == before
          and not os.path.exists(cr.log_path(td)), "a dry run changes nothing")

    # refusals
    for args, what in ((["--add", "no-such-id"], "an unknown builds_on id"),
                       (["--add", "fuse-ckrs2010"], "an id already listed"),
                       (["--set", "a\nb"], "a line break"),
                       (["--replace", "zzz", "y"], "a replace text that does not occur")):
        try:
            cr.main(["--table-dir", td, "--row", "3,12,196,6228", "--field", "builds_on",
                     "--reason", "r", "--requested-by", "x", "--apply"] + args)
            check(False, "refuses " + what)
        except SystemExit:
            check(open(os.path.join(td, "ca_table.csv"), "rb").read() == before, "refuses " + what)

    # an ambiguous row
    try:
        cr.main(["--table-dir", td, "--row", "2,2,4,5", "--field", "notes", "--append", "x",
                 "--reason", "r", "--requested-by", "x", "--apply"])
        amb = len([r for r in old_rows if (r["t"], r["v"], r["k"], r["N"]) == ("2", "2", "4", "5")]) == 1
    except SystemExit:
        amb = True
    check(amb, "a size that matches several rows needs --sha or --source")
    # (restore if the call above wrote: it may legitimately match a single row)
    open(os.path.join(td, "ca_table.csv"), "wb").write(before)
    if os.path.exists(cr.log_path(td)):
        os.remove(cr.log_path(td))

    # a real correction
    cr.main(["--table-dir", td, "--row", "3,12,196,6228", "--sha", sha, "--field", "builds_on",
             "--add", "postop-nck2013", "--reason", "NCK post-optimisation used",
             "--requested-by", "C. Smolen", "--date", "2026-11-02", "--apply"])
    after = open(os.path.join(td, "ca_table.csv"), "rb").read()
    a, b = before.split(b"\n"), after.split(b"\n")
    diff = [i for i, (x, y) in enumerate(zip(a, b)) if x != y]
    check(len(a) == len(b) and len(diff) == 1, "exactly one line of ca_table.csv changes")
    check(b[diff[0]].endswith(b"\r") == a[diff[0]].endswith(b"\r"), "the line ending is kept")
    new_rows = rows_of(td)
    fz = [c for c in cr.KEY_COLS if new_rows[diff[0] - 1][c] != old_rows[diff[0] - 1][c]]
    check(fz == [], "no frozen column changes")
    check(new_rows[diff[0] - 1]["builds_on"].endswith(";postop-nck2013"), "builds_on gains the id")
    log = cr.read_log(td)
    check(len(log) == 1 and log[0]["requested_by"] == "C. Smolen" and log[0]["field"] == "builds_on",
          "one log line with the request")
    check(cr.check_log(new_rows, td) == [], "the log check accepts the logged correction")
    check(cr.unlogged_changes(old_rows, new_rows, td) == [], "the base check accepts it")

    # a hand edit of another row's notes, with no log line
    hand = [dict(r) for r in new_rows]
    j = next(i for i, r in enumerate(hand) if r["tier"] == "VERIFIED" and i != diff[0] - 1)
    hand[j]["notes"] = hand[j]["notes"] + " (edited by hand)"
    probs = cr.unlogged_changes(old_rows, hand, td)
    check(len(probs) == 1 and "notes changed with no line" in probs[0], "an unlogged edit is refused")

    # a hand edit of the corrected row after its correction
    hand2 = [dict(r) for r in new_rows]
    hand2[diff[0] - 1]["builds_on"] = "fuse-ckrs2010"
    probs = cr.check_log(hand2, td)
    check(len(probs) == 1 and "differs from its last logged correction" in probs[0],
          "a change after a logged correction is refused")
finally:
    shutil.rmtree(tmp)
print("%d passed" % ok)
