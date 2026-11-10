import sys, numpy as np, time
f, pf, out = sys.argv[1], sys.argv[2], sys.argv[3]
A=[list(map(int,l.split())) for l in open(f) if l.strip()]
N=len(A); k=len(A[0]); full=(1<<N)-1; F=np.uint64(full)
cols=np.array([sum(A[r][j]<<r for r in range(N)) for j in range(k)],dtype=np.uint64)
I,J=np.triu_indices(k,1)
M=[];PI=[];PA=[];PJ=[];PB=[]
for a in (0,1):
    for b in (0,1):
        M.append((cols[I] if a else ~cols[I]&F)&(cols[J] if b else ~cols[J]&F)); PI.append(I); PJ.append(J)
        PA.append(np.full(len(I),a)); PB.append(np.full(len(I),b))
M=np.concatenate(M);PI=np.concatenate(PI);PJ=np.concatenate(PJ);PA=np.concatenate(PA);PB=np.concatenate(PB)
P=[int(x) for x in open(pf)]; n=len(P)
W1=np.zeros((n,k),bool); W0=np.zeros((n,k),bool); newbit=np.zeros(n,int); old=np.zeros(n,np.uint64)
for t,c in enumerate(P):
    co=np.uint64(c&full); old[t]=co; newbit[t]=c>>N&1
    viol=((M&co)==0)|((M&~co&F)==0)
    for idx in np.nonzero(viol)[0]:
        (W1 if PA[idx] else W0)[t,PI[idx]]=True; (W1 if PB[idx] else W0)[t,PJ[idx]]=True
assert not (W1&W0).any()
print('pool',n,'mean demanded cells %.1f'%((W1|W0).sum(1).mean()),'zero-demand columns',int(((W1|W0).sum(1)==0).sum()),flush=True)
conf=(W1.astype(np.int32)@W0.T.astype(np.int32))>0; conf|=conf.T
cand=np.argwhere(np.triu(~conf,1)); print('demand-compatible pairs',len(cand),flush=True)
found=0; t0=time.time()
for x,y in cand:
    w1=W1[x]|W1[y]; w0=W0[x]|W0[y]; ok=True
    for b in (0,1):
        for d in (0,1):
            m=(old[x] if b else ~old[x]&F)&(old[y] if d else ~old[y]&F)
            u1=(cols&m)==0; u0=(~cols&m&F)==0     # pattern a=1 / a=0 uncovered by old rows
            if (b,d)!=(newbit[x],newbit[y]):
                if u1.any() or u0.any(): ok=False;break
            else:
                if (u1&u0).any() or (u1&w0).any() or (u0&w1).any(): ok=False;break
                w1=w1|u1; w0=w0|u0
        if not ok: break
    if ok:
        found+=1
        yrow=[1 if w1[i] else 0 for i in range(k)]
        rows=[A[r]+[P[x]>>r&1,P[y]>>r&1] for r in range(N)]+[yrow+[int(newbit[x]),int(newbit[y])]]
        open(out,'w').write('\n'.join(' '.join(map(str,r)) for r in rows)+'\n'); print('FOUND pair',x,y,flush=True); break
print('checked',len(cand),'found',found,'secs %.0f'%(time.time()-t0))
