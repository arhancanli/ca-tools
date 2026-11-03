#!/usr/bin/env python3
"""construction_cert - check a construction certificate and rebuild the array it proves.

A construction certificate records the recipe of a covering array instead of the array. Five
constructions are known (tools/CONSTRUCTION_CERT.md states each theorem, its hypotheses and the
proof the checker follows):

  powercz-1  Colbourn and Zhou 2012, Theorem 2.2 with Lemma 2.3 (below)
  powercz-2  powercz-1 for v = 2 with a column relabelling per block, and the constant tuples (weights
             0 and t) proved by exact enumeration instead of being declared by a block (e = 2); the
             heavy parts run in the C helper tools/cz2help.c, compiled at run time with cc
  fuse-1     Colbourn, Keri, Rivas Soriano and Schlage-Puchta 2010, Lemma 3.1: a CA(N; t, k, v+1)
             gives a CA(N-2; t, k, v), t >= 2, by the two-row fusing of tools/cphf/fuse2.c
  derive-1   the derived array: the rows of a CA(N; t+1, k+1, v) with symbol s in column c,
             column c deleted, form a CA(N_s; t, k, v)
  product-1  the direct product of a CA(N1; 2, k1, v) and a CA(N2; 2, k2, v): a CA(N1+N2-d; 2,
             k1 k2, v), d the rows of the second part that repeat a row of the first (constant rows)

An ingredient is given inline ("rows"), as a file beside the certificate ("file" and its "sha256"),
both checked exhaustively here, or by the array_sha256 of a counted VERIFIED row of the table
("table"; the array is read from table/arrays, its canonical hash checked, and its coverage
trusted as verified by the table). For "powercz-1" (Colbourn and Zhou 2012, Theorem 2.2 with
Lemma 2.3) the certificate is a hash family with M rows and k columns, one quilting array
(ingredient) per row, and the species classes each ingredient is claimed to cover. This program

  1. regenerates the hash family from its description (its own GF(q) arithmetic),
  2. checks every hypothesis the coverage proof uses, exactly and exhaustively:
       width       every row of the hash family has width w_i >= t
       ingredient  every ingredient file has the recorded sha256, is a rectangular array over
                   0..v-1 with exactly w_i columns for each row it is assigned to
       agreement   any two distinct columns of the hash family agree in at most e-1 rows
                   (checked as: every e-subset of rows maps the k columns injectively)
       quilting    every ingredient covers, on every t-set of its columns, every t-tuple whose
                   species (multiset of values) it is declared to cover
       species     every species S of size t over v symbols is declared in more than
                   (e-1) * tau(S) rows, tau(S) = number of pairs of unequal entries
  3. assembles the array (block i = ingredient i with its columns indexed by row i of the hash
     family), serializes it in the table's canonical text (tools/check_submission.py:
     canon_serialize) and hashes it as a stream,
  4. compares N, k and the sha256 with the certificate's expected values.

It exits 0 only if every check passes. The format and the proof are in
tools/CONSTRUCTION_CERT.md. Standard library only (powercz-2 also compiles tools/cz2help.c with cc
when it is available, and otherwise does its exact work in Python up to a limit, failing above it).

Usage:
  construction_cert.py CERT.json [--write ARRAY.txt] [--quiet] [--table-dir DIR]
--table-dir (default: the table/ of this repository) is where "table" ingredients are found.
Exit status: 0 certificate valid, 1 a check failed, 2 malformed certificate or usage error.
"""
import csv
import gzip
import hashlib
import itertools
import json
import os
import re
import sys
import time

FORMAT = "construction-cert-1"
CONSTRUCTIONS = ("powercz-1", "powercz-2", "fuse-1", "derive-1", "product-1")
ARRAY_KINDS = ("fuse-1", "derive-1", "product-1")
# the reference id (table/references.csv) of the theorem of each construction, for builds_on
# (derive-1 has none: deriving a strength t-1 array is folklore with no single source in
# references.csv, so the submitter's builds_on is kept as given and nothing is added)
REFERENCE = {"powercz-1": "power-cz2012", "powercz-2": "power-cz2012", "fuse-1": "fuse-ckrs2010",
             "derive-1": None, "product-1": "product-cmmssy2006"}
REPO_TABLE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "table")
# the exhaustive check of an inline or file ingredient here costs about C(k, t) * N entry reads in
# Python; above this an ingredient must be entered in the table first and named by its hash
INGREDIENT_WORK = 3 * 10 ** 8
# powercz-2: the C helper (compiled at run time; its source must have this sha256, so the tool hash
# of this file in a row's stamp also fixes the helper) and its work limit, in 64-bit word operations
HELPER_SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cz2help.c")
HELPER_SHA256 = "17a22a3d3e604e8d862860f8656877c21f53d73294cb9451647561dae6137b56"
HELPER_WORK = 10 ** 11
HELPER_LIST = 10 ** 7       # the most bad t-sets of one block the helper lists for the enumeration
MAX_FIELD = 4096            # largest q for which GF(q) tables are built
MAX_COLUMNS = 4000000       # largest q^e enumerated
HEX64 = re.compile(r"^[0-9a-f]{64}$")
NAME_RE = re.compile(r"^[A-Za-z0-9_.+-]{1,100}$")
INT_RE = re.compile(r"^[0-9]+$")


class CertError(Exception):
    """the certificate is malformed (exit 2)"""


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def is_int(x):
    return isinstance(x, int) and not isinstance(x, bool)


def need_int(obj, key, lo=None, hi=None, where=""):
    if key not in obj:
        raise CertError("%smissing key %r" % (where, key))
    x = obj[key]
    if not is_int(x):
        raise CertError("%s%r must be an integer, got %r" % (where, key, x))
    if lo is not None and x < lo:
        raise CertError("%s%r = %d is below %d" % (where, key, x, lo))
    if hi is not None and x > hi:
        raise CertError("%s%r = %d is above %d" % (where, key, x, hi))
    return x


def only_keys(obj, allowed, where):
    if not isinstance(obj, dict):
        raise CertError("%s must be a JSON object" % where)
    extra = sorted(set(obj) - set(allowed))
    if extra:
        raise CertError("%s: unknown key(s) %s" % (where, ", ".join(map(repr, extra))))


def is_prime(n):
    if n < 2:
        return False
    d = 2
    while d * d <= n:
        if n % d == 0:
            return False
        d += 1
    return True


def comb(n, r):
    if r < 0 or r > n:
        return 0
    out = 1
    for i in range(r):
        out = out * (n - i) // (i + 1)
    return out


def species_list(t, v):
    """all species of size t over v symbols, as count vectors (c_0, ..., c_{v-1}), sum t"""
    out = []

    def rec(prefix, left, slots):
        if slots == 1:
            out.append(tuple(prefix + [left]))
            return
        for c in range(left, -1, -1):
            rec(prefix + [c], left - c, slots - 1)
    rec([], t, v)
    return out


def tau(sp):
    t = sum(sp)
    return comb(t, 2) - sum(comb(c, 2) for c in sp)


def species_of(tup, v):
    c = [0] * v
    for x in tup:
        c[x] += 1
    return tuple(c)


def arrangements(sp, v):
    """every t-tuple over 0..v-1 whose species is sp"""
    t = sum(sp)
    return [tup for tup in itertools.product(range(v), repeat=t) if species_of(tup, v) == sp]


def fmt_species(sp, v):
    if v == 2:
        return "weight %d" % sp[1]
    return "{" + ",".join("%d^%d" % (s, c) for s, c in enumerate(sp) if c) + "}"


# ---------------------------------------------------------------------------
# GF(p^m): element i <-> polynomial sum_j d_j x^j with d_j the base-p digits of i
# (d_0 least significant), modulo the monic modulus a_0 + a_1 x + ... + a_m x^m.
# ---------------------------------------------------------------------------

class Field:
    def __init__(self, p, m, modulus):
        self.p, self.m, self.q = p, m, p ** m
        self.modulus = list(modulus)
        q = self.q
        digits = [self._digits(i) for i in range(q)]
        self.add = [[self._undigits([(a + b) % p for a, b in zip(digits[i], digits[j])])
                     for j in range(q)] for i in range(q)]
        self.mul = [[self._undigits(self._polymulmod(digits[i], digits[j]))
                     for j in range(q)] for i in range(q)]

    def _digits(self, i):
        d = []
        for _ in range(self.m):
            d.append(i % self.p)
            i //= self.p
        return d

    def _undigits(self, d):
        x = 0
        for c in reversed(d):
            x = x * self.p + c
        return x

    def _polymulmod(self, a, b):
        p, m = self.p, self.m
        prod = [0] * (2 * m - 1)
        for i, x in enumerate(a):
            if x:
                for j, y in enumerate(b):
                    prod[i + j] = (prod[i + j] + x * y) % p
        # reduce: x^m = -(a_0 + ... + a_{m-1} x^{m-1})  (modulus is monic)
        for deg in range(2 * m - 2, m - 1, -1):
            c = prod[deg]
            if c:
                prod[deg] = 0
                for j in range(m):
                    prod[deg - m + j] = (prod[deg - m + j] - c * self.modulus[j]) % p
        return prod[:m]


def parse_field(obj):
    only_keys(obj, ("q", "p", "m", "modulus"), "field")
    q = need_int(obj, "q", 2, MAX_FIELD, "field: ")
    p = need_int(obj, "p", 2, None, "field: ")
    m = need_int(obj, "m", 1, None, "field: ")
    if p ** m != q:
        raise CertError("field: q = %d is not p^m = %d^%d" % (q, p, m))
    if m == 1:
        if "modulus" in obj and obj["modulus"] not in (None, [0, 1]):
            raise CertError("field: a prime field takes no modulus (or [0, 1])")
        modulus = [0, 1]
    else:
        modulus = obj.get("modulus")
        if not isinstance(modulus, list) or len(modulus) != m + 1 or \
                not all(is_int(c) and 0 <= c < p for c in modulus):
            raise CertError("field: modulus must be a list of m+1 = %d coefficients in 0..%d, "
                            "constant term first" % (m + 1, p - 1))
        if modulus[m] != 1:
            raise CertError("field: modulus must be monic (last coefficient 1)")
    return p, m, q, modulus


# ---------------------------------------------------------------------------
# certificate parsing
# ---------------------------------------------------------------------------

def parse_covers(obj, t, v, where):
    only_keys(obj, ("weights", "species", "all"), where)
    if len(obj) != 1:
        raise CertError("%s: give exactly one of 'weights', 'species', 'all'" % where)
    allsp = species_list(t, v)
    if "all" in obj:
        if obj["all"] is not True:
            raise CertError("%s: 'all' must be true" % where)
        return set(allsp)
    if "weights" in obj:
        if v != 2:
            raise CertError("%s: 'weights' is only for v = 2; use 'species'" % where)
        w = obj["weights"]
        if not (isinstance(w, list) and len(w) == 2 and all(is_int(x) for x in w)
                and 0 <= w[0] <= w[1] <= t):
            raise CertError("%s: 'weights' must be [a, b] with 0 <= a <= b <= t" % where)
        return {(t - wt, wt) for wt in range(w[0], w[1] + 1)}
    sps = obj["species"]
    if not isinstance(sps, list):
        raise CertError("%s: 'species' must be a list of count vectors (it may be empty: an "
                        "ingredient that counts for no species)" % where)
    out = set()
    for sp in sps:
        if not (isinstance(sp, list) and len(sp) == v and all(is_int(c) and c >= 0 for c in sp)
                and sum(sp) == t):
            raise CertError("%s: species %r is not a list of %d counts summing to t = %d"
                            % (where, sp, v, t))
        if tuple(sp) in out:
            raise CertError("%s: species %r listed twice" % (where, sp))
        out.add(tuple(sp))
    return out


def parse_matrix_text(text, where):
    rows = []
    for lineno, line in enumerate(text.splitlines(), 1):
        toks = line.split()
        if not toks:
            continue
        row = []
        for tok in toks:
            if not INT_RE.match(tok):
                raise CertError("%s line %d: entry %r is not a nonnegative integer"
                                % (where, lineno, tok[:20]))
            row.append(int(tok))
        rows.append(row)
    return rows


def load_certificate(path, table_dir=None):
    def no_duplicates(pairs):
        d = {}
        for key, val in pairs:
            if key in d:
                raise CertError("duplicate key %r in the certificate" % key)
            d[key] = val
        return d
    try:
        with open(path, "rb") as f:
            raw = f.read()
        cert = json.loads(raw.decode("utf-8"), object_pairs_hook=no_duplicates)
    except (OSError, ValueError) as e:
        raise CertError("cannot read certificate %s: %s" % (path, e))
    if isinstance(cert, dict) and cert.get("construction") in ARRAY_KINDS:
        return load_array_kind(cert, raw, path, table_dir)
    cz2 = isinstance(cert, dict) and cert.get("construction") == "powercz-2"
    only_keys(cert, ("format", "construction", "t", "v", "e", "field", "family", "ingredients",
                     "expected", "notes") + (("enumerate_weights",) if cz2 else ()), "certificate")
    if cert.get("format") != FORMAT:
        raise CertError("format must be %r" % FORMAT)
    if cert.get("construction") not in CONSTRUCTIONS:
        raise CertError("construction must be one of %s" % ", ".join(CONSTRUCTIONS))
    if "notes" in cert and not (isinstance(cert["notes"], str) or
                                (isinstance(cert["notes"], list) and
                                 all(isinstance(s, str) for s in cert["notes"]))):
        raise CertError("notes must be a string or a list of strings")
    t = need_int(cert, "t", 2, 32)
    v = need_int(cert, "v", 2, 64)
    e = need_int(cert, "e", 1, 64)
    c = {"t": t, "v": v, "e": e, "dir": os.path.dirname(os.path.abspath(path)),
         "cert_sha256": hashlib.sha256(raw).hexdigest(), "kind": cert["construction"]}
    if cz2:
        parse_powercz2(cert, c)

    # expected values
    exp = cert.get("expected")
    only_keys(exp, ("N", "k", "array_sha256"), "expected")
    c["exp_N"] = need_int(exp, "N", 1, None, "expected: ")
    c["exp_k"] = need_int(exp, "k", 1, None, "expected: ")
    sha = exp.get("array_sha256")
    if not isinstance(sha, str) or not HEX64.match(sha):
        raise CertError("expected: array_sha256 must be 64 lowercase hex digits")
    c["exp_sha"] = sha

    # ingredients
    ings = cert.get("ingredients")
    if not isinstance(ings, dict) or not ings:
        raise CertError("ingredients must be a nonempty object name -> ingredient")
    c["ingredients"] = {}
    for name, ing in ings.items():
        where = "ingredient %r" % name
        if not NAME_RE.match(name):
            raise CertError("%s: bad name" % where)
        only_keys(ing, ("file", "sha256", "rows", "covers", "table"), where)
        d = {"name": name, "covers": parse_covers(ing.get("covers"), t, v, where + " covers")}
        if "table" in ing:
            if "file" in ing or "rows" in ing or "sha256" in ing:
                raise CertError("%s: give 'table' alone (no 'file', 'rows' or 'sha256')" % where)
            d.update(resolve_table(ing["table"], table_dir, where))
            d["need_t"], d["need_v"] = t, v
        elif "file" in ing:
            if "rows" in ing:
                raise CertError("%s: give 'file' or 'rows', not both" % where)
            fn = ing["file"]
            if not isinstance(fn, str) or not NAME_RE.match(fn) or fn.startswith("."):
                raise CertError("%s: file must be a plain file name beside the certificate"
                                % where)
            h = ing.get("sha256")
            if not isinstance(h, str) or not HEX64.match(h):
                raise CertError("%s: a file ingredient needs sha256 (64 lowercase hex)" % where)
            fp = os.path.join(c["dir"], fn)
            try:
                with open(fp, "rb") as f:
                    raw = f.read()
            except OSError as ex:
                raise CertError("%s: cannot read %s: %s" % (where, fp, ex))
            d["file"], d["sha_expected"] = fn, h
            d["sha_actual"] = hashlib.sha256(raw).hexdigest()
            try:
                text = raw.decode("ascii")
            except UnicodeDecodeError:
                raise CertError("%s: file is not ASCII text" % where)
            d["rows"] = parse_matrix_text(text, "%s (%s)" % (where, fn))
        elif "rows" in ing:
            if "sha256" in ing:
                raise CertError("%s: an inline ingredient takes no sha256" % where)
            rows = ing["rows"]
            if not isinstance(rows, list) or not all(isinstance(r, list) and
                                                     all(is_int(x) and x >= 0 for x in r)
                                                     for r in rows):
                raise CertError("%s: rows must be a list of lists of nonnegative integers"
                                % where)
            d["rows"] = [list(r) for r in rows]
        else:
            raise CertError("%s: give 'file' (with 'sha256') or 'rows'" % where)
        c["ingredients"][name] = d

    # hash family
    fam = cert.get("family")
    if not isinstance(fam, dict):
        raise CertError("family must be an object")
    ftype = fam.get("type")
    if ftype == "reed-solomon":
        only_keys(fam, ("type", "rows", "column_limit"), "family")
        if "field" not in cert:
            raise CertError("a reed-solomon family needs 'field'")
        c["field"] = parse_field(cert["field"])
        q = c["field"][2]
        if q ** e > MAX_COLUMNS:
            raise CertError("q^e = %d columns is above the limit %d" % (q ** e, MAX_COLUMNS))
        rows = fam.get("rows")
        if not isinstance(rows, list) or not rows:
            raise CertError("family: rows must be a nonempty list")
        frows = []
        for i, r in enumerate(rows):
            where = "family row %d" % i
            only_keys(r, ("point", "forbidden", "ingredient") + (("relabel",) if cz2 else ()), where)
            pt = r.get("point")
            if pt == "inf":
                pt = q
            elif not (is_int(pt) and 0 <= pt < q):
                raise CertError("%s: point must be a field element 0..%d or \"inf\"" % (where, q - 1))
            fb = r.get("forbidden", [])
            if not (isinstance(fb, list) and all(is_int(x) and 0 <= x < q for x in fb)):
                raise CertError("%s: forbidden must be a list of field elements" % where)
            if len(set(fb)) != len(fb):
                raise CertError("%s: forbidden lists a value twice" % where)
            if len(fb) >= q:
                raise CertError("%s: every value is forbidden" % where)
            frows.append({"point": pt, "forbidden": sorted(fb), "ingredient": r.get("ingredient")})
            if cz2:
                frows[-1]["relabel"] = parse_relabel(r, where)
        c["family"] = {"type": ftype, "rows": frows}
        if "column_limit" in fam:
            c["family"]["column_limit"] = need_int(fam, "column_limit", 1, None, "family: ")
    elif ftype == "explicit":
        only_keys(fam, ("type", "rows"), "family")
        if "field" in cert:
            raise CertError("an explicit family takes no 'field'")
        rows = fam.get("rows")
        if not isinstance(rows, list) or not rows:
            raise CertError("family: rows must be a nonempty list")
        frows = []
        k = None
        for i, r in enumerate(rows):
            where = "family row %d" % i
            only_keys(r, ("width", "values", "ingredient") + (("relabel",) if cz2 else ()), where)
            w = need_int(r, "width", 1, None, where + ": ")
            vals = r.get("values")
            if not (isinstance(vals, list) and all(is_int(x) and 0 <= x < w for x in vals)):
                raise CertError("%s: values must be a list of symbols 0..width-1" % where)
            if k is None:
                k = len(vals)
            elif len(vals) != k:
                raise CertError("%s: %d values where row 0 has %d" % (where, len(vals), k))
            frows.append({"width": w, "values": list(vals), "ingredient": r.get("ingredient")})
            if cz2:
                frows[-1]["relabel"] = parse_relabel(r, where)
        c["family"] = {"type": ftype, "rows": frows}
    else:
        raise CertError("family type must be 'reed-solomon' or 'explicit'")
    for i, r in enumerate(c["family"]["rows"]):
        if r["ingredient"] not in c["ingredients"]:
            raise CertError("family row %d: ingredient %r is not defined" % (i, r["ingredient"]))
    unused = set(c["ingredients"]) - {r["ingredient"] for r in c["family"]["rows"]}
    if unused:
        raise CertError("ingredient(s) defined but not assigned to any row: %s"
                        % ", ".join(sorted(unused)))
    return c


# ---------------------------------------------------------------------------
# hash family generation
# ---------------------------------------------------------------------------

def build_family(c):
    """sets c['H'] (M lists of k symbols, row i over 0..w_i-1) and c['widths']"""
    fam = c["family"]
    if fam["type"] == "explicit":
        c["H"] = [r["values"] for r in fam["rows"]]
        c["widths"] = [r["width"] for r in fam["rows"]]
        return
    p, m, q, modulus = c["field"]
    F = Field(p, m, modulus)
    c["F"] = F
    e = c["e"]
    add, mul = F.add, F.mul
    # columns: coefficient tuples (c_0, ..., c_{e-1}) of the polynomial c_0 + c_1 x + ... in
    # lexicographic order (c_0 most significant), as itertools.product(range(q), repeat=e)
    raw = []
    for r in fam["rows"]:
        x = r["point"]
        vals = []
        for coeffs in itertools.product(range(q), repeat=e):
            if x == q:                      # the point at infinity: the coefficient of x^(e-1)
                vals.append(coeffs[e - 1])
                continue
            acc = 0
            for cj in reversed(coeffs):     # Horner
                acc = add[mul[acc][x]][cj]
            vals.append(acc)
        raw.append(vals)
    ncols = q ** e
    keep = [j for j in range(ncols)
            if all(raw[i][j] not in fam["rows"][i]["forbidden"] for i in range(len(raw)))]
    lim = fam.get("column_limit")
    if lim is not None:
        if lim > len(keep):         # reported by check_shape
            c["column_limit_short"] = (lim, len(keep))
        keep = keep[:lim]
    H, widths = [], []
    for i, r in enumerate(fam["rows"]):
        allowed = [s for s in range(q) if s not in r["forbidden"]]
        relabel = {s: n for n, s in enumerate(allowed)}
        H.append([relabel[raw[i][j]] for j in keep])
        widths.append(len(allowed))
    c["H"], c["widths"] = H, widths


# ---------------------------------------------------------------------------
# the checks: each takes the context and returns a list of failure messages
# ---------------------------------------------------------------------------

def check_field(c):
    """sanity of the field description (soundness does not depend on it: the agreement check
    below tests the generated family itself); p prime, no zero divisors, ring axioms"""
    if "F" not in c:
        return []
    F = c["F"]
    p, q = F.p, F.q
    out = []
    if not is_prime(p):
        return ["p = %d is not prime" % p]
    for a in range(1, q):
        row = F.mul[a]
        if 0 in row[1:] or len(set(row)) != q:
            return ["GF(%d) with modulus %r is not a field: %d has no inverse (the modulus is "
                    "reducible)" % (q, F.modulus, a)]
    add, mul = F.add, F.mul
    if q <= 64:
        for a in range(q):
            for b in range(q):
                if add[a][b] != add[b][a] or mul[a][b] != mul[b][a]:
                    return ["GF(%d): commutativity fails at %d, %d" % (q, a, b)]
                for d in range(q):
                    if mul[a][add[b][d]] != add[mul[a][b]][mul[a][d]]:
                        return ["GF(%d): distributivity fails at %d, %d, %d" % (q, a, b, d)]
                    if mul[mul[a][b]][d] != mul[a][mul[b][d]]:
                        return ["GF(%d): associativity fails at %d, %d, %d" % (q, a, b, d)]
    return out


def check_shape(c):
    """k >= t; every ingredient a nonempty rectangular array over 0..v-1 whose number of
    columns equals the width of every row it is assigned to"""
    out = []
    k = len(c["H"][0])
    if "column_limit_short" in c:
        out.append("family: column_limit %d exceeds the %d columns kept"
                   % c["column_limit_short"])
    if k < c["t"]:
        out.append("the hash family has k = %d columns, fewer than t = %d" % (k, c["t"]))
    for name, ing in c["ingredients"].items():
        rows = ing["rows"]
        if not rows:
            out.append("ingredient %s has no rows" % name)
            continue
        w = len(rows[0])
        bad = [i for i, r in enumerate(rows) if len(r) != w]
        if bad:
            out.append("ingredient %s is ragged (row %d has %d entries, row 0 has %d)"
                       % (name, bad[0], len(rows[bad[0]]), w))
            continue
        big = [(i, j) for i, r in enumerate(rows) for j, x in enumerate(r) if x >= c["v"]]
        if big:
            i, j = big[0]
            out.append("ingredient %s: entry %d at row %d column %d is not a symbol 0..%d"
                       % (name, rows[i][j], i, j, c["v"] - 1))
        for i, r in enumerate(c["family"]["rows"]):
            if r["ingredient"] == name and c["widths"][i] != w:
                out.append("ingredient %s has %d columns but family row %d has width %d"
                           % (name, w, i, c["widths"][i]))
    return out


def check_width(c):
    """every row of the hash family has width >= t (a quilting array on fewer than t columns
    covers nothing and its declared species would count vacuously)"""
    return ["family row %d has width %d < t = %d" % (i, w, c["t"])
            for i, w in enumerate(c["widths"]) if w < c["t"]]


def check_ingredient_hash(c):
    out = []
    for name, ing in c["ingredients"].items():
        if "file" in ing and ing["sha_actual"] != ing["sha_expected"]:
            out.append("ingredient %s: file %s has sha256 %s, the certificate records %s"
                       % (name, ing["file"], ing["sha_actual"], ing["sha_expected"]))
    return out


def agreement_by_subsets(H, e):
    """two distinct columns agree in >= e rows iff they agree on some e-subset of rows, iff
    that subset maps them to the same tuple; returns (column, column, rows) or None"""
    M, k = len(H), len(H[0])
    for sub in itertools.combinations(range(M), e):
        seen = {}
        rows = [H[i] for i in sub]
        for j in range(k):
            key = tuple(r[j] for r in rows)
            if key in seen:
                return seen[key], j, list(sub)
            seen[key] = j
    return None


def agreement_by_pairs(H, e):
    """direct count over all pairs of columns; returns (column, column, rows) or None"""
    M, k = len(H), len(H[0])
    cols = [tuple(H[i][j] for i in range(M)) for j in range(k)]
    for a in range(k):
        ca = cols[a]
        for b in range(a + 1, k):
            cb = cols[b]
            n = 0
            for i in range(M):
                if ca[i] == cb[i]:
                    n += 1
            if n >= e:
                return a, b, [i for i in range(M) if ca[i] == cb[i]]
    return None


def check_agreement(c):
    """any two distinct columns agree in at most e-1 rows (exact; the cheaper of two exact
    methods is used)"""
    H, e = c["H"], c["e"]
    M, k = len(H), len(H[0])
    if comb(M, e) * k * e <= k * k * M // 2:
        bad = agreement_by_subsets(H, e)
    else:
        bad = agreement_by_pairs(H, e)
    if bad:
        a, b, rows = bad
        return ["columns %d and %d agree in rows %s, at least e = %d rows; the bound is "
                "e-1 = %d" % (a, b, rows, e, e - 1)]
    return []


def check_quilting(c):
    """each ingredient covers every tuple of every declared species on every t-set of columns"""
    t, v = c["t"], c["v"]
    out = []
    arr_cache = {}
    for name, ing in c["ingredients"].items():
        if "table" in ing:
            continue        # a covering array of strength >= t of the table covers every species
        rows = ing["rows"]
        if not rows:
            out.append("ingredient %s has no rows" % name)
            continue
        w = len(rows[0])
        if any(len(r) != w for r in rows):
            out.append("ingredient %s is ragged; its quilting property cannot hold" % name)
            continue
        need = []
        for sp in sorted(ing["covers"]):
            if sp not in arr_cache:
                arr_cache[sp] = arrangements(sp, v)
            need.append((sp, arr_cache[sp]))
        missing = 0
        first = None
        for cols in itertools.combinations(range(w), t):
            present = set(tuple(r[j] for j in cols) for r in rows)
            for sp, arrs in need:
                for tup in arrs:
                    if tup not in present:
                        missing += 1
                        if first is None:
                            first = (cols, tup, sp)
        if missing:
            cols, tup, sp = first
            out.append("ingredient %s does not cover its declared species: %d (t-set, tuple) "
                       "pairs missing, first columns %s tuple %s (%s)"
                       % (name, missing, list(cols), list(tup), fmt_species(sp, v)))
    return out


def check_species(c):
    """every species S is declared in more than (e-1) * tau(S) rows"""
    t, v, e = c["t"], c["v"], c["e"]
    out = []
    table = []
    decl = [c["ingredients"][r["ingredient"]]["covers"] for r in c["family"]["rows"]]
    for sp in species_list(t, v):
        n = sum(1 for d in decl if sp in d)
        need = (e - 1) * tau(sp) + 1
        table.append((sp, tau(sp), need, n))
        if n < need:
            out.append("%s (tau = %d) is declared in %d rows; Lemma 2.3 needs more than "
                       "(e-1)*tau = %d, i.e. at least %d" % (fmt_species(sp, v), tau(sp), n,
                                                             (e - 1) * tau(sp), need))
    c["species_table"] = table
    return out


# ---------------------------------------------------------------------------
# powercz-2: relabelled blocks and constant tuples by enumeration (tools/CONSTRUCTION_CERT.md,
# "Power CZ with relabelled blocks (powercz-2)")
# ---------------------------------------------------------------------------

def parse_powercz2(cert, c):
    """the keys of powercz-2 beyond those of powercz-1: v = 2, t <= 7, enumerate_weights"""
    t, v, e = c["t"], c["v"], c["e"]
    if v != 2:
        raise CertError("powercz-2 is for v = 2 (v = %d)" % v)
    if t > 7:
        raise CertError("powercz-2 is for t <= 7 (t = %d)" % t)
    ew = cert.get("enumerate_weights", [])
    if not (isinstance(ew, list) and all(is_int(x) for x in ew)):
        raise CertError("enumerate_weights must be a list of weights")
    if len(set(ew)) != len(ew):
        raise CertError("enumerate_weights lists a weight twice")
    if any(x not in (0, t) for x in ew):
        raise CertError("enumerate_weights may list only the weights 0 and t = %d (the species with tau = 0, "
                        "the constant tuples), not %s" % (t, [x for x in ew if x not in (0, t)]))
    if ew and e != 2:
        raise CertError("the enumeration of enumerate_weights is implemented for e = 2 only (two blocks "
                        "determine a column only when two columns agree in at most one row); e = %d" % e)
    c["enumerate_weights"] = sorted(ew)


def parse_relabel(r, where):
    """a family row's relabel: a list of ingredient columns (a permutation, checked by 'relabel'), or None"""
    if "relabel" not in r:
        return None
    pi = r["relabel"]
    if not (isinstance(pi, list) and all(is_int(x) for x in pi)):
        raise CertError("%s: relabel must be a list of integers (ingredient columns)" % where)
    return list(pi)


def apply_relabel(c):
    """H[i][col] := pi_i[H[i][col]]: the value of row i (0..w_i-1) selects ingredient column pi_i of that
    value. A relabel that is not a permutation of 0..w_i-1 is reported by check_relabel and not applied."""
    c["relabel_failures"] = []
    c["relabelled_rows"] = 0
    for i, r in enumerate(c["family"]["rows"]):
        pi = r.get("relabel")
        if pi is None:
            continue
        w = c["widths"][i]
        if sorted(pi) != list(range(w)):
            dup = sorted({x for x in pi if pi.count(x) > 1})[:3] if len(pi) <= 4096 else []
            out = [x for x in pi if not 0 <= x < w][:3]
            c["relabel_failures"].append(
                "family row %d: relabel is not a permutation of the %d ingredient columns 0..%d (%d entries%s%s)"
                % (i, w, w - 1, len(pi), ", repeated %s" % dup if dup else "",
                   ", outside the range %s" % out if out else ""))
            continue
        c["H"][i] = [pi[x] for x in c["H"][i]]
        c["relabelled_rows"] += 1


def check_relabel(c):
    """powercz-2: every relabel is a permutation of the columns of the row's ingredient (0..w_i-1)"""
    return list(c["relabel_failures"])


class Helper:
    """tools/cz2help.c, compiled once per process into a temporary folder with cc; None (with the
    reason) when there is no compiler, the build fails, or the source is not the recorded one"""
    path = None
    why = None
    tried = False
    disabled = bool(os.environ.get("CONSTRUCTION_CERT_NO_HELPER"))

    @classmethod
    def get(cls):
        if cls.disabled:
            cls.why = "the C helper is disabled"
            return None
        if cls.tried:
            return cls.path
        cls.tried = True
        import atexit
        import shutil
        import subprocess
        import tempfile
        try:
            with open(HELPER_SRC, "rb") as f:
                src = f.read()
        except OSError as ex:
            cls.why = "cannot read %s: %s" % (HELPER_SRC, ex)
            return None
        h = hashlib.sha256(src).hexdigest()
        if h != HELPER_SHA256:
            cls.why = "tools/cz2help.c has sha256 %s, construction_cert.py records %s" % (h, HELPER_SHA256)
            return None
        cc_exe = shutil.which("cc") or shutil.which("gcc")
        if not cc_exe:
            cls.why = "no C compiler (cc)"
            return None
        d = tempfile.mkdtemp(prefix="cz2help-")
        atexit.register(shutil.rmtree, d, True)
        exe = os.path.join(d, "cz2help")
        try:
            p = subprocess.run([cc_exe, "-O3", "-o", exe, HELPER_SRC], stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, universal_newlines=True)
        except OSError as ex:
            cls.why = "cc failed: %s" % ex
            return None
        if p.returncode != 0 or not os.access(exe, os.X_OK):
            cls.why = "cc could not build tools/cz2help.c: %s" % p.stderr[:300]
            return None
        cls.path = exe
        return exe

    @classmethod
    def run(cls, args):
        import subprocess
        p = subprocess.run([cls.path] + [str(a) for a in args], stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, universal_newlines=True)
        if p.returncode != 0:
            raise RuntimeError("cz2help %s failed (exit %d): %s" % (args[0], p.returncode, p.stderr.strip()[:300]))
        return p.stdout


def cz2_tmpdir(c):
    """a temporary folder for the helper's input files, removed at the end of run()"""
    if "cz2_tmp" not in c:
        import tempfile
        c["cz2_tmp"] = tempfile.mkdtemp(prefix="cz2-")
    return c["cz2_tmp"]


def cz2_file(c, name):
    """the ingredient as a text file for the helper, written from the rows read (0/1, single spaces)"""
    files = c.setdefault("cz2_files", {})
    if name not in files:
        p = os.path.join(cz2_tmpdir(c), "ing%d.txt" % len(files))
        with open(p, "w", encoding="ascii", newline="\n") as f:
            for r in c["ingredients"][name]["rows"]:
                f.write(" ".join(map(str, r)) + "\n")
        files[name] = p
    return files[name]


def words(n):
    return (n + 63) // 64


def py_quilt_missing(rows, t, weights):
    """pure Python, exact: the number of (t-set, tuple) pairs with the tuple's weight in `weights` that no
    row shows, and the first such t-set with the first such weight (tuples in itertools.product order,
    as the helper)"""
    w = len(rows[0])
    tuples = [tp for tp in itertools.product((0, 1), repeat=t) if sum(tp) in weights]
    cols = [tuple(r[j] for r in rows) for j in range(w)]
    missing, first = 0, None
    for cs in itertools.combinations(range(w), t):
        present = set(zip(*[cols[j] for j in cs]))
        for tp in tuples:
            if tp not in present:
                missing += 1
                if first is None:
                    first = (list(cs), sum(tp))
    return missing, first


def zmasks(rows, z):
    """column j -> the rows equal to z, as a Python int bit set"""
    w = len(rows[0])
    out = [0] * w
    for i, r in enumerate(rows):
        b = 1 << i
        for j in range(w):
            if r[j] == z:
                out[j] |= b
    return out


def py_bad(rows, t, z, listing=False):
    """pure Python, exact: {s: number of s-sets of columns with no row constant z} for s = 1..t, stopping
    after the first s < t with a positive count; with listing, also the bad t-sets (lexicographic)"""
    zm = zmasks(rows, z)
    w = len(rows[0])
    counts, lst = {}, []
    for s in range(1, t + 1):
        n = 0
        for cs in itertools.combinations(range(w), s):
            x = -1
            for j in cs:
                x &= zm[j]
            if not x:
                n += 1
                if listing and s == t:
                    lst.append(cs)
        counts[s] = n
        if s < t and n:
            break
    return counts, lst


def py_enumerate(c, z, a, b, bad_a, bad_b):
    """pure Python, exact (e = 2): (candidates, survivors, first survivors), as the helper's enum"""
    t, H = c["t"], c["H"]
    M, k = len(H), len(H[0])
    pair = {}
    for col in range(k):
        key = (H[a][col], H[b][col])
        if key in pair:
            raise RuntimeError("columns %d and %d agree in rows %d and %d" % (pair[key], col, a, b))
        pair[key] = col
    others = [r for r in range(M) if r not in (a, b)]
    zm = {}
    for r in others:
        name = c["family"]["rows"][r]["ingredient"]
        if name not in zm:
            zm[name] = zmasks(c["ingredients"][name]["rows"], z)
    test = [(H[r], zm[c["family"]["rows"][r]["ingredient"]]) for r in others]
    perms = list(itertools.permutations(range(t)))
    cand, surv, shown = 0, 0, []
    for Xa in bad_a:
        for Xb in bad_b:
            for pm in perms:
                cols = []
                for j in range(t):
                    col = pair.get((Xa[j], Xb[pm[j]]))
                    if col is None:
                        break
                    cols.append(col)
                else:
                    cand += 1
                    alive = True
                    for Hr, zr in test:
                        x = -1
                        for col in cols:
                            x &= zr[Hr[col]]
                        if x:
                            alive = False
                            break
                    if alive:
                        surv += 1
                        if len(shown) < 5:
                            shown.append(sorted(cols))
    return cand, surv, shown


def cz2_note(c):
    return " (%s)" % Helper.why if Helper.get() is None and Helper.why else ""


def check_quilting2(c):
    """powercz-2: as check_quilting (every tuple of every declared weight on every t-set of columns of
    every ingredient), exact, by the C helper or, up to INGREDIENT_WORK, in Python"""
    t = c["t"]
    out = []
    for name, ing in c["ingredients"].items():
        if "table" in ing:
            continue        # a covering array of strength >= t of the table covers every species
        rows = ing["rows"]
        if not rows or not rows[0]:
            out.append("ingredient %s has no rows" % name)
            continue
        w = len(rows[0])
        if any(len(r) != w for r in rows) or any(x not in (0, 1) for r in rows for x in r):
            out.append("ingredient %s is ragged or not binary; its quilting property cannot hold" % name)
            continue
        wts = sorted(sp[1] for sp in ing["covers"])
        if not wts or w < t:
            continue        # nothing declared (or no t-set: the width check reports it)
        exe = Helper.get()
        if exe and comb(w, t) * (2 ** t) * words(len(rows)) <= HELPER_WORK:
            res = Helper.run(["quilt", cz2_file(c, name), t, sum(1 << x for x in wts)]).split()
            miss = int(res[2])
            first = (list(map(int, res[4:4 + t])), int(res[5 + t])) if miss else None
        elif comb(w, t) * len(rows) * t <= INGREDIENT_WORK:
            miss, first = py_quilt_missing(rows, t, set(wts))
        else:
            out.append("ingredient %s: the quilting check (C(%d, %d) column sets of %d rows) is above the limit of "
                       "this checker%s" % (name, w, t, len(rows), cz2_note(c)))
            continue
        if miss:
            out.append("ingredient %s does not cover its declared weights %s: %d (t-set, tuple) pairs missing, "
                       "first columns %s (weight %d)" % (name, wts, miss, first[0], first[1]))
    return out


def check_species2(c):
    """powercz-2: every species (weight) is declared in more than (e-1) tau rows (Lemma 2.3), or is a
    constant tuple listed in enumerate_weights (proved by check_enumeration)"""
    t, v, e = c["t"], c["v"], c["e"]
    out, table = [], []
    decl = [c["ingredients"][r["ingredient"]]["covers"] for r in c["family"]["rows"]]
    for sp in species_list(t, v):
        n = sum(1 for d in decl if sp in d)
        need = (e - 1) * tau(sp) + 1
        table.append((sp, tau(sp), need, n))
        if sp[1] in c["enumerate_weights"]:
            continue
        if n < need:
            out.append("%s (tau = %d) is declared in %d rows; Lemma 2.3 needs more than (e-1)*tau = %d, i.e. at "
                       "least %d%s" % (fmt_species(sp, v), tau(sp), n, (e - 1) * tau(sp), need,
                                       " (or list it in enumerate_weights)" if tau(sp) == 0 else ""))
    c["species_table"] = table
    return out


def check_enumeration(c):
    """powercz-2: every weight of enumerate_weights (the tuple z^t, z = 0 for weight 0 and 1 for weight
    t) is shown on every t-set of array columns, by exact enumeration (tools/CONSTRUCTION_CERT.md):
      1. no ingredient has an s-set of columns, s < t, with no row constant z ("bad"), so a t-set of
         array columns whose image in some block has fewer than t columns is covered there;
      2. the bad t-sets of two blocks a and b, every bijection between them, the array columns found
         by their pair of values in rows a and b (unique, e = 2), and the other blocks tested directly;
         a t-set left over (a survivor) misses z^t, and there must be none."""
    out = []
    c["enumeration"] = {}
    ew = c["enumerate_weights"]
    if not ew:
        return out
    t, H = c["t"], c["H"]
    M = len(H)
    rows_of = [r["ingredient"] for r in c["family"]["rows"]]
    if M < 2:
        return ["the enumeration needs at least two rows in the hash family"]
    for name in set(rows_of):
        rws = c["ingredients"][name]["rows"]
        if not rws or not rws[0] or any(len(r) != len(rws[0]) for r in rws) or \
                any(x not in (0, 1) for r in rws for x in r):
            return ["ingredient %s is ragged or not binary; nothing can be enumerated" % name]
    for wt in ew:
        z = 0 if wt == 0 else 1
        rep = c["enumeration"].setdefault(wt, {"z": z})
        # 1. bad sets of every ingredient
        counts, too_big = {}, False
        for name in sorted(set(rows_of)):
            rws = c["ingredients"][name]["rows"]
            w = len(rws[0])
            exe = Helper.get()
            if exe and comb(w, t) * words(len(rws)) * t <= HELPER_WORK:
                cn = {}
                for line in Helper.run(["bad", cz2_file(c, name), t, z]).splitlines():
                    f = line.split()
                    cn[int(f[1])] = int(f[2])
            elif comb(w, t) * len(rws) * t <= INGREDIENT_WORK:
                cn = py_bad(rws, t, z)[0]
            else:
                out.append("weight %d: listing the bad %d-sets of ingredient %s (C(%d, %d) sets) is above the limit "
                           "of this checker%s" % (wt, t, name, w, t, cz2_note(c)))
                too_big = True
                continue
            counts[name] = cn
            small = [s for s in range(1, t) if cn.get(s, 0) > 0]
            if small:
                out.append("weight %d: ingredient %s has %d %d-sets of columns with no row constant %d, so a t-set of "
                           "array columns whose image there has %d columns can miss the tuple; the enumeration needs "
                           "none below t" % (wt, name, cn[small[0]], small[0], z, small[0]))
        rep["bad"] = {name: [cn.get(s) for s in range(1, t + 1)] for name, cn in counts.items()}
        if too_big or len(counts) < len(set(rows_of)) or any(cn.get(s, 0) for cn in counts.values()
                                                             for s in range(1, t)):
            continue
        # 2. the two blocks with the fewest pairs of bad t-sets, and the enumeration
        nbad = [counts[n][t] for n in rows_of]
        a, b = min(itertools.combinations(range(M), 2), key=lambda p: (nbad[p[0]] * nbad[p[1]], p))
        rep["blocks"] = [a, b]
        work = nbad[a] * nbad[b] * math_factorial(t)
        rep["cases"] = work
        exe = Helper.get()
        maxw = max(words(len(c["ingredients"][n]["rows"])) for n in rows_of)
        if work == 0:
            # block a or b has no bad t-set (and none below t): it covers z^t on every t-set
            cand, surv, shown = 0, 0, []
            rep["method"] = "none needed"
        elif exe and work * max(1, M - 2) * maxw * t <= HELPER_WORK and max(nbad[a], nbad[b]) <= HELPER_LIST:
            hp = os.path.join(cz2_tmpdir(c), "H.txt")
            if not os.path.exists(hp):
                with open(hp, "w", encoding="ascii", newline="\n") as f:
                    for row in H:
                        f.write(" ".join(map(str, row)) + "\n")
            res = Helper.run(["enum", t, z, a, b, hp] + [cz2_file(c, n) for n in rows_of])
            shown = []
            for line in res.splitlines():
                f = line.split()
                if f[0] == "survivor":
                    shown.append(list(map(int, f[1:])))
                elif f[:2] == ["enum", "candidates"]:
                    cand = int(f[2])
                elif f[:2] == ["enum", "survivors"]:
                    surv = int(f[2])
            rep["method"] = "cz2help"
        elif work * max(1, M - 2) * t * t <= INGREDIENT_WORK:
            la = py_bad(c["ingredients"][rows_of[a]]["rows"], t, z, True)[1]
            lb = py_bad(c["ingredients"][rows_of[b]]["rows"], t, z, True)[1]
            cand, surv, shown = py_enumerate(c, z, a, b, la, lb)
            rep["method"] = "python"
        else:
            out.append("weight %d: the enumeration (%d x %d bad %d-sets x %d bijections) is above the limit of this "
                       "checker%s" % (wt, nbad[a], nbad[b], t, math_factorial(t), cz2_note(c)))
            continue
        rep["candidates"], rep["survivors"] = cand, surv
        if surv:
            out.append("weight %d: %d t-sets of array columns have no row constant %d (first %s)"
                       % (wt, surv, z, "; ".join(str(s) for s in shown[:3])))
    return out


def enumeration_text(c, rep):
    bad = ", ".join("%s %s" % (n, "/".join("-" if x is None else str(x) for x in v)) for n, v in sorted(rep.get("bad", {}).items()))
    s = "tuple %s^%d; bad s-sets (s = 1..%d) per ingredient: %s" % (rep["z"], c["t"], c["t"], bad or "not computed")
    if "survivors" in rep:
        s += "; blocks %d and %d, %d cases, %d give array columns, %d survivors (%s)" % (
            rep["blocks"][0], rep["blocks"][1], rep["cases"], rep["candidates"], rep["survivors"], rep["method"])
    return s


def math_factorial(n):
    out = 1
    for i in range(2, n + 1):
        out *= i
    return out


CHECKS2 = [("field", check_field), ("shape", check_shape), ("width", check_width),
           ("ingredient_hash", check_ingredient_hash), ("agreement", check_agreement),
           ("relabel", check_relabel), ("quilting", check_quilting2), ("species", check_species2),
           ("enumeration", check_enumeration)]


# assembly-dependent checks (run after the array is built)

def check_symbols(c):
    """the table's parser keeps an array 0-based only if symbol 0 occurs"""
    if 0 not in c["symbols"]:
        return ["the assembled array never uses symbol 0, so the table's canonicalization "
                "(check_submission.parse_array) would not read it as 0-based"]
    return []


def check_N(c):
    if c["N"] != c["exp_N"]:
        return ["the array has N = %d rows, the certificate claims %d" % (c["N"], c["exp_N"])]
    return []


def check_k(c):
    if c["k"] != c["exp_k"]:
        return ["the array has k = %d columns, the certificate claims %d" % (c["k"], c["exp_k"])]
    return []


def check_sha(c):
    if c["sha256"] != c["exp_sha"]:
        return ["the rebuilt array has canonical sha256 %s, the certificate claims %s"
                % (c["sha256"], c["exp_sha"])]
    return []


# ---------------------------------------------------------------------------
# ingredients from the table, and the constructions on arrays (fuse-1, derive-1, product-1)
# ---------------------------------------------------------------------------

def resolve_table(sha, table_dir, where):
    """An ingredient named by the array_sha256 of a counted VERIFIED row of the table (tier VERIFIED,
    not retracted; table/ca_table.py counted()). The array is read from table/arrays (plain or gzip)
    and its canonical text must hash to sha. Returns the rows and the row's t, v, k, N (the largest
    strength among the counted VERIFIED rows of that array)."""
    if not isinstance(sha, str) or not HEX64.match(sha):
        raise CertError("%s: 'table' must be the 64 lower-case hex digits of an array_sha256" % where)
    td = table_dir or REPO_TABLE
    if REPO_TABLE not in sys.path:
        sys.path.insert(0, REPO_TABLE)
    from ca_table import counted
    try:
        with open(os.path.join(td, "ca_table.csv"), newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        with open(os.path.join(td, "MANIFEST.csv"), newline="", encoding="utf-8") as f:
            man = list(csv.DictReader(f))
    except OSError as e:
        raise CertError("%s: cannot read the table in %s: %s" % (where, td, e))
    cand = [r for r in counted(rows) if r["tier"] == "VERIFIED" and r["array_sha256"] == sha]
    if not cand:
        raise CertError("%s: %s is not the array_sha256 of a counted VERIFIED row of the table"
                        % (where, sha[:16]))
    row = max(cand, key=lambda r: int(r["t"]))
    files = [m["file"] for m in man if m["sha256"] == sha]
    if not files:
        raise CertError("%s: the array %s is not stored in table/arrays" % (where, sha[:16]))
    path = os.path.join(td, "arrays", files[0])
    try:
        op = gzip.open if path.endswith(".gz") else open
        with op(path, "rb") as f:
            data = f.read()
    except OSError as e:
        raise CertError("%s: cannot read table/arrays/%s: %s" % (where, files[0], e))
    if hashlib.sha256(data).hexdigest() != sha:
        raise CertError("%s: table/arrays/%s does not hash to %s" % (where, files[0], sha[:16]))
    text = data.decode("ascii")
    if "NA" in text:
        raise CertError("%s: the array has don't-care entries, which an ingredient may not have" % where)
    mat = parse_matrix_text(text, "%s (table/arrays/%s)" % (where, files[0]))
    return {"rows": mat, "table": {"sha256": sha, "file": files[0], "t": int(row["t"]), "v": int(row["v"]),
                                   "k": int(row["k"]), "N": int(row["N"]), "stamp": row["verify_stamp"]}}


def parse_expected(cert, c):
    exp = cert.get("expected")
    only_keys(exp, ("N", "k", "array_sha256"), "expected")
    c["exp_N"] = need_int(exp, "N", 1, None, "expected: ")
    c["exp_k"] = need_int(exp, "k", 1, None, "expected: ")
    sha = exp.get("array_sha256")
    if not isinstance(sha, str) or not HEX64.match(sha):
        raise CertError("expected: array_sha256 must be 64 lowercase hex digits")
    c["exp_sha"] = sha


def parse_array_ingredient(obj, where, c, table_dir):
    """an array ingredient: {"rows": [[...]]}, {"file": name, "sha256": hex} or {"table": sha}"""
    only_keys(obj, ("file", "sha256", "rows", "table"), where)
    if sum(1 for x in ("file", "rows", "table") if x in obj) != 1:
        raise CertError("%s: give exactly one of 'rows', 'file' (with 'sha256') or 'table'" % where)
    d = {"name": where}
    if "table" in obj:
        if "sha256" in obj:
            raise CertError("%s: a table ingredient takes no sha256 (the table hash is its name)" % where)
        d.update(resolve_table(obj["table"], table_dir, where))
    elif "file" in obj:
        fn, h = obj["file"], obj.get("sha256")
        if not isinstance(fn, str) or not NAME_RE.match(fn) or fn.startswith("."):
            raise CertError("%s: file must be a plain file name beside the certificate" % where)
        if not isinstance(h, str) or not HEX64.match(h):
            raise CertError("%s: a file ingredient needs sha256 (64 lowercase hex)" % where)
        try:
            with open(os.path.join(c["dir"], fn), "rb") as f:
                raw = f.read()
        except OSError as ex:
            raise CertError("%s: cannot read %s: %s" % (where, fn, ex))
        d["file"], d["sha_expected"], d["sha_actual"] = fn, h, hashlib.sha256(raw).hexdigest()
        try:
            text = raw.decode("ascii")
        except UnicodeDecodeError:
            raise CertError("%s: file is not ASCII text" % where)
        d["rows"] = parse_matrix_text(text, "%s (%s)" % (where, fn))
    else:
        if "sha256" in obj:
            raise CertError("%s: an inline ingredient takes no sha256" % where)
        rows = obj["rows"]
        if not isinstance(rows, list) or not all(isinstance(r, list) and all(is_int(x) and x >= 0 for x in r)
                                                 for r in rows):
            raise CertError("%s: rows must be a list of lists of nonnegative integers" % where)
        d["rows"] = [list(r) for r in rows]
    return d


ARRAY_KEYS = {"fuse-1": ("input", "rows"), "derive-1": ("input", "column", "symbol"),
              "product-1": ("first", "second", "constant_rows")}


def load_array_kind(cert, raw, path, table_dir):
    kind = cert["construction"]
    only_keys(cert, ("format", "construction", "t", "v", "expected", "notes") + ARRAY_KEYS[kind], "certificate")
    if cert.get("format") != FORMAT:
        raise CertError("format must be %r" % FORMAT)
    if "notes" in cert and not (isinstance(cert["notes"], str) or
                                (isinstance(cert["notes"], list) and all(isinstance(x, str) for x in cert["notes"]))):
        raise CertError("notes must be a string or a list of strings")
    t = need_int(cert, "t", 1, 32)
    v = need_int(cert, "v", 2, 64)
    c = {"kind": kind, "t": t, "v": v, "dir": os.path.dirname(os.path.abspath(path)),
         "cert_sha256": hashlib.sha256(raw).hexdigest(), "ingredients": {}}
    parse_expected(cert, c)
    # each ingredient with the strength and the number of symbols the theorem needs of it
    roles = {"fuse-1": [("input", t, v + 1)], "derive-1": [("input", t + 1, v)],
             "product-1": [("first", 2, v), ("second", 2, v)]}[kind]
    for role, nt, nv in roles:
        if role not in cert:
            raise CertError("missing key %r" % role)
        d = parse_array_ingredient(cert[role], role, c, table_dir)
        d["need_t"], d["need_v"] = nt, nv
        c["ingredients"][role] = d
    if kind == "fuse-1":
        zr = cert.get("rows", [0, 1])
        if not (isinstance(zr, list) and len(zr) == 2 and all(is_int(x) and x >= 0 for x in zr)):
            raise CertError("rows must be [z, r], two row numbers (default [0, 1])")
        c["zr"] = list(zr)
    elif kind == "derive-1":
        c["column"] = need_int(cert, "column", 0)
        c["symbol"] = need_int(cert, "symbol", 0)
    else:
        cr = cert.get("constant_rows", [None, None])
        if not (isinstance(cr, list) and len(cr) == 2 and all(x is None or (is_int(x) and x >= 0) for x in cr)):
            raise CertError("constant_rows must be [a, b], each a row number or null")
        c["constant_rows"] = list(cr)
    return c


def ca_missing(rows, t, v, limit=None):
    """Exhaustive: None if rows (N x k over 0..v-1) cover every t-tuple on every t-set of columns,
    else (columns, a missing tuple). Raises ValueError when C(k, t) * N exceeds limit."""
    k = len(rows[0])
    if limit is not None and comb(k, t) * len(rows) * t > limit:
        raise ValueError("C(%d, %d) * %d is above the limit of this check" % (k, t, len(rows)))
    for r in rows:
        for j, x in enumerate(r):
            if not 0 <= x < v:            # a symbol outside 0..v-1 must not count towards a t-set
                return [j], [x]
    cols = [tuple(r[j] for r in rows) for j in range(k)]
    full = v ** t
    for cs in itertools.combinations(range(k), t):
        seen = set(zip(*[cols[j] for j in cs]))
        if len(seen) < full:
            for tup in itertools.product(range(v), repeat=t):
                if tup not in seen:
                    return list(cs), list(tup)
    return None


def check_array_shape(c):
    """every array ingredient is a nonempty rectangular array over the symbols 0..v_in-1 the theorem
    needs of it, with at least as many columns as the strength needed of it"""
    out = []
    for name, ing in c["ingredients"].items():
        rows = ing["rows"]
        if not rows or not rows[0]:
            out.append("ingredient %s has no rows" % name)
            continue
        w = len(rows[0])
        bad = [i for i, r in enumerate(rows) if len(r) != w]
        if bad:
            out.append("ingredient %s is ragged (row %d has %d entries, row 0 has %d)"
                       % (name, bad[0], len(rows[bad[0]]), w))
            continue
        big = [(i, j) for i, r in enumerate(rows) for j, x in enumerate(r) if x >= ing["need_v"]]
        if big:
            i, j = big[0]
            out.append("ingredient %s: entry %d at row %d column %d is not a symbol 0..%d"
                       % (name, rows[i][j], i, j, ing["need_v"] - 1))
        if w < ing["need_t"]:
            out.append("ingredient %s has %d columns, fewer than the strength %d it needs"
                       % (name, w, ing["need_t"]))
    return out


def check_ingredient_ca(c):
    """every inline or file ingredient is a covering array of the strength and over the number of
    symbols the theorem needs, checked here exhaustively (every t-set, every tuple); a table
    ingredient is checked by ingredient_table instead"""
    out = []
    for name, ing in c["ingredients"].items():
        if "table" in ing:
            continue
        rows = ing["rows"]
        if not rows or not rows[0] or any(len(r) != len(rows[0]) for r in rows) or len(rows[0]) < ing["need_t"]:
            out.append("ingredient %s cannot be a covering array of strength %d (see shape)" % (name, ing["need_t"]))
            continue
        try:
            miss = ca_missing(rows, ing["need_t"], ing["need_v"], INGREDIENT_WORK)
        except ValueError as e:
            out.append("ingredient %s is too large to check here (%s); enter it in the table first and name "
                       "it by its array_sha256" % (name, e))
            continue
        if miss:
            out.append("ingredient %s is not a CA(%d; %d, %d, %d): columns %s miss the tuple %s"
                       % (name, len(rows), ing["need_t"], len(rows[0]), ing["need_v"], miss[0], miss[1]))
    return out


def check_table_ingredients(c):
    """every table ingredient is the array of a counted VERIFIED row (resolved when the certificate
    is read) whose strength is at least the strength needed, with the number of symbols needed and
    the number of rows and columns of the array read"""
    out = []
    for name, ing in c["ingredients"].items():
        tb = ing.get("table")
        if not tb:
            continue
        rows = ing["rows"]
        if tb["t"] < ing["need_t"]:
            out.append("ingredient %s: the table row has strength %d, the construction needs %d"
                       % (name, tb["t"], ing["need_t"]))
        if tb["v"] != ing["need_v"]:
            out.append("ingredient %s: the table row has v = %d, the construction needs %d"
                       % (name, tb["v"], ing["need_v"]))
        if (tb["N"], tb["k"]) != (len(rows), len(rows[0]) if rows else 0):
            out.append("ingredient %s: the table row is %d x %d, the stored array %d x %d"
                       % (name, tb["N"], tb["k"], len(rows), len(rows[0]) if rows else 0))
    return out


def check_fuse_strength(c):
    """fuse-1: t >= 2 (the proof covers a tuple with the help of a second column)"""
    return [] if c["t"] >= 2 else ["fuse-1 needs t >= 2 (t = %d)" % c["t"]]


def check_fuse_rows(c):
    """fuse-1: the rows z and r are two distinct rows of the input"""
    z, r = c["zr"]
    n = len(c["ingredients"]["input"]["rows"])
    if z == r or not (z < n and r < n):
        return ["rows [%d, %d] are not two distinct rows of the %d-row input" % (z, r, n)]
    return []


def check_derive_column(c):
    """derive-1: the column is a column of the input, and the input has at least t+1 columns"""
    rows = c["ingredients"]["input"]["rows"]
    k = len(rows[0]) if rows else 0
    out = []
    if not c["column"] < k:
        out.append("column %d is not a column of the %d-column input" % (c["column"], k))
    if k - 1 < c["t"]:
        out.append("the derived array would have %d columns, fewer than t = %d" % (k - 1, c["t"]))
    return out


def check_derive_symbol(c):
    """derive-1: the symbol is one of 0..v-1"""
    return [] if c["symbol"] < c["v"] else ["symbol %d is not one of 0..%d" % (c["symbol"], c["v"] - 1)]


def check_product_strength(c):
    """product-1: the direct product gives strength 2 only"""
    return [] if c["t"] == 2 else ["product-1 gives strength 2, the certificate says t = %d" % c["t"]]


def check_product_constant_rows(c):
    """product-1: each constant_rows entry is null or a row of its ingredient"""
    out = []
    for role, x in zip(("first", "second"), c["constant_rows"]):
        n = len(c["ingredients"][role]["rows"])
        if x is not None and x >= n:
            out.append("constant_rows: %d is not a row of the %d-row %s ingredient" % (x, n, role))
    return out


def rows_fuse(c):
    A = c["ingredients"]["input"]["rows"]
    z, r = c["zr"]
    top = c["v"]                       # the symbol removed: the largest of the input, v
    Z = A[z]

    def tau(x, j):                     # the transposition Z[j] <-> top in column j
        return top if x == Z[j] else Z[j] if x == top else x
    R = [tau(x, j) for j, x in enumerate(A[r])]
    for i, row in enumerate(A):
        if i in (z, r):
            continue
        out = []
        for j, x in enumerate(row):
            y = tau(x, j)
            if y == top:
                y = R[j] if R[j] != top else 0
            out.append(y)
        yield out


def rows_derive(c):
    col, s = c["column"], c["symbol"]
    for row in c["ingredients"]["input"]["rows"]:
        if row[col] == s:
            yield row[:col] + row[col + 1:]


def normalize(rows, r):
    """row r made all 0 by the transposition rows[r][j] <-> 0 in every column j (None: unchanged)"""
    if r is None:
        return rows
    Z = rows[r]
    return [[0 if x == Z[j] else Z[j] if x == 0 else x for j, x in enumerate(row)] for row in rows]


def rows_product(c):
    A = normalize(c["ingredients"]["first"]["rows"], c["constant_rows"][0])
    B = normalize(c["ingredients"]["second"]["rows"], c["constant_rows"][1])
    k1, k2 = len(A[0]), len(B[0])
    const_a = {row[0] for row in A if len(set(row)) == 1}
    for a in A:
        yield [a[i] for i in range(k1) for _ in range(k2)]
    for b in B:
        if len(set(b)) == 1 and b[0] in const_a:
            continue                   # the same row as a constant row of the first part
        yield [b[j] for _ in range(k1) for j in range(k2)]


ROWS_OF = {"fuse-1": rows_fuse, "derive-1": rows_derive, "product-1": rows_product}


def width_of(c):
    ing = c["ingredients"]
    if c["kind"] == "fuse-1":
        return len(ing["input"]["rows"][0])
    if c["kind"] == "derive-1":
        return len(ing["input"]["rows"][0]) - 1
    return len(ing["first"]["rows"][0]) * len(ing["second"]["rows"][0])


def assemble_array_kind(c, write=None):
    """the rows of the construction in order, in the table's canonical text, hashed as a stream"""
    h = hashlib.sha256()
    fout = open(write, "w", encoding="ascii", newline="\n") if write else None
    N, symbols = 0, set()
    try:
        for row in ROWS_OF[c["kind"]](c):
            line = " ".join(map(str, row)) + "\n"
            symbols.update(row)
            h.update(line.encode("ascii"))
            if fout:
                fout.write(line)
            N += 1
    finally:
        if fout:
            fout.close()
    c["N"], c["k"], c["sha256"], c["symbols"] = N, width_of(c), h.hexdigest(), symbols


def check_out_symbols(c):
    """every symbol of the rebuilt array is one of 0..v-1 (the theorem's alphabet)"""
    bad = sorted(x for x in c["symbols"] if not 0 <= x < c["v"])
    return ["the rebuilt array uses symbol %d, outside 0..%d" % (bad[0], c["v"] - 1)] if bad else []


KIND_CHECKS = {
    "fuse-1": [("shape", check_array_shape), ("ingredient_hash", check_ingredient_hash),
               ("ingredient_ca", check_ingredient_ca), ("fuse_strength", check_fuse_strength),
               ("fuse_rows", check_fuse_rows)],
    "derive-1": [("shape", check_array_shape), ("ingredient_hash", check_ingredient_hash),
                 ("ingredient_ca", check_ingredient_ca), ("derive_column", check_derive_column),
                 ("derive_symbol", check_derive_symbol)],
    "product-1": [("shape", check_array_shape), ("ingredient_hash", check_ingredient_hash),
                  ("ingredient_ca", check_ingredient_ca), ("product_strength", check_product_strength),
                  ("product_constant_rows", check_product_constant_rows)],
}
# run for every construction (powercz-1 included) that names an ingredient by its table hash
TABLE_CHECKS = [("ingredient_table", check_table_ingredients)]
KIND_POST_CHECKS = [("alphabet", check_out_symbols)]


# order matters only for reporting; every check runs (those after the assembly only if the
# array could be built)
CHECKS = [("field", check_field), ("shape", check_shape), ("width", check_width),
          ("ingredient_hash", check_ingredient_hash), ("agreement", check_agreement),
          ("quilting", check_quilting), ("species", check_species)]
POST_CHECKS = [("symbols", check_symbols), ("N", check_N), ("k", check_k), ("sha256", check_sha)]


# ---------------------------------------------------------------------------
# assembly in the table's canonical text
# ---------------------------------------------------------------------------

def assemble(c, write=None):
    """stack block i = ingredient(i)[:, H[i]] for i = 0..M-1; hash the canonical text
    (one run per line, single spaces, '\\n' after every line, symbols 0-based)"""
    h = hashlib.sha256()
    fout = open(write, "w", encoding="ascii", newline="\n") if write else None
    N = 0
    symbols = set()
    try:
        for i, r in enumerate(c["family"]["rows"]):
            Q = c["ingredients"][r["ingredient"]]["rows"]
            Hi = c["H"][i]
            used = sorted(set(Hi))
            for qrow in Q:
                strs = [str(x) for x in qrow]
                line = " ".join([strs[s] for s in Hi]) + "\n"
                symbols.update(qrow[s] for s in used)
                h.update(line.encode("ascii"))
                if fout:
                    fout.write(line)
                N += 1
    finally:
        if fout:
            fout.close()
    c["N"], c["k"], c["sha256"], c["symbols"] = N, len(c["H"][0]), h.hexdigest(), symbols


# ---------------------------------------------------------------------------
# driver
# ---------------------------------------------------------------------------

def run(path, write=None, log=None, table_dir=None):
    """check the certificate at path; returns a dict with ok, failures [(check, message)],
    passed [check], N, k, sha256, species_table, construction, ingredients, seconds. Raises
    CertError when malformed. table_dir: where "table" ingredients are found (default: the table/
    of this repository)."""
    t0 = time.time()
    say = log or (lambda s: None)
    c = load_certificate(path, table_dir)
    kind = c["kind"]
    if kind in ARRAY_KINDS:
        checks, post, build = KIND_CHECKS[kind], POST_CHECKS + KIND_POST_CHECKS, assemble_array_kind
        say("certificate %s: %s, t = %d, v = %d, ingredients %s"
            % (path, kind, c["t"], c["v"], ", ".join("%s %d x %d" % (n, len(i["rows"]), len(i["rows"][0]) if i["rows"] else 0)
                                                    for n, i in c["ingredients"].items())))
    elif kind == "powercz-2":
        build_family(c)
        apply_relabel(c)
        checks, post, build = CHECKS2, POST_CHECKS, assemble
        say("certificate %s: powercz-2, %s, t = %d, v = %d, e = %d, M = %d rows (%d relabelled), k = %d columns, "
            "enumerate_weights %s" % (path, c["family"]["type"], c["t"], c["v"], c["e"], len(c["H"]),
                                      c["relabelled_rows"], len(c["H"][0]), c["enumerate_weights"]))
    else:
        build_family(c)
        checks, post, build = CHECKS, POST_CHECKS, assemble
        say("certificate %s: %s, t = %d, v = %d, e = %d, M = %d rows, k = %d columns"
            % (path, c["family"]["type"], c["t"], c["v"], c["e"], len(c["H"]), len(c["H"][0])))
    if any("table" in i for i in c["ingredients"].values()):
        checks = checks + TABLE_CHECKS
    failures, passed = [], []
    try:
        for name, fn in checks:
            try:
                msgs = fn(c)
            except Exception as ex:          # a check that cannot complete is a failure
                msgs = ["the check could not complete: %r" % (ex,)]
            if msgs:
                failures += [(name, m) for m in msgs]
                for m in msgs:
                    say("FAIL [%s] %s" % (name, m))
            else:
                passed.append(name)
                say("pass [%s]" % name)
            if name == "enumeration":
                for wt, rep in sorted(c.get("enumeration", {}).items()):
                    say("  weight %d: %s" % (wt, enumeration_text(c, rep)))
    finally:
        if "cz2_tmp" in c:
            import shutil
            shutil.rmtree(c["cz2_tmp"], ignore_errors=True)
    built = False
    try:
        build(c, write)
        built = True
    except Exception as ex:
        failures.append(("assembly", "the array cannot be assembled: %r" % (ex,)))
        say("FAIL [assembly] %r" % (ex,))
    if built:
        for name, fn in post:
            try:
                msgs = fn(c)
            except Exception as ex:
                msgs = ["the check could not complete: %r" % (ex,)]
            if msgs:
                failures += [(name, m) for m in msgs]
                for m in msgs:
                    say("FAIL [%s] %s" % (name, m))
            else:
                passed.append(name)
                say("pass [%s]" % name)
    ings = []
    for name, i in c["ingredients"].items():
        if "table" in i:
            ings.append(dict(name=name, source="table", sha256=i["table"]["sha256"], file=i["table"]["file"]))
        elif "file" in i:
            ings.append(dict(name=name, source="file", sha256=i["sha_actual"], file=i["file"]))
        else:
            ings.append(dict(name=name, source="inline"))
    return {"ok": built and not failures, "failures": failures, "passed": passed,
            "cert_sha256": c["cert_sha256"], "construction": kind, "ingredients": ings,
            "N": c.get("N"), "k": c.get("k"), "sha256": c.get("sha256"), "t": c["t"],
            "v": c["v"], "species_table": c.get("species_table"),
            "seconds": time.time() - t0, **({"enumerate_weights": c["enumerate_weights"],
                                             "enumeration": c.get("enumeration", {})}
                                            if kind == "powercz-2" else {})}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    write, quiet = None, False
    if "--write" in argv:
        i = argv.index("--write")
        if i + 1 >= len(argv):
            print(__doc__)
            return 2
        write = argv[i + 1]
        del argv[i:i + 2]
    if "--quiet" in argv:
        argv.remove("--quiet")
        quiet = True
    table_dir = None
    if "--table-dir" in argv:
        i = argv.index("--table-dir")
        if i + 1 >= len(argv):
            print(__doc__)
            return 2
        table_dir = argv[i + 1]
        del argv[i:i + 2]
    if len(argv) != 1 or argv[0].startswith("-"):
        print(__doc__)
        return 2
    log = None if quiet else print
    try:
        res = run(argv[0], write, log, table_dir)
    except CertError as ex:
        print("MALFORMED: %s" % ex)
        return 2
    if not quiet and res["species_table"]:
        print("species table (species, tau, rows needed, rows declared):")
        for sp, ta, need, n in res["species_table"]:
            print("  %-14s tau %2d  need >= %2d  have %2d%s" % (fmt_species(sp, res["v"]), ta, need, n,
                                                               "  (enumerated)" if sp[1] in
                                                               res.get("enumerate_weights", ()) else ""))
    print("certificate sha256 = %s" % res["cert_sha256"])
    if res["sha256"]:
        print("N = %s  k = %s  t = %d  v = %d  sha256 = %s"
              % (res["N"], res["k"], res["t"], res["v"], res["sha256"]))
    print("%s (%.2f s)" % ("CERTIFICATE VALID" if res["ok"] else
                           "CERTIFICATE REJECTED: %d failure(s) in %s"
                           % (len(res["failures"]),
                              ", ".join(sorted({f[0] for f in res["failures"]}))),
                           res["seconds"]))
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
