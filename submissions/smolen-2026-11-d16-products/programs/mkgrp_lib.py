#!/usr/bin/env python3
"""mkgrp.py (debate15 A, own code). Build a spec file for grpm.c:
group G of order n given by name, left regular action on n columns (+ optional fixed column -> k = n+1),
and a word list: each word has a stabilizer subgroup H (given by its order and an index among conjugacy classes
of subgroups of that order; 'G' = whole group = constant-on-blocks row). Rows of a word = |G|/|H|.
usage: mkgrp.py GROUP WORDSPEC [-f] [-o out] [-l]   WORDSPEC like "4x1,2,3,G" ; -l lists subgroup classes.
Groups: Zn ; Z2^n ; ab:a,b,c (direct product of cyclics) ; D<n> (order 2n) ; Dic<n> (order 4n) ; SD:m,n,r (Z_m x| Z_n, generator acts by r) ;
 F20 ; SL23 ; S4 ; A4 ; Q8 ; X*Y direct product of any two.
"""
import sys, itertools
def cyclic(n):
    return list(range(n)), (lambda a,b: (a+b)%n), 0
def product(G1,G2):
    e1,m1,i1=G1; e2,m2,i2=G2
    els=[(a,b) for a in e1 for b in e2]
    return els,(lambda x,y:(m1(x[0],y[0]),m2(x[1],y[1]))),(i1,i2)
def semidirect(m,n,r):
    assert pow(r,n,m)==1
    els=[(i,j) for i in range(m) for j in range(n)]
    def mul(x,y):
        i,j=x; k,l=y
        return ((i+pow(r,j,m)*k)%m,(j+l)%n)
    return els,mul,(0,0)
def dicyclic(n):  # order 4n: a^i x^j, a^(2n)=1, x^2=a^n, x a x^-1 = a^-1
    els=[(i,j) for i in range(2*n) for j in range(2)]
    def mul(x,y):
        i,j=x; k,l=y
        if j==0: return ((i+k)%(2*n), l)
        i2=(i-k)%(2*n); j2=1+l
        if j2==2: return ((i2+n)%(2*n),0)
        return (i2,1)
    return els,mul,(0,0)
def matgroup(mats,p):
    els=[tuple(m) for m in mats]
    def mul(x,y):
        a,b,c,d=x; e,f,g,h=y
        return ((a*e+b*g)%p,(a*f+b*h)%p,(c*e+d*g)%p,(c*f+d*h)%p)
    return els,mul,(1,0,0,1)
def sl23():
    mats=[(a,b,c,d) for a in range(3) for b in range(3) for c in range(3) for d in range(3) if (a*d-b*c)%3==1]
    return matgroup(mats,3)
def symmetric(n, even=False):
    els=[p for p in itertools.permutations(range(n))]
    if even:
        def sgn(p):
            s=1
            for i in range(len(p)):
                for j in range(i+1,len(p)):
                    if p[i]>p[j]: s=-s
            return s
        els=[p for p in els if sgn(p)==1]
    return els,(lambda x,y: tuple(x[y[i]] for i in range(n))),tuple(range(n))
def quat():  # Q8 = Dic2
    return dicyclic(2)
def parse(name):
    if '*' in name:
        a,b=name.split('*',1); return product(parse(a),parse(b))
    if name.startswith('Z2^'): 
        n=int(name[3:]); G=cyclic(2)
        for _ in range(n-1): G=product(G,cyclic(2))
        return G
    if name.startswith('Z'): return cyclic(int(name[1:]))
    if name.startswith('ab:'):
        parts=[int(x) for x in name[3:].split(',')]; G=cyclic(parts[0])
        for p in parts[1:]: G=product(G,cyclic(p))
        return G
    if name.startswith('Dic'): return dicyclic(int(name[3:]))
    if name.startswith('D'): n=int(name[1:]); return semidirect(n,2,n-1)
    if name.startswith('SD:'): m,n,r=[int(x) for x in name[3:].split(',')]; return semidirect(m,n,r)
    if name=='F20': return semidirect(5,4,2)
    if name=='SL23': return sl23()
    if name=='S4': return symmetric(4)
    if name=='A4': return symmetric(4,True)
    if name=='Q8': return quat()
    raise SystemExit('unknown group '+name)
