"""sms_theorem62.py - the strength-4 covering array of Shokri, Moura and Stevens,
arXiv:2510.13122v3, Theorem 6.2 (the array X of Table 5 there) with the ingredient size of
their Corollary 6.5 (Table 6), for an odd prime power q.

Theorem 6.2: if a CA(N; 3, (q^2+1)/2, q) exists, then X is a CA(3q^4 + N(q - 2); 4, q^2+1, q).
Rows of X, in blocks (half = (q^2+1)/2, column c = x + p*half):
  block 0:      A(G^{q+1}_{q^2+1})                          (all q^2+1 columns)
  block 1:      A(G^{2(q+1)}_half) | A(G^{2(q+1)}_half)
  block 2:      A(G^{4(q+1)}_half) | A(G^{4(q+1)}_half) + e_0
  block 2 + r:  R | R + e_r,  r = 1, ..., q - 2
with e_0, ..., e_{q-2} the nonzero elements of F_q (here e_r is the element numbered r + 1, so
e_0 = 1), over F_{q^4}. A(G) is the array of all F_q-linear combinations of the rows of G
(Construction 2.5), and + is the addition of F_q.

The ingredient R = CA(2q^3 - q; 3, half, q) has the size of their Theorem 3.4 and Remark 6.4 but is
built here differently: in the two blocks A(G^1), A(G^-1) over F_{q^3} of their Theorem 3.3
(a pair of orthogoval planes), keep the first `half` projective points whose column has nonzero
first coordinate in both blocks, scale each column within its block so that this coordinate is 1
(so c e_0 gives the constant row c in both blocks), and remove the q constant rows of the second
block. Scaling a column within a block keeps the rank of every set of its columns, and every 3 of
the points are independent in at least one of the two planes (orthogovality), so R is a strength-3
covering array; tools/construction_cert.py (construction sms65-1) checks this exactly. With
N = 2q^3 - q, X has 3q^4 + (q - 2)(2q^3 - q) rows: 294, 2610, 10598, 29826, 67782 for
q = 3, 5, 7, 9, 11.

F_q for q = p^m, the primitive polynomials, the order of the rows of A(G) and the output are as in
sms_theorem51.py (whose field code this script uses); for a prime q the output is the same as
before prime powers were added (2026-11-10).

Usage: python3 sms_theorem62.py q [--ingredient-only] [--ingredient-3.3] [--modulus c0,...]
           [--columns K] [--certificate CERT.json] > out.txt
--ingredient-3.3 uses the 2q^3 - 1 array of Theorem 3.3 instead (3q^4 + (q - 2)(2q^3 - 1) rows).
Writes canonical text (0-based, space-separated, one row per line) to stdout; --columns K writes
only the first K columns (for tests); the field and the primitive polynomials are printed to stderr.
--certificate writes the certificate of tools/construction_cert.py (construction sms65-1, with the
ingredient built from the orthogoval planes as here), with the N, k and sha256 of the text written
to stdout.
"""
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sms_theorem51 import (GF, HashOut, field_json, prime_power, primitive, powers, span,  # noqa: E402
                           write_certificate, write_rows)


def ingredient(F, small=True):
    """the strength-3 ingredient R on half columns, and the cubic primitive polynomial"""
    q = F.q
    half = (q * q + 1) // 2
    f3 = primitive(F, 3); L3 = powers(F, 3, f3); n3 = q ** 3 - 1
    if small:
        # CA(2q^3 - q; 3, half, q), the size of their Theorem 3.4 / Remark 6.4: keep the first `half`
        # projective points j (0 <= j < q^2+q+1) whose column in A(G^1) has nonzero first coordinate and
        # whose column in A(G^-1) has nonzero first coordinate; scale each column of each block so that
        # the first coordinate is 1. Then u = c e_0 gives the constant row c in both blocks, and the q
        # constant rows of the second block are removed.
        npts = q * q + q + 1
        cols = [j for j in range(npts) if L3[j % n3][0] and L3[(-j) % n3][0]][:half]
        assert len(cols) == half
        inv = np.array([0] + F.inv[1:], dtype=np.uint8)
        G1 = np.stack([F.MUL[L3[j % n3], inv[L3[j % n3][0]]] for j in cols], axis=1)
        Gm = np.stack([F.MUL[L3[(-j) % n3], inv[L3[(-j) % n3][0]]] for j in cols], axis=1)
        A1, A2 = span(F, G1), span(F, Gm)
        const2 = np.where((A2 == A2[:, :1]).all(axis=1))[0]; assert len(const2) == q
        R = np.vstack([A1, np.delete(A2, const2, axis=0)])
        assert R.shape[0] == 2 * q ** 3 - q
    else:
        G1 = np.stack([L3[j % n3] for j in range(half)], axis=1)
        Gm = np.stack([L3[(-j) % n3] for j in range(half)], axis=1)
        R = np.vstack([span(F, G1), span(F, Gm)])
        z = np.where(~R.any(axis=1))[0]; assert len(z) == 2
        R = np.delete(R, z[1:], axis=0)
    return R, f3, (cols if small else None)


def main():
    args = sys.argv[1:]
    modulus = cols_out = cert = None
    if "--certificate" in args:
        i = args.index("--certificate"); cert = args[i + 1]; del args[i:i + 2]
    if "--modulus" in args:
        i = args.index("--modulus"); modulus = [int(x) for x in args[i + 1].split(",")]; del args[i:i + 2]
    if "--columns" in args:
        i = args.index("--columns"); cols_out = int(args[i + 1]); del args[i:i + 2]
    q = int(args[0]); assert q % 2 == 1 and prime_power(q), "q must be an odd prime power"
    F = GF(q, modulus)
    only_R = "--ingredient-only" in args
    small = "--ingredient-3.3" not in args   # default: the 2q^3 - q ingredient (Corollary 6.5 size)
    half = (q * q + 1) // 2
    R, f3, rcols = ingredient(F, small)
    out = HashOut(sys.stdout.buffer)
    if only_R:
        sys.stderr.write("R: q=%d %s f3 low-first %s N=%d k=%d\n" % (q, F.describe(), f3, R.shape[0], R.shape[1]))
        write_rows(R if cols_out is None else R[:, :cols_out], out); return
    f4 = primitive(F, 4); L4 = powers(F, 4, f4); n4 = q ** 4 - 1
    B0 = span(F, np.stack([L4[((q + 1) * c) % n4] for c in range(q * q + 1)], axis=1))
    H2 = span(F, np.stack([L4[(2 * (q + 1) * i) % n4] for i in range(half)], axis=1))
    H4 = span(F, np.stack([L4[(4 * (q + 1) * i) % n4] for i in range(half)], axis=1))
    blocks = [B0, np.hstack([H2, H2]), np.hstack([H4, F.ADD[H4, 1]])]
    for r in range(1, q - 1):
        blocks.append(np.hstack([R, F.ADD[R, r + 1]]))
    X = np.vstack(blocks)
    assert X.shape == (3 * q ** 4 + (q - 2) * R.shape[0], q * q + 1)
    sys.stderr.write("q=%d %s f4 low-first %s f3 low-first %s N=%d k=%d (R has %d rows)\n"
                     % (q, F.describe(), f4, f3, X.shape[0], X.shape[1], R.shape[0]))
    write_rows(X if cols_out is None else X[:, :cols_out], out)
    if cert:
        assert cols_out is None and small, "a certificate is for the whole array with the 2q^3 - q ingredient"
        write_certificate(cert, {"format": "construction-cert-1", "construction": "sms65-1", "t": 4, "v": q,
                                 "field": field_json(F), "quartic": [int(x) for x in f4],
                                 "ingredient": {"orthogoval": {"cubic": [int(x) for x in f3],
                                                               "points": [int(j) for j in rcols]}}},
                          X.shape[0], X.shape[1], out.h.hexdigest())


if __name__ == "__main__":
    main()
