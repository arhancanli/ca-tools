"""sm_xplication.py - build the strength-3 x-plication covering arrays of K. Shokri and L. Moura,
New families of strength-3 covering arrays using linear feedback shift register sequences,
J. Combin. Des. 33 (2025) 156-171 (doi:10.1002/jcd.21963), as stated in Chapter 5 of K. Shokri's
PhD thesis (University of Ottawa, 2026, doi:10.20381/ruor-31663), which the numbering below follows.

  THEOREM   thesis              array
  2         Theorem 5.2.7       CA(4q^3 - 5q^2 + 2q; 3, 2(q^2+q+1), q), q >= 2       (2-plication)
  q         Theorem 5.2.8       CA(5q^3 - 6q^2 + 2q; 3, q(q^2+q+1), q), q >= 3       (q-plication)
  q2        Theorem 5.2.11      CA(8q^3 - 10q^2 + 4q - 1; 3, q^2(q^2+q+1), q)       (q^2-plication)
  q2even    Corollary 5.2.12    CA(8q^3 - 10q^2 + 3q; 3, q^2(q^2+q+1), q), q = 2^n  (q^2-plication, even q)
  q2q1      Theorem 5.2.13      CA(8q^3 - 10q^2 + 3q; 3, (q^2-q+1)(q^2+q+1), q)     ((q^2-q+1)-plication)

All five are the general theorem (thesis Theorem 5.2.6) with x column blocks of k = q^2+q+1 columns:
row block 0 is A(G1) and row block 1 is A(G2), G1 and G2 the 3 x k matrices with columns L(alpha^j)
and L(alpha^-j), 0 <= j < k, alpha a root of a primitive cubic f (Construction 3.1.1, Theorem 3.2.4);
row blocks 2 .. m-1 are P, the CA(2q^2 - q; 2, q^2+q+1, q) of Corollary 5.1.9 (its first q^2+q+1
columns); block r is shifted in column block l by d_rl, D = (d_rl) an m x x difference covering array;
the last row block has the row c_l repeated k times in column block l, for the rows c of the last
ingredient C', which is the thesis's CA(N2; 3, x, q) with its redundant rows removed:

  2       x = 2,     D = columns 0 and 1 of the multiplication table (m = q), no last block
  q       x = q,     D = the multiplication table DCA(q; 2, q, q) (Theorem 5.1.11), C' = the Bush
                     OA(q^3; 3, q, q) (Corollary 5.1.2) without the q^2 rows of degree at most 1
                     (rows c2 X^2 + c1 X + c0 at the points, (c2, c1, c0) in product order)
  q2      x = q^2,   D = D (x) D without one zero row, DCA(2q - 1; 2, q^2, q) (Theorem 5.1.13),
                     C' = A(G1') without the 2q^2 - q rows u with u_1 = 0 or u_2 = 0, then A(G2')
                     without its zero row (G1' = Table 5.3, G2' the matching columns of G2)
  q2even  as q2, with G2' = (1, x^2 + y, y^2 + by + cx) for the column (1, x, y) of G1' (Colbourn,
          Ingalls, Jedwab, Saaltink, Smith and Stevens 2024, Corollary 3.4 and Theorem 3.8, b and c
          with X^3 + bX + c irreducible), and A(G2') without its q constant rows
  q2q1    as q2, without the q - 1 column blocks where G2' has first entry 0 (D and G1' lose the same
          columns), G2' scaled to first entry 1, and A(G2') without its q constant rows

Conventions (the same as tools/construction_cert.py, construction sm-xplication-1, which checks the
hypotheses of the general theorem and rebuilds this array from the certificate written by
--certificate): F_q as in tools/sms_theorem51.py (labels 0..q-1, the default modulus the first
irreducible one); e the smallest label of order q - 1; the points a_0 = 0, a_i = e^(i-1); D(r, c) =
a_r a_c for the multiplication table; in D (x) D the column j q + z has a_r a_z in the first q rows and
a_r a_j in the other q - 1 (r = 1 .. q-1); G1' has the column (1, a_z, a_j) at j q + z. f is the first
primitive cubic in the order of itertools.product over its lower coefficients (constant term first,
nonzero), and for q2q1 the first one for which G2' has exactly q - 1 columns with first entry 0
(the thesis says every primitive cubic does; that is not so, see tools/CONSTRUCTION_CERT.md).
Rows of A(G) are in the order of u in itertools.product(range(q), repeat=3), row = sum u_i G[i].
Columns of the array: column l k + i is column i of column block l.

Usage: python3 tools/sm_xplication.py THEOREM q [--modulus c0,...] [--cubic c0,c1,c2]
           [--certificate CERT.json] [--columns K] > out.txt
Writes the canonical text (0-based, single spaces, a newline after every row) to stdout; --columns K
writes only the first K columns (for tests); the choices are printed to stderr. Needs numpy.
"""
import hashlib, itertools, json, os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sms_theorem51 import GF, prime_power, primitive, powers, span, HashOut, field_json, write_rows, mulmod, is_prime  # noqa: E402

THEOREMS = {"2": "5.2.7", "q": "5.2.8", "q2": "5.2.11", "q2even": "5.2.12", "q2q1": "5.2.13"}


def formula(thm, q):
    K = q * q + q + 1
    return {"2": (4 * q ** 3 - 5 * q ** 2 + 2 * q, 2 * K),
            "q": (5 * q ** 3 - 6 * q ** 2 + 2 * q, q * K),
            "q2": (8 * q ** 3 - 10 * q ** 2 + 4 * q - 1, q * q * K),
            "q2even": (8 * q ** 3 - 10 * q ** 2 + 3 * q, q * q * K),
            "q2q1": (8 * q ** 3 - 10 * q ** 2 + 3 * q, (q * q - q + 1) * K)}[thm]


def is_primitive(F, f):
    """x has order q^3 - 1 modulo the monic cubic f (constant term first)"""
    q, m = F.q, 3
    order = q ** m - 1
    one, x = [1, 0, 0], [0, 1, 0]

    def pw(e):
        res, base = one[:], x[:]
        while e:
            if e & 1:
                res = mulmod(F, res, base, f, m)
            base = mulmod(F, base, base, f, m)
            e >>= 1
        return res
    primes = [p for p in range(2, order + 1) if order % p == 0 and is_prime(p)]
    return pw(order) == one and all(pw(order // p) != one for p in primes)


def dump_certificate(c, path):
    """one key per line, matrices one row per line"""
    def val(v):
        if isinstance(v, list) and v and isinstance(v[0], list):
            if isinstance(v[0][0], list):
                return "[\n" + ",\n".join("  " + val(H) for H in v) + "\n ]"
            return "[" + ",\n   ".join(json.dumps(r, separators=(",", ":")) for r in v) + "]"
        return json.dumps(v, separators=(", ", ": "))
    lines = ['{']
    keys = list(c)
    for i, key in enumerate(keys):
        lines.append(' %s: %s%s' % (json.dumps(key), val(c[key]), "," if i < len(keys) - 1 else ""))
    lines.append('}')
    text = "\n".join(lines) + "\n"
    assert json.loads(text) == c
    with open(path, "w", encoding="ascii", newline="\n") as fh:
        fh.write(text)


def poly_text(f):
    """x^3 + c2 x^2 + c1 x + c0 from f = [c0, c1, c2, 1] (labels)"""
    terms = ["x^%d" % (len(f) - 1)]
    for d in range(len(f) - 2, -1, -1):
        c = f[d]
        if c:
            terms.append(("" if c == 1 and d else str(c)) + ("x^%d" % d if d >= 2 else "x" if d == 1 else ""))
    return " + ".join(terms)


def primitive_element(F):
    for g in range(1, F.q):
        x, order = g, 1
        while x != 1:
            x = F.mul[x][g]
            order += 1
        if order == F.q - 1:
            return g
    raise ValueError("no primitive element")


def points(F):
    """a_0 = 0, a_i = e^(i-1), i = 1 .. q-1"""
    e = primitive_element(F)
    a, x = [0], 1
    for _ in range(F.q - 1):
        a.append(x)
        x = F.mul[x][e]
    return e, a


def cor519(F, a):
    """Corollary 5.1.9: the CA(2q^2 - q; 2, q^2 + 2q, q) of Theorem 5.1.8 with the Bush OA(q^2; 2, q+1, q)
    (the polynomials c0 + c1 X evaluated at the points a_0, ..., a_(q-1), and c1) as both ingredients.
    Rows: (c1, c0) for c1 = 1..q-1, c0 = 0..q-1 (labels; first part), the same (second part), then the
    q constant rows 0..q-1. Columns: j q + z (z, j < q), then q columns j, then q columns z."""
    q = F.q
    rho = [(c1, c0) for c1 in range(1, q) for c0 in range(q)]
    ev = np.array([[F.add[c0][F.mul[c1][z]] for z in a] for c1, c0 in rho], dtype=np.uint8)  # F(rho, a_z)
    c1s = np.array([c1 for c1, _ in rho], dtype=np.uint8)
    nr = len(rho)
    top = np.concatenate([np.tile(ev, (1, q)), np.repeat(c1s[:, None], q, axis=1), ev], axis=1)
    mid = np.concatenate([np.repeat(ev, q, axis=1), ev, np.repeat(c1s[:, None], q, axis=1)], axis=1)
    bot = np.concatenate([np.repeat(np.arange(q, dtype=np.uint8)[:, None], q * q, axis=1),
                          np.zeros((q, 2 * q), dtype=np.uint8)], axis=1)
    P = np.vstack([top, mid, bot])
    assert P.shape == (2 * nr + q, q * q + 2 * q)
    return P


def irreducible_bc(F):
    """the first (b, c) in itertools.product order, c != 0, with X^3 + bX + c without a root in F_q"""
    q = F.q
    for b, c in itertools.product(range(q), range(1, q)):
        if all(F.add[F.add[F.mul[F.mul[x][x]][x]][F.mul[b][x]]][c] for x in range(q)):
            return b, c
    raise ValueError("no irreducible X^3 + bX + c")


class Build:
    def __init__(self, thm, q, modulus=None, cubic=None):
        if thm not in THEOREMS:
            raise ValueError("THEOREM must be one of %s" % ", ".join(THEOREMS))
        if not prime_power(q):
            raise ValueError("q must be a prime power")
        if thm == "q" and q < 3:
            raise ValueError("q-plication needs q >= 3")
        if thm == "q2even" and q & (q - 1):
            raise ValueError("Corollary 5.2.12 is built here for q = 2^n only")
        self.thm, self.q = thm, q
        F = self.F = GF(q, modulus)
        self.e, self.a = points(F)
        self.k = k = q * q + q + 1
        cands = [list(cubic) + [1]] if cubic else self._cubics()
        for f in cands:
            L = powers(F, 3, f)
            self.f, self.L = f, L
            G1 = np.stack([L[j] for j in range(k)], axis=1)
            G2 = np.stack([L[(-j) % (q ** 3 - 1)] for j in range(k)], axis=1)
            self.G1, self.G2 = G1, G2
            self._ingredients()
            if thm != "q2q1" or len(self.Z) == q - 1:
                break
        else:
            raise ValueError("no primitive cubic gives |Z| = q - 1")

    def _cubics(self):
        """primitive cubics in order (for q2q1 several may be tried)"""
        F, q = self.F, self.q
        first = primitive(F, 3)
        yield first
        if self.thm != "q2q1":
            return
        for coeffs in itertools.product(range(q), repeat=3):
            f = list(coeffs) + [1]
            if coeffs[0] and f != first and is_primitive(F, f):
                yield f

    def _ingredients(self):
        F, q, a, k = self.F, self.q, self.a, self.k
        MUL = F.MUL
        self.P = cor519(F, a)[:, :k]
        thm = self.thm
        self.Z = []
        if thm in ("2", "q"):
            x = 2 if thm == "2" else q
            self.D = np.array([[F.mul[a[r]][a[c]] for c in range(x)] for r in range(q)], dtype=np.uint8)
            if thm == "2":
                self.C = np.zeros((0, 2), dtype=np.uint8)
            else:
                V = np.array([[F.mul[b][b] for b in a], a, [1] * q], dtype=np.uint8)   # c2 X^2 + c1 X + c0 at a
                B = span(F, V)
                U = np.array(list(itertools.product(range(q), repeat=3)), dtype=np.uint8)
                self.C = B[U[:, 0] != 0]                                                # drop degree <= 1
                self.last = [V]
            if thm == "2":
                self.last = []
            return
        # q^2-plications: D (x) D without the second zero row
        cols = [(j, z) for j in range(q) for z in range(q)]
        top = [[F.mul[a[r]][a[z]] for j, z in cols] for r in range(q)]
        bot = [[F.mul[a[r]][a[j]] for j, z in cols] for r in range(1, q)]
        D = np.array(top + bot, dtype=np.uint8)
        G1p = np.array([[1] * (q * q), [a[z] for j, z in cols], [a[j] for j, z in cols]], dtype=np.uint8)
        if thm == "q2even":
            b, c = irreducible_bc(F)
            self.bc = (b, c)
            G2p = np.array([[1] * (q * q),
                            [F.add[F.mul[a[z]][a[z]]][a[j]] for j, z in cols],
                            [F.add[F.add[F.mul[a[j]][a[j]]][F.mul[b][a[j]]]][F.mul[c][a[z]]] for j, z in cols]],
                           dtype=np.uint8)
        else:
            # the column of G1 proportional to (1, a_z, a_j), and the column of G2 with the same index
            inv = F.inv
            idx = {}
            for i in range(k):
                v = [int(t) for t in self.G1[:, i]]
                if v[0]:
                    s = inv[v[0]]
                    idx[tuple(F.mul[s][t] for t in v)] = i
            n = q ** 3 - 1
            G2p = np.stack([self.L[(-idx[(1, a[z], a[j])]) % n] for j, z in cols], axis=1).astype(np.uint8)
        U = np.array(list(itertools.product(range(q), repeat=3)), dtype=np.uint8)
        keep1 = (U[:, 1] != 0) & (U[:, 2] != 0)
        if thm == "q2":
            C = np.vstack([span(F, G1p)[keep1], span(F, G2p)[U.any(axis=1)]])
        else:
            if thm == "q2q1":
                self.Z = [c for c in range(q * q) if G2p[0, c] == 0]
                keepc = [c for c in range(q * q) if G2p[0, c] != 0]
                D, G1p, G2p = D[:, keepc], G1p[:, keepc], G2p[:, keepc]
                s = np.array([F.inv[int(t)] for t in G2p[0]], dtype=np.uint8)
                G2p = MUL[s[None, :], G2p]
            C = np.vstack([span(F, G1p)[keep1], span(F, G2p)[(U[:, 1] != 0) | (U[:, 2] != 0)]])
        self.D, self.C, self.last = D, C, [G1p, G2p]

    def rows(self, chunk=2048):
        """the array in row chunks (numpy uint8)"""
        F, k = self.F, self.k
        ADD = F.ADD
        D = self.D
        x = D.shape[1]
        bases = [span(F, self.G1), span(F, self.G2)] + [self.P] * (D.shape[0] - 2)
        for r, base in enumerate(bases):
            for s in range(0, base.shape[0], chunk):
                B = base[s:s + chunk]
                yield np.concatenate([ADD[B, D[r, l]] for l in range(x)], axis=1)
        for s in range(0, self.C.shape[0], chunk):
            yield np.repeat(self.C[s:s + chunk], k, axis=1)

    def certificate(self):
        F = self.F
        c = {"format": "construction-cert-1", "construction": "sm-xplication-1",
             "notes": ["Shokri and Moura, J. Combin. Des. 33 (2025) 156-171, thesis %s (%s-plication), q = %d."
                       % ({"2": "Theorem 5.2.7", "q": "Theorem 5.2.8", "q2": "Theorem 5.2.11",
                           "q2even": "Corollary 5.2.12", "q2q1": "Theorem 5.2.13"}[self.thm],
                          {"2": "2", "q": "q", "q2": "q^2", "q2even": "q^2", "q2q1": "(q^2-q+1)"}[self.thm], self.q),
                       "Written by tools/sm_xplication.py %s %d --certificate; the expected sha256 is that of "
                       "the script's own output." % (self.thm, self.q)],
             "t": 3, "v": self.q, "field": field_json(F), "cubic": [int(t) for t in self.f],
             "points": [int(t) for t in self.a],
             "dca": [[int(t) for t in r] for r in self.D],
             "last": [[[int(t) for t in r] for r in H] for H in self.last]}
        return c


def main():
    args = sys.argv[1:]
    modulus = cubic = cert = cols_out = None
    for opt in ("--certificate", "--modulus", "--cubic", "--columns"):
        if opt in args:
            i = args.index(opt)
            val = args[i + 1]
            del args[i:i + 2]
            if opt == "--certificate":
                cert = val
            elif opt == "--modulus":
                modulus = [int(t) for t in val.split(",")]
            elif opt == "--cubic":
                cubic = [int(t) for t in val.split(",")]
            else:
                cols_out = int(val)
    if len(args) != 2:
        sys.exit(__doc__)
    thm, q = args[0], int(args[1])
    b = Build(thm, q, modulus, cubic)
    Nf, kf = formula(thm, q)
    N2 = b.C.shape[0]
    N = 2 * q ** 3 + (b.D.shape[0] - 2) * b.P.shape[0] + N2
    kk = b.D.shape[1] * b.k
    sys.stderr.write("theorem %s (thesis %s), q = %d, %s, e = %d, primitive cubic %s (constant term first: %s)%s; "
                     "m = %d, x = %d, |C'| = %d; N = %d, k = %d (formula N = %d, k = %d)\n"
                     % (thm, THEOREMS[thm], q, b.F.describe(), b.e, poly_text(b.f), b.f,
                        "; b, c = %d, %d" % b.bc if thm == "q2even" else
                        "; Z = %s" % b.Z if thm == "q2q1" else "",
                        b.D.shape[0], b.D.shape[1], N2, N, kk, Nf, kf))
    if (N, kk) != (Nf, kf):
        sys.exit("the array does not have the size of the theorem")
    out = HashOut(sys.stdout.buffer)
    n_out = 0
    for R in b.rows():
        if cols_out is not None:
            R = R[:, :cols_out]
        write_rows(R, out)
        n_out += R.shape[0]
    assert n_out == N
    if cert:
        assert cols_out is None, "a certificate is for the whole array"
        c = b.certificate()
        c["expected"] = {"N": N, "k": kk, "array_sha256": out.h.hexdigest()}
        dump_certificate(c, cert)


if __name__ == "__main__":
    main()
