"""correct_credit.py - correct the credit of one table row, with a permanent record.

The claim of a row (its size, tier, source, hash, stamp and date) never changes; a
wrong result is withdrawn by a RETRACTED row. The credit of a row can be wrong too:
a missing reference in builds_on, a starting array whose author is not named, a
'new' method that is someone else's. This tool corrects the three credit fields of
an existing row in place (notes, construction, builds_on) and appends what it did to
table/CREDIT_CORRECTIONS.csv: the date, the row, the field, the old and new value,
the reason, and who asked. tools/consistency.py --check requires every logged
correction to match the table, and with --base it refuses a change to a credit field
of an existing row that has no log line, so a correction is never silent. The page
marks a corrected row with a link to the log.

Usage (a dry run unless --apply is given):

  python3 tools/correct_credit.py --row 3,12,196,6228 --sha 1a2b... \\
      --field builds_on --add postop-nck2013 \\
      --reason "construction uses NCK post-optimisation" --requested-by "C. Smolen" --apply

  --row t,v,k,N           the row, with --sha (array_sha256 or family_sha256, any prefix
                          of 8+ hex digits) or --source TEXT (part of source_detail) when
                          the size alone matches more than one row
  --tier TIER             with --row: only rows of this tier (a SCREENED row and its
                          VERIFIED twin share the size and the hash)
  --field                 notes, construction or builds_on
  --set VALUE             replace the field
  --add ID / --remove ID  builds_on only: add or remove one entry
  --replace OLD NEW       replace one exact piece of the text (must occur once)
  --append TEXT           notes only: append "; TEXT"
  --reason, --requested-by  required; they go into the log
  --check                 check the log against the table and exit

Standard library only. ca_table.csv is edited on the one line of the row; every other
byte of the file is kept.
"""
import argparse
import csv
import datetime
import hashlib
import io
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "tools"))
import builds_on as bo  # noqa: E402

FIELDS = ("notes", "construction", "builds_on")
# the columns that identify a row: the frozen ones of tools/consistency.py, less
# family_sha256 (filled once, later, in certificate rows)
KEY_COLS = ["t", "v", "k", "N", "tier", "source_id", "source_detail", "snapshot_id",
            "array_sha256", "verify_stamp", "entered"]
LOG_HEADER = ["date", "row_key", "t", "v", "k", "N", "tier", "source_id", "array_sha256",
              "family_sha256", "field", "old", "new", "reason", "requested_by"]


def row_key(r):
    s = "\x1f".join(str(r.get(c) or "") for c in KEY_COLS)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def log_path(table_dir):
    return os.path.join(table_dir, "CREDIT_CORRECTIONS.csv")


def read_log(table_dir):
    p = log_path(table_dir)
    if not os.path.isfile(p):
        return []
    with open(p, newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f)
        if rd.fieldnames != LOG_HEADER:
            raise SystemExit("%s header is %s, expected %s" % (p, rd.fieldnames, LOG_HEADER))
        return list(rd)


def latest(log):
    """(row_key, field) -> the last logged entry."""
    out = {}
    for e in log:
        out[(e["row_key"], e["field"])] = e
    return out


def check_log(rows, table_dir):
    """Problems: log entries whose row is gone, and corrected fields that no longer hold
    their last logged value (an unlogged change after a correction)."""
    probs = []
    try:
        log = read_log(table_dir)
    except SystemExit as e:
        return [str(e)]
    keys = {}
    for r in rows:
        keys.setdefault(row_key(r), []).append(r)
    for i, e in enumerate(log, 2):
        if e["field"] not in FIELDS:
            probs.append("CREDIT_CORRECTIONS.csv line %d: field %r is not a credit field" % (i, e["field"]))
        if e["row_key"] not in keys:
            probs.append("CREDIT_CORRECTIONS.csv line %d: no row of ca_table.csv has key %s"
                         % (i, e["row_key"]))
        elif len(keys[e["row_key"]]) > 1:
            probs.append("CREDIT_CORRECTIONS.csv line %d: key %s matches %d rows"
                         % (i, e["row_key"], len(keys[e["row_key"]])))
    for (k, field), e in latest(log).items():
        rs = keys.get(k) or []
        if len(rs) == 1 and (rs[0].get(field) or "") != e["new"]:
            probs.append("ca_table.csv row t=%s v=%s k=%s N=%s: %s differs from its last logged "
                         "correction (%s); correct it with tools/correct_credit.py"
                         % (e["t"], e["v"], e["k"], e["N"], field, e["date"]))
    return probs


def unlogged_changes(old_rows, new_rows, table_dir):
    """Credit fields of existing rows (same position, same key) changed between two tables
    with no log entry ending in the current value."""
    last = latest(read_log(table_dir))
    probs = []
    for i, (a, b) in enumerate(zip(old_rows, new_rows), 2):
        if row_key(a) != row_key(b):
            continue            # reported by the append-only check
        for f in FIELDS:
            if (a.get(f) or "") != (b.get(f) or ""):
                e = last.get((row_key(b), f))
                if e is None or e["new"] != (b.get(f) or ""):
                    probs.append("ca_table.csv line %d: %s changed with no line in "
                                 "table/CREDIT_CORRECTIONS.csv; use tools/correct_credit.py"
                                 % (i, f))
    return probs


def find_row(rows, spec, sha=None, source=None, tier=None):
    try:
        t, v, k, N = (x.strip() for x in spec.split(","))
    except ValueError:
        raise SystemExit("--row wants t,v,k,N")
    m = [r for r in rows if (r["t"], r["v"], r["k"], r["N"]) == (t, v, k, N)]
    if sha:
        sha = sha.lower()
        if len(sha) < 8:
            raise SystemExit("--sha needs at least 8 hex digits")
        m = [r for r in m if (r.get("array_sha256") or "").startswith(sha)
             or (r.get("family_sha256") or "").startswith(sha)]
    if source:
        m = [r for r in m if source in (r.get("source_detail") or "")]
    if tier:
        m = [r for r in m if r["tier"] == tier]
    if not m:
        raise SystemExit("no row matches %s%s%s%s" % (spec, " sha " + sha if sha else "",
                                                         " source " + repr(source) if source else "",
                                                         " tier " + tier if tier else ""))
    if len(m) > 1:
        lines = "\n".join("  %s %s %s sha=%s %s" % (r["tier"], r["source_id"], r["entered"],
                                                    (r.get("array_sha256") or r.get("family_sha256") or "-")[:12],
                                                    (r.get("source_detail") or "")[:70]) for r in m)
        raise SystemExit("%d rows match %s; narrow it with --sha or --source:\n%s" % (len(m), spec, lines))
    return m[0]


def new_value(r, a, refs):
    old = r.get(a.field) or ""
    if a.set is not None:
        new = a.set
    elif a.add or a.remove:
        if a.field != "builds_on":
            raise SystemExit("--add and --remove are for builds_on")
        parts = [p.strip() for p in old.split(";") if p.strip()]
        if a.add:
            if a.add in parts:
                raise SystemExit("%s is already in builds_on" % a.add)
            parts.append(a.add)
        if a.remove:
            if a.remove not in parts:
                raise SystemExit("%s is not in builds_on (%s)" % (a.remove, old))
            parts.remove(a.remove)
        new = ";".join(parts)
    elif a.replace:
        o, n = a.replace
        if old.count(o) != 1:
            raise SystemExit("%r occurs %d times in %s; it must occur once" % (o, old.count(o), a.field))
        new = old.replace(o, n)
    elif a.append:
        if a.field != "notes":
            raise SystemExit("--append is for notes")
        new = (old + "; " + a.append) if old else a.append
    else:
        raise SystemExit("say what to change: --set, --add, --remove, --replace or --append")
    if any(ch in new for ch in "\r\n"):
        raise SystemExit("the new value contains a line break")
    if new == old:
        raise SystemExit("nothing changes")
    if a.field == "builds_on" and new:
        ids, links, errs = bo.parse(new, refs)
        if errs:
            raise SystemExit("builds_on: " + "; ".join(errs))
    if a.field == "notes" and "credit: " in old and "credit: " not in new:
        print("warning: the notes no longer contain 'credit: '", file=sys.stderr)
    return old, new


def csv_line(values):
    buf = io.StringIO()
    csv.writer(buf, lineterminator="").writerow(values)
    return buf.getvalue()


def rewrite_row(table_path, target, field, new):
    """Replace the field on the one physical line of the row; every other byte stays."""
    raw = open(table_path, "rb").read().decode("utf-8")
    lines = raw.splitlines(keepends=True)
    header = next(csv.reader([lines[0]]))
    hit = []
    for i in range(1, len(lines)):
        body = lines[i].rstrip("\r\n")
        if not body:
            continue
        rec = next(csv.reader([body]))
        if len(rec) != len(header):
            raise SystemExit("ca_table.csv line %d does not parse as one record" % (i + 1))
        if dict(zip(header, rec)) == target:
            hit.append(i)
    if len(hit) != 1:
        raise SystemExit("the row is on %d lines of ca_table.csv, expected 1" % len(hit))
    i = hit[0]
    body = lines[i].rstrip("\r\n")
    eol = lines[i][len(body):]
    rec = dict(zip(header, next(csv.reader([body]))))
    rec[field] = new
    lines[i] = csv_line([rec[h] for h in header]) + eol
    with open(table_path, "w", encoding="utf-8", newline="") as f:
        f.write("".join(lines))
    return i + 1


def append_log(table_dir, entry):
    p = log_path(table_dir)
    new = not os.path.isfile(p)
    with open(p, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        if new:
            w.writerow(LOG_HEADER)
        w.writerow([entry[h] for h in LOG_HEADER])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--table-dir", default=os.path.join(REPO, "table"))
    ap.add_argument("--row")
    ap.add_argument("--sha")
    ap.add_argument("--source")
    ap.add_argument("--tier")
    ap.add_argument("--field", choices=FIELDS)
    ap.add_argument("--set")
    ap.add_argument("--add")
    ap.add_argument("--remove")
    ap.add_argument("--replace", nargs=2, metavar=("OLD", "NEW"))
    ap.add_argument("--append")
    ap.add_argument("--reason")
    ap.add_argument("--requested-by")
    ap.add_argument("--date")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    table_path = os.path.join(a.table_dir, "ca_table.csv")
    with open(table_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if a.check:
        probs = check_log(rows, a.table_dir)
        for p in probs:
            print("PROBLEM  " + p)
        print("credit corrections: %d logged, %d problems" % (len(read_log(a.table_dir)), len(probs)))
        return 1 if probs else 0
    if not (a.row and a.field and a.reason and a.requested_by):
        ap.error("--row, --field, --reason and --requested-by are required")
    refs = bo.load(a.table_dir)
    r = find_row(rows, a.row, a.sha, a.source, a.tier)
    old, new = new_value(r, a, refs)
    date = a.date or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    print("row: t=%s v=%s k=%s N=%s %s %s entered %s (key %s)"
          % (r["t"], r["v"], r["k"], r["N"], r["tier"], r["source_id"], r["entered"], row_key(r)))
    print("  %s before: %s" % (a.field, old))
    print("  %s after:  %s" % (a.field, new))
    print("  reason: %s; requested by %s; %s" % (a.reason, a.requested_by, date))
    if not a.apply:
        print("dry run; add --apply to write the table and the log")
        return 0
    line = rewrite_row(table_path, r, a.field, new)
    append_log(a.table_dir, dict(date=date, row_key=row_key(r), t=r["t"], v=r["v"], k=r["k"], N=r["N"],
                                 tier=r["tier"], source_id=r["source_id"],
                                 array_sha256=r.get("array_sha256") or "",
                                 family_sha256=r.get("family_sha256") or "", field=a.field,
                                 old=old, new=new, reason=a.reason, requested_by=a.requested_by))
    print("written: ca_table.csv line %d, and a line in table/CREDIT_CORRECTIONS.csv" % line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
