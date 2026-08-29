#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, pathlib, sys, types, time
from multiprocessing import Pool
from cache_contract import KERNEL, n9_metadata, save_columns, sha256_path

ROOT=pathlib.Path('/data/projects/relu-depth-frontier-research')
CERT=ROOT/'literature/repos/max-relu-certificates/certificates/certificate_9_4.json'
VER=ROOT/'literature/repos/max-relu-certificates/verify_certificate.py'
META=n9_metadata()

def getmod():
    m=types.ModuleType('tqdm'); m.tqdm=lambda xs,**kw:xs; sys.modules['tqdm']=m
    spec=importlib.util.spec_from_file_location('upverify',VER)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod

def work(item):
    idx,pair=item; mod=getmod()
    left,right=mod.read_pair(pair,9)
    lin,hinges=mod.symmetrized_pair(left,right,9)
    return idx,lin,hinges

def compute():
    d=json.loads(CERT.read_text()); items=[(i,t['pair']) for i,t in enumerate(d['terms'])]
    out=[None]*len(items); t=time.time()
    with Pool(8) as pool:
      for k,(i,lin,h) in enumerate(pool.imap_unordered(work,items,chunksize=1),1):
        out[i]=(lin,h)
        if k%20==0: print('columns',k,'/',len(items),'elapsed',round(time.time()-t,1),flush=True)
    if sha256_path(CERT)!=META['certificate_sha256'] or sha256_path(KERNEL)!=META['kernel_sha256']:
        raise SystemExit('kernel or certificate changed during column generation')
    path=save_columns('n9_columns',META,out)
    print('wrote content-bound cache',path,flush=True)
    return out

cols=compute()
directions=sorted(set().union(*(set(h) for _,h in cols)))
row={d:i for i,d in enumerate(directions)}
offset=len(directions); nrows=offset+9
print('directions',len(directions),'rows',nrows,'columns',len(cols),flush=True)

from flint import nmod_mat
missing={46,171}
keep=[i for i in range(len(cols)) if i not in missing]
for prime in (1000003,1000033,1000037):
  M=nmod_mat(len(keep),nrows,prime)
  for rr,j in enumerate(keep):
    lin,h=cols[j]
    for d,v in h.items():
      if v%prime:M[rr,row[d]]=v%prime
    for q,v in enumerate(lin):
      if v%prime:M[rr,offset+q]=v%prime
  r=M.rank()
  A=nmod_mat(len(keep)+1,nrows,prime)
  # Copy entries. Matrix is only 336 x ~20k.
  for i in range(len(keep)):
    for j in range(nrows):
      v=M[i,j]
      if v:A[i,j]=v
  A[len(keep),offset+8]=1
  ra=A.rank()
  print('prime',prime,'rank_without_two',r,'rank_aug_target',ra,'obstructed',ra>r,flush=True)
