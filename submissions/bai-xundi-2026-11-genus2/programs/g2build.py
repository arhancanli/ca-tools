"""Build the genus-2 two-block covering array of a certificate (paper C, Theorem 5.2),
optionally fused j times (Lemma 2.4 = CKRS 2010 Lemma 3.1). Prime q only.
Rows: every f in C1 u C2, where V = L(a*Inf+ + b*Inf-) has the basis V_basis in the
monomials x^i y^j and C_i = {f in V : f(Q_i) = 0}; entries f(P) at the columns of the certificate.
usage: g2build.py cert.json j out.txt"""
import json, sys, itertools
import numpy as np
c = json.load(open(sys.argv[1])); j = int(sys.argv[2]); out = sys.argv[3]
q = c['q']; t = c['t']; f = c['f']; mons = [tuple(m) for m in c['mons']]
Vb = np.array(c['V_basis'], dtype=np.int64)            # (t+2) x len(mons)
r = int(c['F2'].split('-')[1].rstrip(')'))               # F_q^2 = F_q[z]/(z^2 - r)
assert all(q % d for d in range(2, int(q**.5)+1)), 'prime q only'
def mul(u, v): return ((u[0]*v[0] + r*u[1]*v[1]) % q, (u[0]*v[1] + u[1]*v[0]) % q)
def pw(u, e):
    o = (1, 0)
    for _ in range(e): o = mul(o, u)
    return o
# sqrt series of f at infinity (for the columns Inf+ and Inf-)
s = next(y for y in range(1, q) if y*y % q == f[6]); L = len(mons) + 12
g = [f[6-i] if i <= 6 else 0 for i in range(L)]; cs = [s] + [0]*(L-1)
for k in range(1, L): cs[k] = (g[k] - sum(cs[i]*cs[k-i] for i in range(1, k))) * pow(2*s, q-2, q) % q
def infcoef(m, e, sg):
    i, jj = m
    if jj == 0: return 1 if e == i else 0
    k = 3 + i - e; return sg*cs[k] % q if 0 <= k < L else 0
cols = c['columns'] if isinstance(c['columns'], list) else json.loads(c['columns'].replace("'", '"'))
E = []
for col in cols:
    if col[0] == 'A': _, x, y = col; E.append([pow(x, i, q) * (y if jj else 1) % q for (i, jj) in mons])
    elif col[0] == 'I+': E.append([infcoef(m, c['a'], 1) for m in mons])
    else: E.append([infcoef(m, c['b'], -1) for m in mons])
E = (np.array(E, dtype=np.int64) @ Vb.T) % q              # n x (t+2): column functionals on V
def nullspace(M):
    M = [list(map(int, row)) for row in M]; ncol = len(M[0]); piv = []; rr = 0
    for cc in range(ncol):
        p = next((i for i in range(rr, len(M)) if M[i][cc] % q), None)
        if p is None: continue
        M[rr], M[p] = M[p], M[rr]; iv = pow(M[rr][cc], q-2, q)
        M[rr] = [x*iv % q for x in M[rr]]
        for i in range(len(M)):
            if i != rr and M[i][cc]: M[i] = [(a - M[i][cc]*b) % q for a, b in zip(M[i], M[rr])]
        piv.append(cc); rr += 1
    free = [cc for cc in range(ncol) if cc not in piv]; B = []
    for fc in free:
        v = [0]*ncol; v[fc] = 1
        for i, pc in enumerate(piv): v[pc] = -M[i][fc] % q
        B.append(v)
    return np.array(B, dtype=np.int64)
blocks = []
for Q in (c['Q1'], c['Q2']):
    x0, y0 = tuple(Q[0]), tuple(Q[1]); r1 = []; r2 = []
    for (i, jj) in mons:
        e = pw(x0, i)
        if jj: e = mul(e, y0)
        r1.append(e[0]); r2.append(e[1])
    Phi = (np.array([r1, r2], dtype=np.int64) @ Vb.T) % q    # f(Q) = 0 in F_q^2: two F_q conditions
    K = nullspace(Phi); assert K.shape[0] == t, K.shape       # dim C_i = t
    coef = np.array(list(itertools.product(range(q), repeat=t)), dtype=np.int64)
    blocks.append((coef @ K) % q)                           # all q^t elements of C_i in V-coordinates
allf = np.unique(np.vstack(blocks), axis=0)                 # C1 u C2 (the intersection once)
A = (allf @ E.T) % q
expect = 2*q**t - q**(t-2)
assert len(A) == c['N'] == expect, (len(A), c['N'], expect)
# rows sorted lexicographically by f; the zero function (all-zero row) comes first
v = q
for step in range(j):                                       # Lemma 2.4: CA(N;t,k,v) -> CA(N-2;t,k,v-1)
    inf = v - 1
    z = np.flatnonzero((A == 0).all(axis=1)) if step == 0 else np.flatnonzero((A == inf).all(axis=1))
    i1 = int(z[0]) if len(z) else 0
    rho1 = A[i1].copy()
    # permute symbols per column so that rho1 = (inf,...,inf): swap rho1(c) and inf in column c
    B = A.copy()
    for cc in range(A.shape[1]):
        a = rho1[cc]
        if a != inf:
            m1 = A[:, cc] == a; m2 = A[:, cc] == inf; B[m1, cc] = inf; B[m2, cc] = a
    i2 = 1 if i1 == 0 else 0
    rho2 = B[i2].copy()
    keep = np.ones(len(B), bool); keep[[i1, i2]] = False; B = B[keep]
    for cc in range(B.shape[1]):
        m = B[:, cc] == inf; B[m, cc] = rho2[cc] if rho2[cc] != inf else 0
    A = B; v -= 1
assert A.max() < v
np.savetxt(out, A, fmt='%d', delimiter=' ')
print('CA(%d;%d,%d,%d)' % (len(A), t, A.shape[1], v), 'distinct rows', len(np.unique(A, axis=0)))
