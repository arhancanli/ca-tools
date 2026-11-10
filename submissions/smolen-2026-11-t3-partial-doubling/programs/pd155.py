# pd155.py CA_33_3_121_2.txt OUT: exact partial doubling CA(41;3,155,2).
# Columns 0..120 are the base; columns 121..154 are second copies ("twins") of base columns 0..33.
# Rows 0..32: base rows (a twin repeats its column). Rows 33..40 (8 helper rows): a strength-2 family on 8 rows,
# one zero row plus a 4-subset of the other 7 rows. Twinned column i gets family member i+1 and its twin the
# complement; every other column gets family member 0. Needs 34 + 1 <= C(7,4) = 35.
import sys
from itertools import combinations
A=[list(map(int,l.split())) for l in open(sys.argv[1]) if l.strip()]; k=len(A[0])
fam=[[0]+[1 if r in s else 0 for r in range(7)] for s in combinations(range(7),4)]
p=fam[0]; F=fam[1:]
cols=[(i, F[i] if i<34 else p) for i in range(k)]+[(i,[1-x for x in F[i]]) for i in range(34)]
R=[[A[r][c[0]] for c in cols] for r in range(len(A))]+[[c[1][b] for c in cols] for b in range(8)]
open(sys.argv[2],'w').write('\n'.join(' '.join(map(str,r)) for r in R)+'\n')
