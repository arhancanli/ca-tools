#!/usr/bin/env python3
"""build_frame - write table/ca_frame.csv, the best known sizes under the frame rule, and
table/ca_table.csv.gz, a gzipped copy of table/ca_table.csv.

The frame rule (table/CONVENTIONS.md, section 4) counts what the Colbourn rule counts (the rows of
table/ca_table.py counted(): CITED and VERIFIED, less retracted rows) plus proven derived sizes
(section 6). The proven size rules used here are exactly three, all from Colbourn, Keri, Rivas
Soriano and Schlage-Puchta 2010 (CKRS):
  fuse    Lemma 3.1: CAN(t, k, v) <= CAN(t, k, v + 1) - 2 (one symbol fused; done m times for m
          symbols, written fuse:fuse:...)
  derive  (7): CAN(t, k, v) <= floor(CAN(t + 1, k + 1, v) / v)
  add1    Theorem 3.2, (8): CAN(t, k + 1, v) <= CAN(t, k, v) + v(v - 1) CAN(t - 2, k - 1, v) (one column
          added; Colbourn's label "Add 1 factors"), used for t >= 3 (valid for every t >= 2: copy a column,
          then for each ordered pair of distinct symbols in the two copies append a strength t - 2 array
          on the other columns). For t >= 4 its second input, the strength t - 2 ingredient, is a table
          row (or a row fused or derived); for t = 3 it is the trivial CA(v; 1, k - 1, v), v constant rows
The rules are applied repeatedly to the counted rows, and to the sizes they give, until nothing
changes. Fuse lowers v at the same k, derive lowers t at k - 1, and add1 keeps t and v at k + 1 (it may
repeat: k + 1, k + 2, ...). The ingredient of an add1 step at t >= 4 is the smallest size at strength
t - 2 and width k - 1 or more (k the width before the step) under fuse and derive alone: a row, or a row
fused or derived, never itself made by add1; among ingredients of that size a VERIFIED row comes first. Every derived size has the width of the row it comes from, less one
per derive step, plus one per add1 step. Past every counted row of its t and v a derived size counts
only when it is made by fuse alone, so no line there ends in an add1 or derive step (a working may pass
through such a point on its way to a point inside the counted range of another t or v), and only when
no line of table/derived.csv at the same t and v, at a width k' >= k, by any size rule counted or not,
has a smaller N (section 6, version 1.3). An uncounted rule there only withholds a size, never gives
one; without a derived.csv beside the table nothing is withheld. The counted range of a t and v ends at its
widest counted row, except that a row past the baseline's column range whose N is above a line of derived.csv at
a width k' >= k does not widen it (version 1.4): the row counts, but the derived sizes between the range and that
row are judged as past the range, so a weak row does not let in sizes that derived.csv beats (a CA(1000; 3,
100000, 2) would have let in 231 lines of 80 to 996 against PCT 77 to 99). So past the baseline's column range
a derived size appears only near the counted rows entered there (at a row's width, one less per derive
step, one more per add1 step), and no ladder of widths is evaluated (tools/derive_table.py does that
for table/derived.csv). A CITED row that has a DISPUTED
row beside it (today the three cyclotomy rows (3, 6, 128, 762), (3, 20, 2162, 43220) and
(3, 21, 2312, 48531)) is still counted as a row but is never an input of a derived size (neither the
source nor an add1 ingredient).

ca_frame.csv has one line per stair step under the frame rule, sorted by t, v, k. The steps are
those of the page (tools/render_table.py stair()): for each (t, v), a step is a pair (k, N) where N
is the smallest value at any k' >= k and k is the largest width with that value. A line is
"row" when a counted row reaches N at that point, else "derived" (a derived size strictly below
every counted row at k' >= k). The columns (CONVENTIONS.md, section 7):

  t, v, k, N          the step, as in ca_table.csv (the five columns CAs reads are t, v, k, N and
                      construction, with the same meaning)
  basis               row or derived
  tier                the tier of the named row; for a derived step the weakest tier among its rows (the
                      source row and the ingredient row of each add1 step): CITED if one of them is
                      CITED, else VERIFIED
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
  construction        the named row's construction label; for a derived step its working: the source
                      row's own construction label followed by one ':fuse', ':derive' or ':add1' per
                      step, in the order applied (for example Sherwood covering perfect hash family
                      (affine):fuse:fuse, or SCPHF Random Extension (CLS):add1). Close to CAs's Source
                      labels, but the order may mix steps (':fuse:add1', ':derive:fuse'), which CAs
                      0.25's labels never do. The source row's id is in ids_all, followed by the id of
                      each add1 step's ingredient row (t >= 4; a t = 3 step names none). To split a
                      working, remove the trailing ':fuse', ':derive' and ':add1' pieces: there are
                      exactly (t of the source - t) derive steps, (v of the source - v) fuse steps and
                      (k - k of the source + t of the source - t) add1 steps, and no source label ends
                      in one of them (consistency.py checks, and recomputes N from the rows), so a
                      colon inside a label is never taken for a step. A label with a comma or a quote is
                      quoted as CSV quotes it (R read.csv reads it whole). A source row whose label
                      is empty, contains " || " or ends in ':fuse', ':derive' or ':add1' is written
                      by its id instead (frame_label; also in constructions_all of a row line).
  family              empty for now (the family list of section 8 does not exist yet)
  constructions_all   every counted row reaching N at the step, in headline order, separated by
                      " || "; for a derived step every working reaching N, each in the label form
  ids_all             the ids of the same rows, in the same order, separated by ";"; for a derived
                      step, for each working, its source row, then "+" and the ingredient row of each
                      add1 step at t >= 4 in step order (for example t6-v8-k237-1+t4-v8-k274-2; the same row may
                      appear more than once). The ingredient is credited here only: its own fuse or
                      derive steps are not written, and are recomputed from its row by consistency.py.
                      Among ingredients of equal size a VERIFIED row is named first, then headline
                      order.
  prev_id             the previous best at the step (below), or empty
  entered             the named row's entry date; for a derived step the latest entry date among its rows
                      (as for tier)
  generated           the latest entry date in ca_table.csv when the file was built (so a rebuild
                      of an unchanged table gives the same bytes)

Ids. Every row of ca_table.csv has one, t<t>-v<v>-k<k>-<n>, where n counts the rows at that point
(t, v, k) in file order, starting at 1. As the table is append-only, an id never changes.

Headline (the named row among those reaching N, section 9): a CITED row first, then more constant
rows (an unknown count ranks below every known one), then the earlier entry date, then the wider array, then the id (file order). Derived
workings are ordered by their source row in the same order, then the shorter working.

prev_id. For a row step: let F be the first row reaching N or less at k' >= k (by file order, the
rows of one snapshot entered on one day counting as one entry, so the 13,641 baseline rows have no
order among them). prev_id is the named row of the best value over the counted rows entered before
F at k' >= k, empty when there is none (so every step set by the baseline has an empty prev_id).
For a derived step: prev_id is the named row of the Colbourn-rule value at the step (what the
step improves on, as lookup_N in table/derived.csv). Past every counted row of its t and v it is the
named row at the widest counted width when the step's N is below the counted value there (for example
CA(13115; 3, 11288, 12) below 13,151 at k = 10,000), else empty. Past the counted range of its t and v,
a derived step is kept only when its working uses fuse alone and derived.csv has nothing smaller at
k' >= k (above). prev_id names rows only; derived sizes have no id.

Usage: build_frame.py [--table-dir DIR] [--check] [--stats]
  (default)  write DIR/ca_frame.csv and DIR/ca_table.csv.gz (gzip without name or time, level 9)
  --check    build in memory and fail if ca_frame.csv differs or ca_table.csv.gz does not
             decompress to ca_table.csv
  --stats    also print the counts (lines, derived steps, steps that differ from the Colbourn rule,
             derived_vetoed: steps past the counted range withheld because derived.csv has less,
             range_rows_left_out: counted rows that do not widen the counted range)
Standard library only.
"""
import bisect
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
    the separator " || " or ends in ':fuse', ':derive' or ':add1', so a working always splits unambiguously"""
    c = construction_of(r)
    if not c or ALL_SEP in c or re.search(r":(fuse|derive|add1)$", c):
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


ADD1_TMIN = 3   # at t = 3 the strength 1 ingredient is the trivial CA(v; 1, k, v) (v constant rows), no row


def ingredient_stairs(clo, rank):
    """for the add1 ingredients: {(t, v): (ks, best)} with best[i] the smallest value at any point k' >= ks[i] of
    clo[(t, v)] and its first origin by rank among every origin reaching that value there"""
    out = {}
    for tv, pts in clo.items():
        ks = sorted(pts)
        best, cur = [None] * len(ks), None
        for i in range(len(ks) - 1, -1, -1):
            n, origins = pts[ks[i]]
            cand = (n, min(origins, key=rank))
            if cur is None or n < cur[0] or (n == cur[0] and rank(cand[1]) < rank(cur[1])):
                cur = cand
            best[i] = cur
        out[tv] = (ks, best)
    return out


def closure(points, derive=True, ingredients=None, rank=None, kmax=None):
    """points: {(t, v, k): [(N, row index)]} of the input rows. Applies fuse and derive (and add1 when
    ingredients is given) until nothing changes. Fuse goes from v + 1 to v and derive from t + 1 to t, so one
    pass over (t, v) in decreasing order reaches the fixpoint. Returns {(t, v): {k: (N, [(row index,
    working)])}} of the smallest value at each point (rows and derived sizes together), every way of reaching it
    kept; a working is a tuple of steps "fuse", "derive", "add1/<j>" (t >= 4) or "add1" (t = 3).
    With derive=False only fuse is applied.
    add1 (CKRS 2010 Theorem 3.2): CAN(t, k + 1, v) <= CAN(t, k, v) + v(v - 1) CAN(t - 2, k - 1, v), t >= 3. The
    main input is a point of (t, v) itself, so add1 runs inside the pass at (t, v), in increasing k, and may
    repeat (k, k + 1, k + 2, ...). For t >= 4 the ingredient CAN(t - 2, k - 1, v) is the smallest value at any
    k' >= k - 1 of ingredients, the closure under fuse and derive alone (so an ingredient is a row, or a row fused
    or derived, never itself made by add1), and j in "add1/<j>" is its source row (the first by rank among ties);
    for t = 3 it is v, the trivial CA(v; 1, k - 1, v), and the step is "add1".
    A size from add1 is dropped where a size at the same k is smaller. A chain stops only once it can no longer
    count anywhere (a bound, not a guess, so every step of the rule is found): kmax gives the largest counted k
    of each (t, v); a point (t, v, k, m) can lead only to sizes of at least m // v^(t - t') - 2(v - v') at
    (t', v', k') with t' <= t, v' <= v and k' >= k - (t - t') (fuse takes 2, derive divides by at most v, add1
    adds), past every counted row of (t', v') only fuse-only workings count, and the input rows' stair never
    falls as k grows, so a chain stops once that bound is not below the stair at the widest counted width
    kmax(t', v') of every such (t', v') with k - (t - t') <= kmax(t', v'). No chain runs past every input row's
    width plus tmax. (A chain is not stopped because a smaller size sits at a wider k of its own (t, v): the two
    can derive or fuse to opposite sides of a counted range.)"""
    by = collections.defaultdict(dict)
    for (t, v, k), lst in points.items():
        n = min(x[0] for x in lst)
        by[(t, v)][k] = (n, sorted((i, ()) for x, i in lst if x == n))
    if not by:
        return {}
    tmax = max(t for t, v in by)
    vmax = max(v for t, v in by)
    kcap = max(k for pts in by.values() for k in pts) + tmax     # no chain is useful past every input row's width
    ing = ingredient_stairs(ingredients, rank) if ingredients is not None else None
    rst = {}                                                                  # the input rows' stair steps
    for tv, pts in by.items():
        ks = sorted(pts)
        suf, m = [0] * len(ks), INF
        for i in range(len(ks) - 1, -1, -1):
            m = min(m, pts[ks[i]][0])
            suf[i] = m
        rst[tv] = (ks, suf)

    def useful(t, v, k, m):
        """can the size m at (t, v, k) still lead to a counted size below the input rows somewhere?"""
        if kmax is None:
            return True
        for t2 in range(t, 1, -1):
            k2 = k - (t - t2)
            for v2 in range(v, 1, -1):
                if k2 > kmax.get((t2, v2), 0):
                    continue                          # past every counted row there: add1 workings do not count
                low = m // v ** (t - t2) - 2 * (v - v2)
                # the size may land at any width k' from k2 to kmax(t2, v2) (add1 steps widen it); the stair
                # never falls as k grows, so the test is against the stair at the widest counted width
                ks, suf = rst.get((t2, v2), ((), ()))
                x = bisect.bisect_left(ks, kmax[(t2, v2)])
                if x >= len(ks) or low < suf[x]:
                    return True
        return False

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
            if ing is not None and t >= ADD1_TMIN and (t == 3 or (t - 2, v) in ing) and cur:
                iks, ibest = ing.get((t - 2, v), ((), ()))
                keys = sorted(cur)
                for k0 in keys:
                    k = k0
                    while t < k < kcap:
                        if t == 3:
                            b, step = v, "add1"                               # the trivial CA(v; 1, k - 1, v)
                        else:
                            x = bisect.bisect_left(iks, k - 1)
                            if x >= len(iks):
                                break
                            b, (j, _) = ibest[x]
                            step = "add1/%d" % j
                        n, origins = cur[k]
                        m = n + v * (v - 1) * b
                        if (k + 1 in cur and m > cur[k + 1][0]) or not useful(t, v, k + 1, m):
                            break
                        offer(k + 1, m, [(i, w + (step,)) for i, w in origins])
                        k += 1
                        if k in keys:
                            break                                             # a point of its own, reached in order
            if cur:
                out[(t, v)] = {k: (n, sorted(set(o))) for k, (n, o) in cur.items()}
    return out


def step_name(s):
    """the step as written in a working: fuse, derive or add1"""
    return s.split("/")[0]


def working_rows(i, w):
    """the row indices a working rests on: its source row, then the ingredient row of each add1 step at t >= 4
    (an add1 step at t = 3 has the trivial ingredient, no row)"""
    return [i] + [int(s.split("/")[1]) for s in w if s.startswith("add1/")]


def stair_steps(values):
    """values {k: N} -> [(k, N)] steps, k increasing: N smallest at any k' >= k, k largest with it"""
    steps, m = [], INF
    for k in sorted(values, reverse=True):
        if values[k] < m:
            steps.append((k, values[k]))
            m = values[k]
    return steps[::-1]


def derived_floor(table_dir):
    """table/derived.csv (tools/derive_table.py) as {(t, v): (ks, suf)}: ks the widths of its lines, increasing,
    and suf[i] the smallest N of any line at a width k' >= ks[i], whatever its size rule. Empty when the file is
    not there (then nothing is withheld)."""
    pts = collections.defaultdict(dict)
    for d in read_csv(os.path.join(table_dir, "derived.csv")):
        tv, k, n = (int(d["t"]), int(d["v"])), int(d["k"]), int(d["N"])
        pts[tv][k] = min(n, pts[tv].get(k, INF))
    out = {}
    for tv, p in pts.items():
        ks = sorted(p)
        suf, m = [0] * len(ks), INF
        for i in range(len(ks) - 1, -1, -1):
            m = min(m, p[ks[i]])
            suf[i] = m
        out[tv] = (ks, suf)
    return out


def derived_witness(table_dir, t, v, k):
    """the line of table/derived.csv at (t, v) and a width k' >= k with the smallest N (the narrowest among equals),
    as (N, k', law), or None"""
    best = None
    for d in read_csv(os.path.join(table_dir, "derived.csv")):
        if (int(d["t"]), int(d["v"])) == (t, v) and int(d["k"]) >= k:
            x = (int(d["N"]), int(d["k"]), d["law"])
            if best is None or x < best:
                best = x
    return best


def floor_at(floor, tv, k):
    """the smallest N of derived.csv at (t, v) and any width k' >= k, or INF"""
    ks, suf = floor.get(tv, ((), ()))
    x = bisect.bisect_left(ks, k)
    return suf[x] if x < len(ks) else INF


def baseline_kmax(rows):
    """the baseline's column range: the largest k of Colbourn's rows (source S1) per (t, v), as in
    tools/derive_table.py"""
    out = collections.defaultdict(int)
    for r in rows:
        if r["source_id"] == "S1":
            tv = (int(r["t"]), int(r["v"]))
            out[tv] = max(out[tv], int(r["k"]))
    return out


def above_rule(floor, t, v, k, n):
    """the smallest N of derived.csv at (t, v) and a width k' >= k when it is below n (the row is above a published
    size rule at its own width), else None"""
    low = floor_at(floor, (t, v), k)
    return low if low < n else None


def counted_range(rows, cnt, floor):
    """{(t, v): the widest width of the counted range} and the counted rows left out of it (section 6, version 1.4):
    the range of (t, v) ends at its widest counted row, except that a row past the baseline's column range whose N is
    above a line of derived.csv at a width k' >= k does not widen it (the row itself still counts). cnt: the counted
    rows; floor: derived_floor()."""
    bk = baseline_kmax(rows)
    kmax, left_out = collections.defaultdict(int), []
    for r in cnt:
        t, v, k, n = int(r["t"]), int(r["v"]), int(r["k"]), int(r["N"])
        if k > bk[(t, v)] and above_rule(floor, t, v, k, n) is not None:
            left_out.append(r)
            continue
        kmax[(t, v)] = max(kmax[(t, v)], k)
    return kmax, left_out


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
    hk = {}
    stats = collections.Counter()

    def hkey(i):
        if i not in hk:
            hk[i] = ctx.headline_key(i)
        return hk[i]

    def okey(o):
        """derived workings: by their source row in headline order, then the shorter working"""
        return (hkey(o[0]), len(o[1]), o[1])
    clo_fd = closure(inputs)                                   # fuse and derive: the add1 ingredients
    veto = derived_floor(table_dir)
    # the counted range of each (t, v): a row past the baseline's column range that derived.csv beats at its own
    # width does not widen it, so the derived sizes it would let in stay under the comparison below (version 1.4)
    kmax_tv, left_out = counted_range(rows, [rows[i] for i in cnt], veto)
    stats["range_rows_left_out"] = len(left_out)
    def ikey(o):
        """add1 ingredients of equal size: a VERIFIED row first (so the step keeps the weakest tier as high as
        it can be), then headline order"""
        return (rows[o[0]]["tier"] != "VERIFIED", okey(o))
    clo = closure(inputs, ingredients=clo_fd, rank=ikey, kmax=kmax_tv)   # fuse, derive and add1
    clo_fuse = closure(inputs, derive=False)
    by_tv = collections.defaultdict(dict)       # (t, v) -> {k: row min N}
    rows_tv = collections.defaultdict(list)     # (t, v) -> counted row indices
    for (t, v, k), lst in rowpts.items():
        by_tv[(t, v)][k] = min(x[0] for x in lst)
        rows_tv[(t, v)].extend(i for _, i in lst)
    lines = []

    def best_row(cands):
        """the named row among (N, index) candidates: smallest N, then headline order"""
        return min(cands, key=lambda x: (x[0], hkey(x[1]))) if cands else None

    for tv in sorted(set(by_tv) | set(clo)):
        t, v = tv
        rmin = by_tv.get(tv, {})
        dmin = {}
        kmax = kmax_tv.get(tv, 0)
        # past the counted range of (t, v) (counted_range: every counted row, less a row past the baseline's range
        # that derived.csv beats at its own width) only fuse counts (CONVENTIONS.md section 6); derive there gives
        # sizes far above known values (t = 2, v = 2 at k = 99,999: 252 against the exact 21). The fuse-only
        # closure gives those, so no add1 step lands there either. A fused size there counts only if no line
        # of table/derived.csv at (t, v) and a width k' >= k, by any size rule counted or not, has a smaller N
        # (fusing a 4-symbol array down to 2 symbols gives 780 at t = 3 where PCT gives 77, issue #62). The
        # uncounted rules only withhold a size here, they never give one.
        pts = {k: x for k, x in clo.get(tv, {}).items() if k <= kmax}
        vetoed = set()
        for k, x in clo_fuse.get(tv, {}).items():
            if k > kmax and not (k in rmin and rmin[k] <= x[0]):     # a row is never withheld, only derived sizes
                if floor_at(veto, tv, k) < x[0]:
                    vetoed.add(k)
                else:
                    pts[k] = x
        if vetoed:
            # withheld steps: those that would have been stair steps without the comparison
            whole = dict(rmin)
            whole.update((k, n) for k, (n, _) in clo_fuse[tv].items() if k > kmax)
            stats["derived_vetoed"] += sum(1 for k, _ in stair_steps(whole) if k in vetoed)
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
                origins = sorted(dmin[k][1], key=okey)
                head = [rows[i] for i in working_rows(*origins[0])]
                tier = "CITED" if any(r["tier"] == "CITED" for r in head) else "VERIFIED"
                works = ["%s:%s" % (frame_label(rows[i], ctx.ids[i]), ":".join(step_name(s) for s in w))
                         for i, w in origins]
                prev = best_row([(int(rows[i]["N"]), i) for i in rtv if int(rows[i]["k"]) >= k])
                if prev is None:
                    stats["derived_no_counted"] += 1
                    if kmax and n < rmin[kmax]:
                        # past the counted range, yet below the counted value at the widest counted width (for
                        # example CA(13115; 3, 11288, 12) below 13,151 at k = 10,000): it improves on that row
                        prev = best_row([(int(rows[i]["N"]), i) for i in rtv if int(rows[i]["k"]) == kmax])
                if tier == "VERIFIED":
                    stats["derived_verified"] += 1
                if any(s.startswith("add1") for s in origins[0][1]):
                    stats["derived_add1"] += 1
                lines.append([str(t), str(v), str(k), str(n), "derived", tier, "", "", "", "none", "",
                              works[0], "", ALL_SEP.join(works),
                              ";".join("+".join(ctx.ids[j] for j in working_rows(i, w)) for i, w in origins),
                              ctx.ids[prev[1]] if prev else "", max(r.get("entered") or "" for r in head),
                              ctx.generated])
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
