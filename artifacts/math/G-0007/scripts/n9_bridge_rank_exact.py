#!/usr/bin/env python3
import time
from flint import fmpz_mat
from cache_contract import bridge_metadata, load_columns, write_result
cols,_=load_columns('n9_bridge_columns',bridge_metadata(),710,required=True)
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
t=time.time();M=build(False);print('built',M.nrows(),M.ncols(),'sec',time.time()-t,flush=True)
t=time.time();r=M.rank();print('rank_Q',r,'sec',time.time()-t,flush=True)
t=time.time();A=build(True);ra=A.rank();print('rank_aug_Q',ra,'sec',time.time()-t,'target_in_span',r==ra,flush=True)
write_result('n9_bridge_rank_exact',{'candidate_count':len(cols),'coordinate_count':nr,'rank_Q':r,'rank_aug_Q':ra,'target_in_span':r==ra})
