# pad.py SRC N K SEED OUT: copy the array SRC and fill it up to N rows and K columns with random bits (start state for ext3 -i)
import sys,random
src,N,k,seed,out=sys.argv[1],int(sys.argv[2]),int(sys.argv[3]),int(sys.argv[4]),sys.argv[5]
A=[l.split() for l in open(src) if l.strip()]; random.seed(seed); n0=len(A); k0=len(A[0])
R=[r+[str(random.randint(0,1)) for _ in range(k-k0)] for r in A]+[[str(random.randint(0,1)) for _ in range(k)] for _ in range(N-n0)]
open(out,'w').write('\n'.join(' '.join(r) for r in R)+'\n')
