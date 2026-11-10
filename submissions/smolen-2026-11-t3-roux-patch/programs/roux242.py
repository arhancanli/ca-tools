# CA(43;3,242,2) by Roux doubling: [A A; B ~B], A = own CA(33;3,121,2) (Power CT, table row S7),
# B = CA(10;2,121,2): one zero row + 121 distinct 5-subsets of 9 rows (Kleitman-Spencer / Katona).
import sys
from itertools import combinations
A=[list(map(int,l.split())) for l in open(sys.argv[1]) if l.strip()]
k=len(A[0]); subs=list(combinations(range(9),5))[:k]
B=[[0]*k]+[[1 if r in s else 0 for s in subs] for r in range(9)]
R=[a+a for a in A]+[b+[1-x for x in b] for b in B]
open(sys.argv[2],'w').write('\n'.join(' '.join(map(str,r)) for r in R)+'\n')
