#!/usr/bin/env python3
"""mkspec.py N c1,c2,... > spec : cyclic row group with the given cycles (rest fixed rows), plus normaliser
generators: rotation of each cycle, swap of adjacent equal cycles, swap of adjacent fixed rows, multipliers."""
import sys
from math import gcd
N = int(sys.argv[1]); cyc = [int(x) for x in sys.argv[2].split(',')]
starts = []; p = 0
for c in cyc:
    starts.append(p); p += c
nf = N - p
assert nf >= 0
L = 1
for c in cyc: L = L * c // gcd(L, c)
def ident(): return list(range(N))
out = [str(N)]
g = ident()
for s, c in zip(starts, cyc):
    for i in range(c): g[s + i] = s + (i + 1) % c
out.append('g ' + ' '.join(map(str, g)))
for s, c in zip(starts, cyc):
    h = ident()
    for i in range(c): h[s + i] = s + (i + 1) % c
    out.append('h ' + ' '.join(map(str, h)))
for a in range(len(cyc) - 1):
    if cyc[a] == cyc[a + 1]:
        h = ident(); c = cyc[a]
        for i in range(c): h[starts[a] + i] = starts[a + 1] + i; h[starts[a + 1] + i] = starts[a] + i
        out.append('h ' + ' '.join(map(str, h)))
for i in range(p, N - 1):
    h = ident(); h[i] = i + 1; h[i + 1] = i
    out.append('h ' + ' '.join(map(str, h)))
for j in range(2, L):
    if gcd(j, L) == 1:
        h = ident()
        for s, c in zip(starts, cyc):
            for i in range(c): h[s + i] = s + (j * i) % c
        out.append('h ' + ' '.join(map(str, h)))
print('\n'.join(out))
