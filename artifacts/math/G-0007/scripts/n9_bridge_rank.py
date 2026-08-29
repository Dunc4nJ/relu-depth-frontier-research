#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,pathlib,sys,types,time
from multiprocessing import Pool
from flint import nmod_mat
from cache_contract import KERNEL, RUN_DIR, bridge_metadata, save_columns, secure_read, sha256_bytes, sha256_path

ROOT=pathlib.Path('/data/projects/relu-depth-frontier-research')
VER=ROOT/'literature/repos/max-relu-certificates/verify_certificate.py'
IN=RUN_DIR/'max9_bridge_reps.json'; META=bridge_metadata()

def mod():
 m=types.ModuleType('tqdm');m.tqdm=lambda xs,**kw:xs;sys.modules['tqdm']=m
 s=importlib.util.spec_from_file_location('upv',VER);x=importlib.util.module_from_spec(s);s.loader.exec_module(x);return x
def work(z):
 i,p=z;x=mod();a,b=x.read_pair(p,9);lin,h=x.symmetrized_pair(a,b,9);return i,lin,h
def compute():
 reps=json.loads(secure_read(IN));out=[None]*len(reps);t=time.time()
 with Pool(8) as pool:
  for k,(i,l,h) in enumerate(pool.imap_unordered(work,enumerate(reps),chunksize=1),1):
   out[i]=(l,h)
   if k%50==0:print('columns',k,'/',len(reps),'elapsed',round(time.time()-t,1),flush=True)
 if sha256_bytes(secure_read(IN))!=META['representatives_sha256'] or sha256_path(KERNEL)!=META['kernel_sha256']:
  raise SystemExit('kernel or representatives changed during column generation')
 path=save_columns('n9_bridge_columns',META,out);print('wrote content-bound cache',path,flush=True);return out
cols=compute()
dirs=sorted(set().union(*(set(h) for _,h in cols)));ri={d:i for i,d in enumerate(dirs)};off=len(dirs);nr=off+9
print('directions',off,'rows',nr,'columns',len(cols),flush=True)
for p in (1000003,1000033,1000037):
 M=nmod_mat(len(cols)+1,nr,p)
 for rr,(lin,h) in enumerate(cols):
  for d,v in h.items():
   if v%p:M[rr,ri[d]]=v%p
  for q,v in enumerate(lin):
   if v%p:M[rr,off+q]=v%p
 # rank candidates, then include target as final row
 cand=nmod_mat(len(cols),nr,p)
 for i in range(len(cols)):
  for j in range(nr):
   v=M[i,j]
   if v:cand[i,j]=v
 r=cand.rank();M[len(cols),off+8]=1;ra=M.rank()
 print('prime',p,'rank',r,'rank+target',ra,'full_row_rank',r==len(cols),'target_in_span',r==ra,flush=True)
