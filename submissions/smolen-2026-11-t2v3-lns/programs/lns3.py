#!/usr/bin/env python3
"""lns2.py START N R poolsecs clsecs wall outprefix seed0 - column LNS: remove R random columns,
pool QI candidates (pool.c), find R+g mutually QI candidates (kcl.c tabu), g = 1,2,..; accept gain>=0.
Own code, debate 9 agent C."""
import sys, subprocess, os, time
start,N,R,ps,cs,wall,outp,seed0=sys.argv[1],int(sys.argv[2]),int(sys.argv[3]),sys.argv[4],sys.argv[5],float(sys.argv[6]),sys.argv[7],int(sys.argv[8])
A=[list(map(int,l.split())) for l in open(start) if l.strip()]
if min(map(min,A))==1: A=[[x-1 for x in r] for r in A]
cols=[''.join(str(A[r][c]) for r in range(N)) for c in range(len(A[0]))]
T0=time.time(); it=0
while time.time()-T0<wall:
    K=len(cols); fn=f'{outp}_cur.txt'
    with open(fn,'w') as f:
        for r in range(N): f.write(' '.join(c[r] for c in cols)+'\n')
    env=dict(os.environ,DUMP=f'{outp}_pool.txt',KEEP=f'{outp}_keep.txt')
    t0=time.time(); sd=seed0+it; it+=1
    o=subprocess.run(['nice','./pool',fn,str(N),str(K),str(R),str(sd),'10000000',ps,'0'],env=env,capture_output=True,text=True).stdout.strip()
    keep=[l.strip() for l in open(f'{outp}_keep.txt') if l.strip()]
    g=0
    while True:
        r=subprocess.run(['nice','./kcl',f'{outp}_pool.txt',str(R+g+1),str(sd),cs,f'{outp}_cl.txt'],capture_output=True,text=True)
        if r.returncode!=0: break
        g+=1; sel=[l.strip() for l in open(f'{outp}_cl.txt') if l.strip()]
    if g>0: cols=keep+sel
    elif os.environ.get('SIDE'):
        r=subprocess.run(['nice','./kcl',f'{outp}_pool.txt',str(R),str(sd+77),'5',f'{outp}_cl.txt'],capture_output=True,text=True)
        if r.returncode==0: cols=keep+[l.strip() for l in open(f'{outp}_cl.txt') if l.strip()]
    print(f"it {it} K={K} -> {len(cols)} gain={g} ({time.time()-t0:.0f}s) | {o[:60]}",flush=True)
    if g>0:
        with open(f'{outp}_{N}_{len(cols)}.txt','w') as f:
            for r in range(N): f.write(' '.join(c[r] for c in cols)+'\n')
