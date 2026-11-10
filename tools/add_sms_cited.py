#!/usr/bin/env python3
"""add_sms_cited.py - appends to table/ca_table.csv, as CITED S7 rows, the published sizes of
two papers of Kianoosh Shokri and Lucia Moura that were not in the table on 2026-11-09:

  A  K. Shokri, L. Moura and B. Stevens, arXiv:2510.13122v3 (16 Oct 2026), strength 4:
     Theorem 5.1, CA(3q^4 - 2; 4, (q^2+1)/2, q), and Corollary 6.5 (Theorem 6.2 with the
     ingredient of Remark 6.4), CA(3q^4 + (q - 2)(2q^3 - q); 4, q^2 + 1, q), odd prime powers q
     (their Tables 4 and 6).
  B  K. Shokri and L. Moura, J. Combin. Des. 33 (2025) 156-171, doi:10.1002/jcd.21963, strength 3:
     the x-plication constructions. The journal text was not read here (it is not openly
     fetchable); the theorems and Table 5.6 were read in Chapter 5 of K. Shokri's PhD thesis
     (University of Ottawa, 2026, doi:10.20381/ruor-31663), which says that the chapter was
     published in this paper. Theorem numbers are therefore the thesis numbers.

Every N is computed here from the theorem's formula and checked against the value the paper
(A) or the thesis table (B) prints; two B values (q = 23 and 25, q-plication) lie past the
thesis table's k <= 10000 and are formula values only, and their rows say so.
The previous best at entry is computed from the counted rows (CITED and VERIFIED) of the table.

Usage, from the repository root:
    python3 tools/add_sms_cited.py YYYY-MM-DD           # dry run: print the rows
    python3 tools/add_sms_cited.py YYYY-MM-DD --apply   # append them
"""
import csv, io, sys, datetime

DATE = sys.argv[1]
datetime.datetime.strptime(DATE, "%Y-%m-%d")
APPLY = "--apply" in sys.argv[2:]

ARXIV = "arXiv:2510.13122v3"
JCD = "doi:10.1002/jcd.21963"
THESIS = "doi:10.20381/ruor-31663"


def a51(q):
    return 3 * q ** 4 - 2, (q * q + 1) // 2


def a65(q):
    return 3 * q ** 4 + (q - 2) * (2 * q ** 3 - q), q * q + 1


B_LAWS = {
    # thesis number: (name, N(q), k(q))
    "Theorem 5.2.7": ("2-plication", lambda q: 4 * q ** 3 - 5 * q ** 2 + 2 * q,
                      lambda q: 2 * (q * q + q + 1), "4q^3 - 5q^2 + 2q", "2(q^2 + q + 1)"),
    "Theorem 5.2.8": ("q-plication", lambda q: 5 * q ** 3 - 6 * q ** 2 + 2 * q,
                      lambda q: q * (q * q + q + 1), "5q^3 - 6q^2 + 2q", "q(q^2 + q + 1)"),
    "Theorem 5.2.11": ("q^2-plication", lambda q: 8 * q ** 3 - 10 * q ** 2 + 4 * q - 1,
                       lambda q: q * q * (q * q + q + 1), "8q^3 - 10q^2 + 4q - 1", "q^2(q^2 + q + 1)"),
    "Corollary 5.2.12": ("q^2-plication for even q", lambda q: 8 * q ** 3 - 10 * q ** 2 + 3 * q,
                         lambda q: q * q * (q * q + q + 1), "8q^3 - 10q^2 + 3q", "q^2(q^2 + q + 1)"),
    "Theorem 5.2.13": ("(q^2-q+1)-plication", lambda q: 8 * q ** 3 - 10 * q ** 2 + 3 * q,
                       lambda q: (q * q - q + 1) * (q * q + q + 1), "8q^3 - 10q^2 + 3q",
                       "(q^2 - q + 1)(q^2 + q + 1)"),
}

# (paper, rule, q, the value printed in the paper or the thesis table, or None for a formula value)
A_ROWS = [("51", 17, 250561), ("51", 19, 390961), ("51", 23, 839521), ("51", 25, 1171873),
          ("65", 17, 397698), ("65", 19, 623846), ("65", 23, 1350054), ("65", 25, 1890050),
          ("65", 13, 133874)]
B_ROWS = [("Theorem 5.2.11", 7, 2281), ("Theorem 5.2.13", 7, 2275), ("Corollary 5.2.12", 8, 3480),
          ("Theorem 5.2.8", 16, 18976), ("Theorem 5.2.8", 17, 22865), ("Theorem 5.2.8", 19, 32167),
          ("Theorem 5.2.7", 23, 46069), ("Theorem 5.2.7", 25, 59425),
          ("Theorem 5.2.8", 23, None), ("Theorem 5.2.8", 25, None)]

raw = open("table/ca_table.csv", "rb").read().decode("utf-8")
lines = raw.split("\r\n"); assert lines[-1] == ""
rows = list(csv.reader(lines[:-1]))
hdr = rows[0]; assert hdr[:5] == ["t", "v", "k", "N", "tier"] and len(hdr) == 17
if any(r[7] in (ARXIV, JCD) and r[4] == "CITED" for r in rows[1:]):
    sys.exit("the rows of add_sms_cited.py are already in the table")
counted = [(int(r[0]), int(r[1]), int(r[2]), int(r[3]), r[4], r[5], i)
           for i, r in enumerate(rows[1:]) if r[4] in ("CITED", "VERIFIED")]


def previous_best(t, v, k):
    c = [(n, kk, i, tier, src) for tt, vv, kk, n, tier, src, i in counted if tt == t and vv == v and kk >= k]
    n, kk, i, tier, src = min(c)
    return n, kk, tier, src


def is_prime(q):
    return q > 1 and all(q % d for d in range(2, int(q ** 0.5) + 1))


new = []
for rule, q, printed in A_ROWS:
    N, k = a51(q) if rule == "51" else a65(q)
    assert N == printed, (rule, q, N, printed)
    pb, pk, ptier, psrc = previous_best(4, q, k)
    if rule == "51":
        where = "Theorem 5.1 and Table 4"
        detail = ("Shokri, Moura and Stevens, arXiv:2510.13122v3 (16 Oct 2026), Theorem 5.1 and Table 4, "
                  "q = %d: CA(3q^4 - 2; 4, (q^2+1)/2, q)" % q)
        cons = ("strength-4 construction from three truncated Moebius planes (Shokri, Moura and Stevens 2025, "
                "Theorem 5.1): for l = 1, 2, 4, all F_q-linear combinations of the rows of the 4 x (q^2+1)/2 matrix "
                "whose columns are the coordinate vectors of alpha^(l(q+1)j), j = i or i + (q^2+1)/2 for each "
                "i < (q^2+1)/2, alpha primitive in F_(q^4); the three q^4-row arrays stacked with two of the three "
                "zero rows removed, N = 3q^4 - 2, q = %d" % q)
        script, built = "tools/sms_theorem51.py", "CA(43921; 4, 61, 11) and CA(85681; 4, 85, 13)"
    else:
        where = "Theorem 6.2 with Corollary 6.5 and Table 6"
        detail = ("Shokri, Moura and Stevens, arXiv:2510.13122v3 (16 Oct 2026), Theorem 6.2 with Corollary 6.5 "
                  "and Table 6, q = %d: CA(3q^4 + (q - 2)(2q^3 - q); 4, q^2 + 1, q)" % q)
        cons = ("strength-4 recursive construction of Shokri, Moura and Stevens 2025 (Theorem 6.2 with "
                "Corollary 6.5): over F_(q^4), all F_q-linear combinations of the rows of G^(q+1) on q^2+1 columns, "
                "two such arrays from G^(2(q+1)) and G^(4(q+1)) on (q^2+1)/2 columns written twice side by side "
                "(the second with e_0 added on the right half), and q - 2 blocks R | R + e_r (e_0, ..., e_(q-2) the "
                "nonzero elements of F_q) with R the CA(2q^3 - q; 3, (q^2+1)/2, q) of their Remark 6.4 (the first "
                "(q^2+1)/2 columns of the CA(2q^3 - q; 3, q^2 - q + 3, q) of their Theorem 3.4 (Torres-Jimenez and Izquierdo-Marquez 2018)); "
                "N = 3q^4 + (q - 2)(2q^3 - q), q = %d" % q)
        script, built = "tools/sms_theorem62.py", "CA(67782; 4, 122, 11)"
    if q == 13:
        arr = ("no array published by the authors; the verified CA(133873; 4, 170, 13) in the table (entered 2026-11-04) is Bai XunDi's "
               "reconstruction of this construction with one redundant row removed")
    elif is_prime(q):
        arr = ("no array published, and none checked here for q = %d yet; %s builds this construction for "
               "prime q and gave the verified %s" % (q, script, built))
    else:
        arr = ("no array published, and none checked here: q = %d is a prime power, and %s works only for "
               "prime q (arithmetic mod q)" % (q, script))
    if pb <= N:
        cmp = ("at entry: previous best %d (k=%d, %s, %s), so this row is not the best known; it records the "
               "paper's own value, as CA(67782; 4, 122, 11) does at q = 11" % (pb, pk, ptier, psrc))
    else:
        cmp = "at entry: previous best %d (k=%d, %s, %s)" % (pb, pk, ptier, psrc)
    notes = ("credit: K. Shokri, L. Moura and B. Stevens 2025 (the construction and the size, arXiv:2510.13122v3, "
             "%s, an arXiv preprint with no journal reference as of %s); %s; %s" % (where, DATE, cmp, arr))
    new.append([4, q, k, N, "CITED", "S7", detail, ARXIV, "", "", DATE, notes, "", "", cons, "mobius-sms2025", ""])

for rule, q, printed in B_ROWS:
    name, fN, fk, sN, sk = B_LAWS[rule]
    N, k = fN(q), fk(q)
    if printed is not None:
        assert N == printed, (rule, q, N, printed)
        assert k <= 10000
        tab = "thesis %s and Table 5.6" % rule
        beyond = ""
    else:
        assert k > 10000
        tab = "thesis %s" % rule
        beyond = ("; a formula value, not in the paper's comparison table, which stops at k = 10000 "
                  "(thesis Table 5.6)")
    pb, pk, ptier, psrc = previous_best(3, q, k)
    assert pb > N, (rule, q, N, pb)
    detail = ("Shokri and Moura 2025, J. Combin. Des. 33 (2025) 156-171, %s with q = %d: CA(%s; 3, %s, q)%s; "
              "the theorem and the value were read in Chapter 5 of K. Shokri's PhD thesis, University of Ottawa, "
              "2026 (%s), %s, which the thesis says was published in this paper; the journal text was not read "
              "here, so the theorem number is the thesis number"
              % (name, q, sN, sk, beyond, THESIS, tab))
    notes = ("credit: K. Shokri and L. Moura 2025 (the construction and the size, J. Combin. Des. 33 (2025) 156-171, "
             "%s, %s in the numbering of K. Shokri's PhD thesis, %s, the journal's own numbering not checked%s); "
             "at entry: previous best %d (k=%d, %s, %s); no array published, and none checked here"
             % (JCD, tab[len("thesis "):], THESIS,
                ", a formula value past the paper's table" if printed is None else "",
                pb, pk, ptier, psrc))
    cons = ("%s construction of Shokri and Moura 2025 (J. Combin. Des. 33, 156-171, thesis %s), from linear "
            "feedback shift register sequences over F_q: CA(%s; 3, %s, q), q = %d" % (name, rule, sN, sk, q))
    new.append([3, q, k, N, "CITED", "S7", detail, JCD, "", "", DATE, notes, "", "", cons,
                "lfsr-sm2025;new " + THESIS, ""])

for r in new:
    print("CA(%d; %d, %d, %d)  %s" % (r[3], r[0], r[2], r[1], r[11].split("; ")[1] if "; " in r[11] else ""))
if APPLY:
    b = io.StringIO(); w = csv.writer(b, lineterminator="\r\n")
    for r in new:
        w.writerow(r)
    open("table/ca_table.csv", "wb").write((raw + b.getvalue()).encode("utf-8"))
    print("%d CITED S7 rows added; date %s" % (len(new), DATE))
else:
    print("dry run: %d rows; add --apply to append them" % len(new))
