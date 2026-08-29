#!/usr/bin/env python3
import importlib.util,json,pathlib,sys,types
from multiprocessing import Pool
from flint import fmpz_mat
from cache_contract import RUN_DIR, bridge_metadata, load_columns, load_tree_manifest, secure_read, write_result
ROOT=pathlib.Path('/data/projects/relu-depth-frontier-research');VER=ROOT/'literature/repos/max-relu-certificates/verify_certificate.py'
def mod():
 m=types.ModuleType('tqdm');m.tqdm=lambda x,**k:x;sys.modules['tqdm']=m;s=importlib.util.spec_from_file_location('v',VER);x=importlib.util.module_from_spec(s);s.loader.exec_module(x);return x
def work(z):
 i,p=z;x=mod();a,b=x.read_pair(p,9);return i,*x.symmetrized_pair(a,b,9)
load_tree_manifest()
extra=json.loads(secure_read(RUN_DIR/'max9_extra_tree_reps.json'))
assert len(extra)==29
with Pool(8) as pool: out=sorted(pool.map(work,enumerate(extra)))
bridge,_=load_columns('n9_bridge_columns',bridge_metadata(),710,required=True)
cols=bridge+[(l,h) for _,l,h in out]
dirs=sorted(set().union(*(set(h) for _,h in cols)));ri={d:i for i,d in enumerate(dirs)};off=len(dirs);nr=off+9
def build(target=False):
 M=fmpz_mat(len(cols)+(1 if target else 0),nr)
 for rr,(lin,h) in enumerate(cols):
  for d,v in h.items():
   if v:M[rr,ri[d]]=v
  for q,v in enumerate(lin):
   if v:M[rr,off+q]=v
 if target:M[len(cols),off+8]=1
 return M
M=build();r=M.rank();A=build(True);ra=A.rank();print('all_tree_types',len(cols),'directions',off,'rank_Q',r,'rank_aug_Q',ra,'target_in_span',r==ra)
write_result('n9_alltree_rank',{'candidate_count':len(cols),'hinge_directions':off,'coordinate_count':nr,'rank_Q':r,'rank_aug_Q':ra,'target_in_span':r==ra})
