# roux176.py CA_32_3_88_2.txt TOP ROUX: writes TOP = the 32 x 176 array [A A] and ROUX = the Roux doubling
# CA(42;3,176,2) = [A A; B ~B], B = CA(10;2,88,2) (one zero row and 88 distinct 5-subsets of the other 9 rows).
import sys
from itertools import combinations
A=[list(map(int,l.split())) for l in open(sys.argv[1]) if l.strip()]; k=len(A[0])
subs=list(combinations(range(9),5))[:k]
B=[[0]*k]+[[1 if r in s else 0 for s in subs] for r in range(9)]
top=[a+a for a in A]; R=top+[b+[1-x for x in b] for b in B]
w=lambda fn,M: open(fn,'w').write('\n'.join(' '.join(map(str,r)) for r in M)+'\n')
w(sys.argv[2],top); w(sys.argv[3],R)
