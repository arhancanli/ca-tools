"""sms_theorem51.py - build the strength-4 covering array of Shokri, Moura and Stevens,
arXiv:2510.13122v3, Theorem 5.1, for an odd prime power q.
Used for the table entries CA(43921; 4, 61, 11) and CA(85681; 4, 85, 13) (table/VERIFICATION_LOG.md).

Theorem 5.1: alpha primitive in F_{q^4}; A_l = A([G^{l(q+1)}_{q^2+1}]_p) for l = 1, 2, 4,
where (Construction 2.5) G^m_c has columns L(alpha^(m i)), 0 <= i < c, L(x) the coordinate
vector of x in the basis 1, alpha, alpha^2, alpha^3, and [.]_p keeps the columns
i + p_i (q^2+1)/2, 0 <= i < (q^2+1)/2, for a choice p in {0,1}^((q^2+1)/2);
A(G) is the q^4 x c array of all F_q-linear combinations of the rows of G.
The vertical concatenation of A_1, A_2, A_4 with two of the three all-zero rows removed is
claimed to be a CA(3q^4 - 2; 4, (q^2+1)/2, q).

F_q for q = p^m: the element with base-p digits d_0, d_1, ... (least significant first) is the
polynomial d_0 + d_1 y + ... modulo a monic irreducible polynomial of degree m over F_p (the
convention of tools/construction_cert.py). The default modulus is the first monic irreducible
one in the order of itertools.product(range(p), repeat=m) over its lower coefficients, constant
term first (x^2 + 1 for q = 9, x^2 + x + 1 for q = 25); --modulus c0,c1,...,c_{m-1} chooses another.
For a prime q this is arithmetic mod q, and the output is the same as before prime powers were
added (2026-11-10).

The rows of A(G) are in the order of u in itertools.product(range(q), repeat=4) (u_0 most
significant), row = sum_i u_i G[i]. The primitive polynomial is the first one found in the same
order over its lower coefficients (constant term first, nonzero).

Usage: python3 tools/sms_theorem51.py q [p-bits as a 0/1 string, default all zeros]
           [--modulus c0,...] [--columns K] [--certificate CERT.json] > out.txt
Writes the array as canonical text (0-based, space-separated, one row per line) to stdout;
--columns K writes only the first K columns (for tests); the field, the primitive polynomial and
p are printed to stderr. tools/construction_cert.py (construction sms51-1) checks the theorem's
hypotheses and rebuilds the same array; --certificate writes its certificate, with the N, k and
sha256 of the text written to stdout.
"""
import hashlib, itertools, json, sys
import numpy as np


def is_prime(n):
    return n > 1 and all(n % d for d in range(2, int(n ** 0.5) + 1))


def prime_power(q):
    for p in range(2, q + 1):
        if q % p == 0:
            m, r = 0, q
            while r % p == 0:
                r //= p; m += 1
            return (p, m) if r == 1 and is_prime(p) else None
    return None


class GF:
    """F_q as the integers 0..q-1 with addition and multiplication tables"""
    def __init__(self, q, modulus=None):
        pm = prime_power(q)
        if pm is None:
            raise ValueError("q = %d is not a prime power" % q)
        self.p, self.m, self.q = pm[0], pm[1], q
        p, m = self.p, self.m
        if m == 1:
            self.modulus = [0, 1]
            self.add = [[(a + b) % p for b in range(q)] for a in range(q)]
            self.mul = [[(a * b) % p for b in range(q)] for a in range(q)]
        else:
            cands = [list(modulus)] if modulus else [list(c) for c in itertools.product(range(p), repeat=m)]
            for c in cands:
                self.modulus = c + [1]
                self._tables()
                if all(0 not in self.mul[a][1:] for a in range(1, q)):
                    break
            else:
                raise ValueError("no irreducible modulus")
            if 0 in [x for a in range(1, q) for x in self.mul[a][1:]]:
                raise ValueError("the modulus %r is reducible" % self.modulus)
        self.ADD = np.array(self.add, dtype=np.uint8)
        self.MUL = np.array(self.mul, dtype=np.uint8)
        self.neg = [self.add[a].index(0) for a in range(q)]
        self.inv = [None] + [self.mul[a].index(1) for a in range(1, q)]

    def _tables(self):
        p, m, q = self.p, self.m, self.q
        dig = [[(i // p ** j) % p for j in range(m)] for i in range(q)]
        und = lambda d: sum(c * p ** j for j, c in enumerate(d))
        self.add = [[und([(x + y) % p for x, y in zip(dig[a], dig[b])]) for b in range(q)] for a in range(q)]
        mul = [[0] * q for _ in range(q)]
        for a in range(q):
            for b in range(q):
                r = [0] * (2 * m - 1)
                for i, x in enumerate(dig[a]):
                    for j, y in enumerate(dig[b]):
                        r[i + j] = (r[i + j] + x * y) % p
                for d in range(2 * m - 2, m - 1, -1):
                    c = r[d]
                    if c:
                        r[d] = 0
                        for k in range(m):
                            r[d - m + k] = (r[d - m + k] - c * self.modulus[k]) % p
                mul[a][b] = und(r[:m])
        self.mul = mul

    def describe(self):
        return "GF(%d)" % self.q if self.m == 1 else "GF(%d) = GF(%d)[y]/(modulus %s, constant first)" % (
            self.q, self.p, self.modulus)


def mulmod(F, a, b, f, m):
    """a, b: coefficient lists over F (low degree first, length m); f: monic of degree m (length m+1)"""
    r = [0] * (2 * m - 1)
    for i, x in enumerate(a):
        if x:
            for j, y in enumerate(b):
                if y:
                    r[i + j] = F.add[r[i + j]][F.mul[x][y]]
    for d in range(2 * m - 2, m - 1, -1):
        c = r[d]
        if c:
            r[d] = 0
            for k in range(m):
                r[d - m + k] = F.add[r[d - m + k]][F.neg[F.mul[c][f[k]]]]
    return r[:m]


def primitive(F, m):
    q = F.q
    order = q ** m - 1
    primes = [p for p in range(2, order + 1) if order % p == 0 and is_prime(p)]
    one = [1] + [0] * (m - 1); x = [0, 1] + [0] * (m - 2)
    for coeffs in itertools.product(range(q), repeat=m):   # f = x^m + c_{m-1} x^{m-1} + ... + c_0
        if coeffs[0] == 0:
            continue
        f = list(coeffs) + [1]

        def pw(e):
            res, base = one[:], x[:]
            while e:
                if e & 1: res = mulmod(F, res, base, f, m)
                base = mulmod(F, base, base, f, m); e >>= 1
            return res
        if pw(order) == one and all(pw(order // p) != one for p in primes):
            return f
    raise ValueError("no primitive polynomial found")


def powers(F, m, f):
    """L[j] = coordinates of alpha^j, j = 0 .. q^m - 2"""
    n = F.q ** m - 1
    L = np.zeros((n, m), dtype=np.uint8); cur = [1] + [0] * (m - 1); x = [0, 1] + [0] * (m - 2)
    for j in range(n):
        L[j] = cur; cur = mulmod(F, cur, x, f, m)
    return L


def span(F, G):
    """A(G): all F-linear combinations of the rows of G, u in itertools.product order"""
    m, k = G.shape
    U = np.array(list(itertools.product(range(F.q), repeat=m)), dtype=np.uint8)
    A = F.MUL[U[:, 0][:, None], G[0][None, :]]
    for i in range(1, m):
        A = F.ADD[A, F.MUL[U[:, i][:, None], G[i][None, :]]]
    return A


class HashOut:
    """a binary stream that also hashes and counts what it writes"""
    def __init__(self, out):
        self.out, self.h = out, hashlib.sha256()

    def write(self, b):
        self.h.update(b)
        self.out.write(b)


def field_json(F):
    d = {"q": F.q, "p": F.p, "m": F.m}
    if F.m > 1:
        d["modulus"] = F.modulus
    return d


def write_certificate(path, cert, N, k, sha):
    cert["expected"] = {"N": N, "k": k, "array_sha256": sha}
    with open(path, "w", encoding="ascii", newline="\n") as f:
        json.dump(cert, f, indent=1)
        f.write("\n")


def write_rows(M, out, chunk=20000):
    """canonical text: entries separated by single spaces, a newline after every row (values < 100)"""
    assert int(M.max(initial=0)) < 100
    k = M.shape[1]
    for s in range(0, M.shape[0], chunk):
        B = M[s:s + chunk]
        r = B.shape[0]
        C = np.empty((r, k, 3), dtype=np.uint8)
        C[:, :, 0] = np.where(B >= 10, 48 + B // 10, 0)
        C[:, :, 1] = 48 + B % 10
        C[:, :, 2] = 32
        C[:, -1, 2] = 10
        flat = C.reshape(-1)
        out.write(flat[flat != 0].tobytes())


def main():
    args = sys.argv[1:]
    modulus = cols_out = cert = None
    if "--certificate" in args:
        i = args.index("--certificate"); cert = args[i + 1]; del args[i:i + 2]
    if "--modulus" in args:
        i = args.index("--modulus"); modulus = [int(x) for x in args[i + 1].split(",")]; del args[i:i + 2]
    if "--columns" in args:
        i = args.index("--columns"); cols_out = int(args[i + 1]); del args[i:i + 2]
    q = int(args[0])
    assert q % 2 == 1 and prime_power(q), "q must be an odd prime power"
    F = GF(q, modulus)
    half = (q * q + 1) // 2
    p = [int(c) for c in args[1]] if len(args) > 1 else [0] * half
    assert len(p) == half and set(p) <= {0, 1}
    f = primitive(F, 4)
    # powers of alpha as coordinate vectors L(alpha^j), j = 0 .. q^4 - 2
    n = q ** 4 - 1
    L = powers(F, 4, f)
    cols = [i + p[i] * half for i in range(half)]
    blocks = []
    for l in (1, 2, 4):
        G = np.stack([L[(l * (q + 1) * i) % n] for i in cols], axis=1)          # 4 x half
        blocks.append(span(F, G))                                                # q^4 x half
    M = np.vstack(blocks)
    zero = np.where(~M.any(axis=1))[0]
    assert len(zero) == 3, zero
    M = np.delete(M, zero[1:], axis=0)                                           # keep one all-zero row
    sys.stderr.write("q=%d %s primitive polynomial x^4 + %s (low degree first: %s); p=%s; N=%d k=%d\n"
                     % (q, F.describe(), f[3::-1], f, "".join(map(str, p)), M.shape[0], M.shape[1]))
    if cols_out is not None:
        M = M[:, :cols_out]
    out = HashOut(sys.stdout.buffer)
    write_rows(M, out)
    if cert:
        assert cols_out is None, "a certificate is for the whole array"
        write_certificate(cert, {"format": "construction-cert-1", "construction": "sms51-1", "t": 4, "v": q,
                                 "field": field_json(F), "quartic": [int(x) for x in f],
                                 "p": "".join(map(str, p))}, M.shape[0], M.shape[1], out.h.hexdigest())


if __name__ == "__main__":
    main()
