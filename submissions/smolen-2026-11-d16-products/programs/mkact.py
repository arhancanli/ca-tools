#!/usr/bin/env python3
"""mkact.py (debate16 D, own code; group constructors reused from debate15/A/mkgrp.py, also own project code).
Spec for grpm.c with a NON-TRANSITIVE column action: columns = disjoint union of coset spaces G/K_i.
usage: mkact.py GROUP COLS WORDS [-o out] [-l]
 COLS  like "1,4.2,G" : each item a subgroup K given as order.index (index into the sorted list of ALL subgroups of
       that order; '1' trivial = regular block of |G| columns; 'G' = one fixed column). Left action a.(gK) = agK.
 WORDS like "6x1,8.0,G,G": stabiliser H of each generator word (rows = |G|/|H|), word constant on H-orbits of columns.
 -l lists subgroups with generators, normality and quotient type.
"""
import sys, os
src=open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'mkgrp_lib.py')).read()
exec(src)
_parse0=parse
def parse(name):
    if name=='A5': return symmetric(5,True)
    if name=='S5': return symmetric(5)
    return _parse0(name)
def main():
    args=sys.argv[1:]; listonly='-l' in args; out=None
    if '-o' in args: out=args[args.index('-o')+1]
    pos=[a for i,a in enumerate(args) if not a.startswith('-') and (i==0 or args[i-1]!='-o')]
    els,mul,e=parse(pos[0]); n=len(els); idx={x:i for i,x in enumerate(els)}
    M=[[idx[mul(els[a],els[b])] for b in range(n)] for a in range(n)]; ident=idx[e]
    inv=[0]*n
    for a in range(n):
        for b in range(n):
            if M[a][b]==ident: inv[a]=b
    def closure(gens):
        S={ident}; fr=[ident]
        while fr:
            x=fr.pop()
            for g in gens:
                y=M[x][g]
                if y not in S: S.add(y); fr.append(y)
        return frozenset(S)
    subs={frozenset([ident])}
    cyc=[closure([a]) for a in range(n)]
    subs|=set(cyc)
    grow=True
    while grow:   # all subgroups: join with cyclic ones until stable
        grow=False
        for H in list(subs):
            for a in range(n):
                if a in H: continue
                J=closure(list(H)+[a])
                if J not in subs: subs.add(J); grow=True
    byord={}
    for H in sorted(subs,key=lambda H:(len(H),sorted(H))): byord.setdefault(len(H),[]).append(H)
    def order(a):
        x=a; o=1
        while x!=ident: x=M[x][a]; o+=1
        return o
    def normal(H): return all(frozenset(M[M[g][h]][inv[g]] for h in H)==H for g in range(n))
    def qtype(H):
        if not normal(H): return 'not normal'
        # exponent profile of quotient
        cos={}
        for a in range(n): cos[a]=min(M[a][h] for h in H)
        def qord(a):
            x=a;o=1
            while cos[x]!=cos[ident]: x=M[x][a]; o+=1
            return o
        prof=sorted(qord(a) for a in set(cos.values()))
        return 'quotient element orders '+','.join(f"{o}^{prof.count(o)}" for o in sorted(set(prof)))
    if listonly:
        print('group',pos[0],'order',n,'element orders',sorted(order(a) for a in range(n)))
        for h in sorted(byord):
            for i,H in enumerate(byord[h]): print(f" {h}.{i}: {sorted(H)}  {qtype(H)}")
        return
    def getsub(spec):
        if spec=='G': return frozenset(range(n))
        if '.' in spec: h,ci=spec.split('.'); h=int(h); ci=int(ci)
        else: h=int(spec); ci=0
        return byord[h][ci]
    def expand(s):
        r=[]
        for item in s.split(','):
            cnt=1; sp=item
            if 'x' in item: c,sp=item.split('x'); cnt=int(c)
            r+= [sp]*cnt
        return r
    # columns
    colid={}; k=0; act=[[] for _ in range(n)]
    cols=[]  # (block index, coset frozenset)
    for bi,sp in enumerate(expand(pos[1])):
        K=getsub(sp); seen=set()
        for g in range(n):
            C=frozenset(M[g][x] for x in K)
            if C in seen: continue
            seen.add(C); colid[(bi,C)]=k; cols.append((bi,C)); k+=1
    for a in range(n):
        act[a]=[colid[(bi,frozenset(M[a][x] for x in C))] for (bi,C) in cols]
    words=expand(pos[2]); outl=[f"{k} {n}"]
    for a in range(n): outl.append(' '.join(map(str,act[a])))
    outl.append(str(len(words))); N=0
    for sp in words:
        H=getsub(sp); reps=[]; cov=set()
        for a in range(n):
            if a in cov: continue
            reps.append(a); cov|={M[a][h] for h in H}
        blocks=[]; cv=set()
        for c in range(k):
            if c in cv: continue
            B=sorted({act[h][c] for h in H}); blocks.append(B); cv|=set(B)
        N+=len(reps)
        outl.append(f"{len(reps)} "+' '.join(map(str,reps)))
        outl.append(f"{len(blocks)} "+' '.join(f"{len(B)} "+' '.join(map(str,B)) for B in blocks))
    txt='\n'.join(outl)+'\n'
    if out: open(out,'w').write(txt)
    else: sys.stdout.write(txt)
    sys.stderr.write(f"group {pos[0]} order {n} k={k} words={len(words)} N={N}\n")
main()
