#!/usr/bin/env python3
"""add_tjim7.py - appends the 152 order-seven sizes of Torres-Jimenez and Izquierdo-Marquez 2024
(Mathematics 12(12) 1908, doi:10.3390/math12121908, Tables 4 to 7) to table/ca_table.csv as CITED
S7 rows. Usage, from the repository root:
    python3 tools/add_tjim7.py tools/tjim7_order_seven.csv YYYY-MM-DD
The csv has n,k,t,N,old_N,refined, read from the article's Tables 4 to 7 (refined: the number of
k at which the paper says N is a new bound). Each row's snapshot best is computed here from the
S1 rows, and a row that an array already in the table beats says so."""
import csv, io, sys, datetime, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import credit_text  # the one reader of a row's credit (to the first ';' outside parentheses)
SRC, DATE = sys.argv[1], sys.argv[2]
datetime.datetime.strptime(DATE, "%Y-%m-%d")
DOI = "doi:10.3390/math12121908"
TABLE_OF_T = {3: 4, 4: 5, 5: 6, 6: 7}
raw = open("table/ca_table.csv", "rb").read().decode("utf-8")
lines = raw.split("\r\n"); assert lines[-1] == ""
rows = list(csv.reader(lines[:-1]))
hdr = rows[0]; assert hdr[:5] == ["t", "v", "k", "N", "tier"]
if any(r[7] == DOI for r in rows[1:]):
    sys.exit("the order-seven rows are already in the table")
s1 = [(int(r[0]), int(r[2]), int(r[3])) for r in rows[1:] if r[5] == "S1" and r[1] == "7"]
ver = [(int(r[0]), int(r[2]), int(r[3]), r[10], r[11]) for r in rows[1:] if r[4] == "VERIFIED" and r[1] == "7"]
def snap(t, k):
    return min(n for tt, kk, n in s1 if tt == t and kk >= k)
new = []
for d in csv.DictReader(open(SRC, newline="")):
    n, k, t, N, old = int(d["n"]), int(d["k"]), int(d["t"]), int(d["N"]), int(d["old_N"])
    sb = snap(t, k); assert N < sb, (t, k, N, sb)
    tab = TABLE_OF_T[t]
    beat = sorted((vn, -vk, ent, note) for vt, vk, vn, ent, note in ver if vt == t and vk >= k and vn <= N)
    if beat:
        vn, vk, ent, note = beat[0]
        who = credit_text.credit(note) or "a verified array"
        extra_beat = ("; a verified %d at k = %d (%s, entered %s) was already in the table, so this row "
                      "is not the best known" % (vn, -vk, who, ent))
    else:
        extra_beat = ""
    notes = ("credit: J. Torres-Jimenez and I. Izquierdo-Marquez 2024 (the CPHF and the size, %s, Table %d); "
             "exceeds snapshot rung (snapshot best %d at this k)%s%s; no array published, the CPHFs are "
             "available from the corresponding author on request"
             % (DOI, tab, sb, "" if old == sb else
                "; the paper lists %d as the previous value here, the snapshot's at a larger k" % old, extra_beat))
    new.append([t, 7, k, N, "CITED", "S7",
                "Torres-Jimenez and Izquierdo-Marquez 2024, Mathematics 12(12) 1908, Table %d, CPHF(%d; %d, 7, %d)"
                % (tab, n, k, t),
                DOI, "", "", DATE, notes, "", "",
                "covering perfect hash family CPHF(%d; %d, 7, %d) found by the authors' greedy column extension algorithm "
                "(Torres-Jimenez and Izquierdo-Marquez 2024), converted to a covering array of "
                "%d * 7^%d rows less repeated rows" % (n, k, t, n, t)])
assert len(new) == 152
b = io.StringIO(); w = csv.writer(b, lineterminator="\r\n")
for r in new: w.writerow(r)
open("table/ca_table.csv", "wb").write((raw + b.getvalue()).encode("utf-8"))
print("152 CITED S7 rows added; date", DATE)
