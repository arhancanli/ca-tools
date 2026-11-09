#!/usr/bin/env python3
"""build_frame - write table/ca_frame.csv, the best known sizes under the frame rule, and
table/ca_table.csv.gz, a gzipped copy of table/ca_table.csv.

The frame rule (table/CONVENTIONS.md, section 4) counts what the Colbourn rule counts (the rows of
table/ca_table.py counted(): CITED and VERIFIED, less retracted rows) plus proven derived sizes
(section 6). The proven size rules used here are exactly two, both from Colbourn, Keri, Rivas
Soriano and Schlage-Puchta 2010:
  fuse    Lemma 3.1: CAN(t, k, v) <= CAN(t, k, v + 1) - 2 (one symbol fused; done m times for m
          symbols, written fuse:fuse:...)
  derive  (7): CAN(t, k, v) <= floor(CAN(t + 1, k + 1, v) / v)
add1 is not implemented (no add1 law exists in tools/derive_laws.py yet), so no size here uses it.
The rules are applied repeatedly to the counted rows, and to the sizes they give, until nothing
changes. Fuse lowers v at the same k and derive lowers t at k - 1, so every derived size sits at
the width of the row it comes from or one less: past the baseline's column range a derived size
appears only where a counted row of that width (or one more) is, and no ladder of widths is
evaluated (tools/derive_table.py does that for table/derived.csv). A CITED row that has a DISPUTED
row beside it (today the three cyclotomy rows (3, 6, 128, 762), (3, 20, 2162, 43220) and
(3, 21, 2312, 48531)) is still counted as a row but is never the input of a derived size.

ca_frame.csv has one line per stair step under the frame rule, sorted by t, v, k. The steps are
those of the page (tools/render_table.py stair()): for each (t, v), a step is a pair (k, N) where N
is the smallest value at any k' >= k and k is the largest width with that value. A line is
"row" when a counted row reaches N at that point, else "derived" (a derived size strictly below
every counted row at k' >= k). The columns (CONVENTIONS.md, section 7):

  t, v, k, N          the step, as in ca_table.csv (the five columns CAs reads are t, v, k, N and
                      construction, with the same meaning)
  basis               row or derived
  tier                the tier of the named row; for a derived step the tier of its source row
                      (its weakest input: fuse and derive have one input each)
  id                  the id of the named row (below); empty for a derived step, which is not a row
  constant_rows       the exact count of the named row's array (table/MANIFEST.csv), or empty
  constant_rows_basis exact where constant_rows is filled, else empty
  get                 where the named row's array is: file (table/arrays), deposit (table/EXTERNAL.csv),
                      certificate (table/certificates), construction (table/constructions), cas (a
                      function of the CAs package that the row names), url (the NIST library, Dwyer's
                      CA_Database), none (every CITED row, every row whose array file was withdrawn,
                      table/withdrawn_files.csv, any other row whose array is nowhere the table can
                      point to, and every derived step: a derived size is not an array in hand).
                      One exception: when the named row has none but another counted VERIFIED row
                      tied at the same step (same t, v, k, N) has an array, get and get_ref are
                      taken from the first such row in headline order; id, tier, constant_rows and
                      construction stay those of the named row, and that row is in ids_all.
  get_ref             the locator: the file path, the deposit link, the URL, the R call, or the
                      command that rebuilds the array; empty when get is none
  construction        the named row's construction label; for a derived step its working in the form
                      CAs shows in its Source column: the source row's own construction label
                      followed by one ':fuse' or ':derive' per step, in the order applied (for
                      example RMScopiesCA:fuse:fuse). The source row's id is in ids_all. To split a
                      working, remove the trailing ':fuse' and ':derive' pieces: there are exactly
                      (t of the source - t) derive steps and (v of the source - v) fuse steps, and no
                      source label ends in ':fuse' or ':derive' (consistency.py checks), so a colon
                      inside a label is never taken for a step. A label with a comma or a quote is
                      quoted as CSV quotes it (R read.csv reads it whole). A source row without a
                      label would be written by its id instead (none today).
  family              empty for now (the family list of section 8 does not exist yet)
  constructions_all   every counted row reaching N at the step, in headline order, separated by
                      " || "; for a derived step every working reaching N, each in the label form
  ids_all             the ids of the same rows, in the same order, separated by ";"; for a derived
                      step the source row of each working (the same source may appear twice)
  prev_id             the previous best at the step (below), or empty
  entered             the named row's entry date; for a derived step its source row's
  generated           the latest entry date in ca_table.csv when the file was built (so a rebuild
                      of an unchanged table gives the same bytes)

Ids. Every row of ca_table.csv has one, t<t>-v<v>-k<k>-<n>, where n counts the rows at that point
(t, v, k) in file order, starting at 1. As the table is append-only, an id never changes.

Headline (the named row among those reaching N, section 9): a CITED row first, then more constant
rows, then the earlier entry date, then the wider array, then the id (file order). Derived
workings are ordered by their source row in the same order, then the shorter working.

prev_id. For a row step: let F be the first row reaching N or less at k' >= k (by file order, the
rows of one snapshot entered on one day counting as one entry, so the 13,641 baseline rows have no
order among them). prev_id is the named row of the best value over the counted rows entered before
F at k' >= k, empty when there is none (so every step set by the baseline has an empty prev_id).
For a derived step: prev_id is the named row of the Colbourn-rule value at the step (what the
step improves on, as lookup_N in table/derived.csv), empty past every counted row. Past every
counted row of its t and v, a derived step is kept only when its working uses fuse alone. prev_id names
rows only; derived sizes have no id.

Usage: build_frame.py [--table-dir DIR] [--check] [--stats]
  (default)  write DIR/ca_frame.csv and DIR/ca_table.csv.gz (gzip without name or time, level 9)
  --check    build in memory and fail if ca_frame.csv differs or ca_table.csv.gz does not
             decompress to ca_table.csv
  --stats    also print the counts (lines, derived steps, steps that differ from the Colbourn rule)
Standard library only.
"""
import collections
import csv
import gzip
import io
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "table"))
from ca_table import counted  # noqa: E402  (the one definition of the counted rows)

FRAME_HEADER = ["t", "v", "k", "N", "basis", "tier", "id", "constant_rows", "constant_rows_basis",
                "get", "get_ref", "construction", "family", "constructions_all", "ids_all", "prev_id",
                "entered", "generated"]
GET_VALUES = ("file", "deposit", "url", "cas", "certificate", "construction", "none")
BASIS_VALUES = ("row", "derived")
CR_BASIS_VALUES = ("exact", "lower_bound", "inherited")
ALL_SEP = " || "
ID_RE = re.compile(r"^t[2-9]-v[0-9]+-k[0-9]+-[0-9]+$")
NIST = "https://math.nist.gov/coveringarrays/ipof/cas/t=%s/v=%s/%s"         # as CAs::nistCA builds it
DWYER = "https://raw.githubusercontent.com/aadwyer/CA_Database/main/Repository/CA/%s"   # CAs::dwyerCA
CAS_CALL = re.compile(r"^(CAs::(?!nistCA|dwyerCA)\w+\([^)]*\))")
INF = 10 ** 30


def read_csv(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def row_ids(rows):
    """the id of every row: t<t>-v<v>-k<k>-<n>, n the row's number at its point in file order"""
    seen = collections.Counter()
    out = []
    for r in rows:
        p = (int(r["t"]), int(r["v"]), int(r["k"]))
        seen[p] += 1
        out.append("t%d-v%d-k%d-%d" % (p + (seen[p],)))
    return out


def frame_label(r, rid):
    """the label a frame working uses for row r: its construction, or its id when the label is empty, contains
    the separator " || " or ends in ':fuse'/':derive', so a working always splits unambiguously"""
    c = construction_of(r)
    if not c or ALL_SEP in c or re.search(r":(fuse|derive)$", c):
        return rid
    return c


def construction_of(r):
    """the construction column; a CITED row from before that column has its label in source_detail"""
    c = (r.get("construction") or "").strip()
    if not c and r["tier"] == "CITED":
        c = (r.get("source_detail") or "").strip()
    return c


class Context:
    """the table and the files that say where arrays are"""

    def __init__(self, table_dir):
        self.dir = table_dir
        self.rows = read_csv(os.path.join(table_dir, "ca_table.csv"))
        self.ids = row_ids(self.rows)
        self.man = {m["sha256"]: m for m in read_csv(os.path.join(table_dir, "MANIFEST.csv"))}
        self.ext = {e["sha256"]: e for e in read_csv(os.path.join(table_dir, "EXTERNAL.csv"))}
        self.withdrawn = {w["sha256"] for w in read_csv(os.path.join(table_dir, "withdrawn_files.csv"))}
        self.certs = read_csv(os.path.join(table_dir, "certificates", "CERTIFICATES.csv"))
        self.cons = read_csv(os.path.join(table_dir, "constructions", "CONSTRUCTIONS.csv"))
        self.cons_by_sha = {c["array_sha256"]: c for c in self.cons if c.get("array_sha256")}
        self.index = {id(r): i for i, r in enumerate(self.rows)}
        # batch position: the rows of one snapshot entered on one day are one entry
        first = {}
        self.pos = []
        for i, r in enumerate(self.rows):
            key = (r.get("snapshot_id") or "", r.get("entered") or "")
            if key[0]:
                self.pos.append(first.setdefault(key, i))
            else:
                self.pos.append(i)
        self.generated = max((r.get("entered") or "" for r in self.rows), default="")

    def cert_of(self, r):
        for c in self.certs:
            if (r["t"], r["v"], r["k"], r["N"]) != (c["t"], c["v"], c["k"], c["N"]):
                continue
            if r.get("family_sha256") and r["family_sha256"] != c.get("family_sha256"):
                continue
            if c.get("array_sha256"):
                if r["array_sha256"] == c["array_sha256"]:
                    return c
            elif not r["array_sha256"] and r.get("family_sha256") and r["family_sha256"] == c.get("family_sha256"):
                return c
        return None

    def get_of(self, r):
        """(get, get_ref) for one row"""
        if r["tier"] != "VERIFIED":
            return "none", ""
        sha = r.get("array_sha256") or ""
        if sha and sha in self.man:
            return "file", "table/arrays/" + self.man[sha]["file"]
        if sha and sha in self.ext:
            return "deposit", self.ext[sha]["location"]
        c = self.cert_of(r)
        if c is not None:
            m = re.match(r"^CPHF\((\d+); (\d+), (\d+), (\d+)\)", c.get("family") or "")
            q = m.group(3) if m else r["v"]
            exp = c.get("expansion") or "smc-1"
            cmd = "tools/cphf/cphfcheck table/certificates/%s %s %s expand CA.txt%s" % (
                c["file"], r["t"], q, " affine" if exp.startswith("smc-1-affine") else "")
            steps = re.findall(r"\+(fuse \d+>\d+|fuse2 \d+)", exp)
            if steps:
                cmd += ", then " + ", then ".join(steps) + " (tools/cphf_cert.py, expansion %s)" % exp
            return "certificate", cmd
        if sha and sha in self.cons_by_sha:
            return "construction", ("python3 tools/construction_cert.py table/constructions/%s --write CA.txt"
                                    % self.cons_by_sha[sha]["file"])
        if sha and sha in self.withdrawn:
            return "none", ""
        sd = r.get("source_detail") or ""
        m = CAS_CALL.match(sd)
        if m:
            return "cas", m.group(1)
        parts = sd.split(" via ")[0].split()
        if r["source_id"] == "S4" and len(parts) == 3 and parts[0] == "math.nist.gov/coveringarrays":
            return "url", NIST % (r["t"], r["v"], parts[2])
        if r["source_id"] == "S5" and len(parts) == 2 and parts[0] == "aadwyer/CA_Database":
            return "url", DWYER % parts[1]
        return "none", ""

    def constant_rows(self, r, get):
        if get == "file":
            c = self.man[r["array_sha256"]].get("constant_rows") or ""
            if c.isdigit():
                return c, "exact"
        return "", ""

    def headline_key(self, i):
        """section 9: CITED first, more constant rows, earlier entry, wider array, file order"""
        r = self.rows[i]
        get, _ = self.get_of(r)
        c, _ = self.constant_rows(r, get)
        return (r["tier"] != "CITED", -(int(c) if c else -1), r.get("entered") or "", -int(r["k"]), i)


def excluded_inputs(rows):
    """CITED rows with a DISPUTED row beside them (same t, v, k, N): counted, never an input"""
    disputed = {(r["t"], r["v"], r["k"], r["N"]) for r in rows if r["tier"] == "DISPUTED"}
    return {i for i, r in enumerate(rows) if r["tier"] == "CITED" and (r["t"], r["v"], r["k"], r["N"]) in disputed}


def closure(points, derive=True):
    """points: {(t, v, k): [(N, row index)]} of the input rows. Applies fuse and derive until nothing
    changes. Fuse goes from v + 1 to v and derive from t + 1 to t, so one pass over (t, v) in
    decreasing order reaches the fixpoint. Returns {(t, v): {k: (N, [(row index, working)])}} of the
    smallest value at each point (rows and derived sizes together), every way of reaching it kept.
    With derive=False only fuse is applied."""
    by = collections.defaultdict(dict)
    for (t, v, k), lst in points.items():
        n = min(x[0] for x in lst)
        by[(t, v)][k] = (n, sorted((i, ()) for x, i in lst if x == n))
    if not by:
        return {}
    tmax = max(t for t, v in by)
    vmax = max(v for t, v in by)
    out = {}
    for t in range(tmax, 1, -1):
        for v in range(vmax, 1, -1):
            cur = {k: (n, list(o)) for k, (n, o) in by.get((t, v), {}).items()}

            def offer(k, n, origins):
                if k not in cur or n < cur[k][0]:
                    cur[k] = (n, list(origins))
                elif n == cur[k][0]:
                    cur[k][1].extend(origins)
            for k, (n, origins) in out.get((t, v + 1), {}).items():           # fuse one symbol
                offer(k, n - 2, [(i, w + ("fuse",)) for i, w in origins])
            if derive and t + 1 <= tmax:
                for k, (n, origins) in out.get((t + 1, v), {}).items():       # derive
                    if k - 1 > t:
                        offer(k - 1, n // v, [(i, w + ("derive",)) for i, w in origins])
            if cur:
                out[(t, v)] = {k: (n, sorted(set(o))) for k, (n, o) in cur.items()}
    return out


def stair_steps(values):
    """values {k: N} -> [(k, N)] steps, k increasing: N smallest at any k' >= k, k largest with it"""
    steps, m = [], INF
    for k in sorted(values, reverse=True):
        if values[k] < m:
            steps.append((k, values[k]))
            m = values[k]
    return steps[::-1]


def build(table_dir):
    """the frame lines (lists of strings, FRAME_HEADER order) and the counts"""
    ctx = Context(table_dir)
    rows = ctx.rows
    cnt = [ctx.index[id(r)] for r in counted(rows)]
    excl = excluded_inputs(rows)
    rowpts = collections.defaultdict(list)      # every counted row, by point
    inputs = collections.defaultdict(list)      # the inputs of the derived sizes
    for i in cnt:
        r = rows[i]
        p = (int(r["t"]), int(r["v"]), int(r["k"]))
        rowpts[p].append((int(r["N"]), i))
        if i not in excl:
            inputs[p].append((int(r["N"]), i))
    clo = closure(inputs)
    clo_fuse = closure(inputs, derive=False)
    by_tv = collections.defaultdict(dict)       # (t, v) -> {k: row min N}
    rows_tv = collections.defaultdict(list)     # (t, v) -> counted row indices
    for (t, v, k), lst in rowpts.items():
        by_tv[(t, v)][k] = min(x[0] for x in lst)
        rows_tv[(t, v)].extend(i for _, i in lst)
    lines, stats = [], collections.Counter()
    hk = {}

    def hkey(i):
        if i not in hk:
            hk[i] = ctx.headline_key(i)
        return hk[i]

    def best_row(cands):
        """the named row among (N, index) candidates: smallest N, then headline order"""
        return min(cands, key=lambda x: (x[0], hkey(x[1]))) if cands else None

    for tv in sorted(set(by_tv) | set(clo)):
        t, v = tv
        rmin = by_tv.get(tv, {})
        dmin = {}
        kmax = max(rmin, default=0)
        # past every counted row of (t, v) only fuse counts for now (CONVENTIONS.md section 6: derived
        # points beyond the counted range come later); derive there gives sizes far above known values
        # (t = 2, v = 2 at k = 99,999: 252 against the exact 21). The fuse-only closure gives those.
        pts = {k: x for k, x in clo.get(tv, {}).items() if k <= kmax}
        pts.update((k, x) for k, x in clo_fuse.get(tv, {}).items() if k > kmax)
        for k, (n, origins) in pts.items():
            der = [o for o in origins if o[1]]
            if der and (k not in rmin or n < rmin[k]):
                dmin[k] = (n, der)
        frame_vals = dict(rmin)
        for k, (n, _) in dmin.items():
            frame_vals[k] = n
        colb_steps = set(stair_steps(rmin))
        rtv = rows_tv.get(tv, [])
        for k, n in stair_steps(frame_vals):
            stats["lines"] += 1
            if (k, n) not in colb_steps:
                stats["changed"] += 1
            if k in dmin:
                stats["derived"] += 1
                origins = sorted(dmin[k][1], key=lambda o: (hkey(o[0]), len(o[1]), o[1]))
                src = rows[origins[0][0]]
                works = ["%s:%s" % (frame_label(rows[i], ctx.ids[i]), ":".join(w)) for i, w in origins]
                prev = best_row([(int(rows[i]["N"]), i) for i in rtv if int(rows[i]["k"]) >= k])
                if prev is None:
                    stats["derived_no_counted"] += 1
                if rows[origins[0][0]]["tier"] == "VERIFIED":
                    stats["derived_verified"] += 1
                lines.append([str(t), str(v), str(k), str(n), "derived", src["tier"], "", "", "", "none", "",
                              works[0], "", ALL_SEP.join(works), ";".join(ctx.ids[i] for i, _ in origins),
                              ctx.ids[prev[1]] if prev else "", src.get("entered") or "", ctx.generated])
                continue
            tied = sorted((i for i in rtv if int(rows[i]["k"]) == k and int(rows[i]["N"]) == n), key=hkey)
            named = rows[tied[0]]
            get, ref = ctx.get_of(named)
            crn, crb = ctx.constant_rows(named, get)
            if get == "none":
                # decision of 2026-11-09: a tied counted VERIFIED row with an array lends its get
                for i in tied[1:]:
                    g2 = ctx.get_of(rows[i])
                    if rows[i]["tier"] == "VERIFIED" and g2[0] != "none":
                        get, ref = g2
                        stats["get_from_tied_row"] += 1
                        break
            first = min((i for i in rtv if int(rows[i]["k"]) >= k and int(rows[i]["N"]) <= n),
                        key=lambda i: ctx.pos[i])
            before = [(int(rows[i]["N"]), i) for i in rtv
                      if int(rows[i]["k"]) >= k and ctx.pos[i] < ctx.pos[first]]
            prev = best_row(before)
            if prev:
                stats["row_with_prev"] += 1
            lines.append([str(t), str(v), str(k), str(n), "row", named["tier"], ctx.ids[tied[0]], crn, crb, get, ref,
                          construction_of(named), "", ALL_SEP.join(frame_label(rows[i], ctx.ids[i]) for i in tied),
                          ";".join(ctx.ids[i] for i in tied), ctx.ids[prev[1]] if prev else "",
                          named.get("entered") or "", ctx.generated])
            stats["get_" + get] += 1
        stats["colbourn_steps"] += len(colb_steps)
    return lines, stats, ctx


def frame_text(lines):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
    w.writerow(FRAME_HEADER)
    w.writerows(lines)
    return buf.getvalue()


def gz_bytes(raw):
    """gzip of raw with no file name and time 0 (as gzip -n), level 9: the same bytes on every run"""
    buf = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=buf, compresslevel=9, mtime=0) as g:
        g.write(raw)
    return buf.getvalue()


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    table_dir = os.path.join(REPO, "table")
    if "--table-dir" in argv:
        table_dir = argv[argv.index("--table-dir") + 1]
    t0 = time.time()
    lines, stats, ctx = build(table_dir)
    text = frame_text(lines)
    fpath = os.path.join(table_dir, "ca_frame.csv")
    gpath = os.path.join(table_dir, "ca_table.csv.gz")
    raw = open(os.path.join(table_dir, "ca_table.csv"), "rb").read()
    if "--stats" in argv:
        for k in sorted(stats):
            print("%s: %d" % (k, stats[k]))
        print("build: %.1f s" % (time.time() - t0))
    if "--check" in argv:
        bad = []
        if not os.path.exists(fpath) or open(fpath, encoding="utf-8", newline="").read() != text:
            bad.append("%s is out of date; run python3 tools/build_frame.py" % fpath)
        try:
            same = gzip.decompress(open(gpath, "rb").read()) == raw
        except (OSError, EOFError):
            same = False
        if not same:
            bad.append("%s does not decompress to ca_table.csv; run python3 tools/build_frame.py" % gpath)
        for b in bad:
            print(b)
        if not bad:
            print("%s and %s are current (%d lines)" % (fpath, gpath, len(lines)))
        return 1 if bad else 0
    with open(fpath, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    gz = gz_bytes(raw)
    with open(gpath, "wb") as f:
        f.write(gz)
    print("wrote %s: %d steps (%d derived); %s: %d bytes" % (fpath, len(lines), stats["derived"], gpath, len(gz)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
