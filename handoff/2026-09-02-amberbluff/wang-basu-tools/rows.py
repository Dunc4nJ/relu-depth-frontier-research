import numpy as np, itertools
def comps(N,k):
    out=[]
    def rec(pref,n,rem):
        if n==1: out.append(pref+[rem]); return
        for v in range(rem+1): rec(pref+[v],n-1,rem-v)
    rec([],N,k); return np.array(out,dtype=np.int16)
def count(N,k):
    Y=comps(N,k); C=np.cumsum(Y,axis=1)
    M=len(Y); tot=M*(M+1)//2
    comparable=0
    step=max(1,2000000//max(M,1))
    for s in range(0,M,step):
        A=C[s:s+step][:,None,:]           # (a,1,N)
        B=C[None,:,:]                     # (1,M,N)
        ge=(A>=B).all(axis=2); le=(A<=B).all(axis=2)
        cmpb=ge|le
        # restrict to j>=i
        for ii in range(A.shape[0]):
            i=s+ii
            comparable+=int(cmpb[ii,i:].sum())
    amb=tot-comparable
    return M,tot,amb,N+amb
for N,k in [(5,2),(6,2),(7,3),(8,3),(8,4),(9,4),(10,4),(11,4),(9,5),(10,5),(11,5)]:
    M,tot,amb,con=count(N,k)
    print(f"N={N:2d} k={k}: |eta|={M:6,d}  unordered pairs={tot:12,d}  ambiguous={amb:12,d}  constraints=N+amb={con:,d}")
