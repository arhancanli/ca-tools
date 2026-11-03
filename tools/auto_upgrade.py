#!/usr/bin/env python3
"""auto_upgrade - queue the exact check of arrays that just entered the table as SCREENED.

An array whose full check does not fit the time budget of one table-page run is screened and
enters as SCREENED. The exact check can still be done, in shards on GitHub-hosted runners, by
an upgrade request (submissions/<slug>/upgrade.csv, tools/check_upgrades.py). This script writes
that request automatically, so the submitter does not have to open a second pull request.

For every slug given (the claims submissions entered in this table-page run), every row that

  - is SCREENED, names "submission <slug>" in its notes and has an array_sha256,
  - has no VERIFIED row with the same array_sha256, and
  - is not named by any existing submissions/*/upgrade.csv,

goes into the request submissions/<slug>-exact/upgrade.csv, with the credit of the SCREENED row
as the person who asks (the submitter asked for the array to be checked by submitting it) and a
note that the request was queued automatically. The folder must not exist yet. The script
prints the slug of every request it wrote, one per line; table-page.yml commits them and starts
certificate-check.yml for each (workflow_dispatch, input slug). A request whose check is over
the budget stays SCREENED and gets NOT_APPLIED.md, as for a request made by hand.

Usage: auto_upgrade.py [--table-dir DIR] [--submissions DIR] [--dry-run] SLUG ...
Exit status 0 (also when nothing was queued), 2 usage error. Standard library only.
"""
import argparse
import csv
import os
import re
import sys

HEADER = ["kind", "sha256", "credit", "notes"]
SLUG_RE = re.compile(r"^[A-Za-z0-9._-]+$")


def original_credit(notes):
    m = re.search(r"(?:^|; )credit: ([^;]+)", notes or "")
    return m.group(1).strip() if m else None


def requested_shas(sub_dir):
    seen = set()
    for name in sorted(os.listdir(sub_dir)):
        p = os.path.join(sub_dir, name, "upgrade.csv")
        if not os.path.isfile(p):
            continue
        with open(p, newline="", encoding="utf-8-sig") as f:
            for rec in csv.DictReader(f):
                if (rec.get("sha256") or "").strip():
                    seen.add(rec["sha256"].strip())
    return seen


def plan(rows, slugs, seen):
    verified = {r["array_sha256"] for r in rows if r["tier"] == "VERIFIED" and r["array_sha256"]}
    out = {}
    for slug in slugs:
        pat = re.compile(r"submission %s(?:[;,\"]|$)" % re.escape(slug))
        for r in rows:
            sha = r["array_sha256"]
            if r["tier"] != "SCREENED" or not sha or not pat.search(r["notes"] or ""):
                continue
            if sha in verified or sha in seen:
                continue
            credit = original_credit(r["notes"])
            if not credit:
                continue  # check_upgrades.py would refuse it; the maintainer asks by hand
            seen.add(sha)
            out.setdefault(slug, []).append(dict(
                kind="array", sha256=sha, credit=credit,
                notes="queued automatically when submission %s entered as SCREENED: CA(%s; %s, %s, %s)"
                      % (slug, r["N"], r["t"], r["k"], r["v"])))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("slugs", nargs="*")
    ap.add_argument("--table-dir", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "table"))
    ap.add_argument("--submissions", default=None)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    sub_dir = a.submissions or os.path.join(a.table_dir, "..", "submissions")
    for s in a.slugs:
        if not SLUG_RE.match(s):
            print("bad slug %r" % s, file=sys.stderr)
            return 2
    with open(os.path.join(a.table_dir, "ca_table.csv"), newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    todo = plan(rows, a.slugs, requested_shas(sub_dir))
    for slug, entries in todo.items():
        req = slug + "-exact"
        d = os.path.join(sub_dir, req)
        if os.path.exists(d):
            print("submissions/%s exists already; not queued" % req, file=sys.stderr)
            continue
        if not a.dry_run:
            os.makedirs(d)
            with open(os.path.join(d, "upgrade.csv"), "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=HEADER, lineterminator="\n")
                w.writeheader()
                for e in entries:
                    w.writerow(e)
        print(req)
    return 0


if __name__ == "__main__":
    sys.exit(main())
