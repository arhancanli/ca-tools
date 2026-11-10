import sys
# agree.py FILE... : min/all pair agreement counts between rows
for fn in sys.argv[1:]:
    A=[list(map(int,l.split())) for l in open(fn) if l.strip()]
    N=len(A);k=len(A[0]);best=[]
    for i in range(N):
        for j in range(i+1,N):
            d=sum(1 for c in range(k) if A[i][c]==A[j][c]); best.append((d,i,j))
    best.sort()
    print(fn.split('/')[-1],N,k,'min agreements',best[:4],'median',best[len(best)//2][0])
