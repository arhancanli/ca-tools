# enumerate "patchable" columns: columns c (N old bits + 1 new-row bit) that extend the array when one free row y is added.
import sys, time
from pysat.solvers import Cadical153
f, cap, secs = sys.argv[1], int(sys.argv[2]), float(sys.argv[3])
A=[list(map(int,l.split())) for l in open(f) if l.strip()]
N=len(A); k=len(A[0]); full=(1<<N)-1
cols=[sum(A[r][j]<<r for r in range(N)) for j in range(k)]
C=list(range(1,N+2)); Y=list(range(N+2,N+2+k))
s=Cadical153(); lit=lambda var,val: var if val else -var
s.add_clause([-C[0]]); seen=set()
for i in range(k):
    for j in range(i+1,k):
        for a in (0,1):
            mi=cols[i] if a else ~cols[i]&full
            for b in (0,1):
                m=mi&(cols[j] if b else ~cols[j]&full)
                rows=[r for r in range(N) if m>>r&1]
                for v in (0,1):
                    base=[lit(C[r],v) for r in rows]
                    s.add_clause(base+[lit(Y[i],a)]); s.add_clause(base+[lit(Y[j],b)])
                    if (m,v) not in seen: seen.add((m,v)); s.add_clause(base+[lit(C[N],v)])
t0=time.time(); n=0
while n<cap and time.time()-t0<secs and s.solve():
    mod=s.get_model()
    c=sum(1<<r for r in range(N+1) if mod[r]>0)
    print(c,flush=True); n+=1
    s.add_clause([-x for x in mod[:N+1]])
print('pool',n,'secs %.0f'%(time.time()-t0),file=sys.stderr)
