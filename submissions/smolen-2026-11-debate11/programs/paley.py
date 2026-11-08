#!/usr/bin/env python3
"""Paley-type binary arrays (own code, after Paley 1933 / Colbourn 2015 doubling).
usage: paley.py q [double] [diag] > file
q prime or p^2 (p prime). Rows x in GF(q); columns c in GF(q): entry (1+chi(x-c))/2, diagonal = diag (0/1).
With 'double': rows [0 | M] and [1 | 1-M] (indicator column first): 2q rows, q+1 columns.
"""
import sys
q=int(sys.argv[1]); dbl='double' in sys.argv[2:]; diag=1 if 'diag1' in sys.argv[2:] else 0
def isprime(n):
    return n>1 and all(n%d for d in range(2,int(n**0.5)+1))
if isprime(q):
    els=list(range(q)); sub=lambda a,b:(a-b)%q
    sq=set((x*x)%q for x in range(1,q))
    chi=lambda a: 0 if a==0 else (1 if a in sq else -1)
else:
    p=int(round(q**0.5)); assert p*p==q and isprime(p)
    # GF(p^2) = F_p[i]/(i^2 - n) with n a non-residue
    nres=next(n for n in range(2,p) if pow(n,(p-1)//2,p)==p-1) if p>2 else None
    els=[(a,b) for a in range(p) for b in range(p)]
    sub=lambda u,v:((u[0]-v[0])%p,(u[1]-v[1])%p)
    def mul(u,v): return ((u[0]*v[0]+nres*u[1]*v[1])%p,(u[0]*v[1]+u[1]*v[0])%p)
    sq=set(mul(e,e) for e in els if e!=(0,0))
    chi=lambda a: 0 if a==(0,0) else (1 if a in sq else -1)
M=[[diag if x==c else (1+chi(sub(x,c)))//2 for c in els] for x in els]
rows=[]
if dbl:
    for r in M: rows.append([0]+r)
    for r in M: rows.append([1]+[1-v for v in r])
else: rows=M
for r in rows: print(' '.join(map(str,r)))
