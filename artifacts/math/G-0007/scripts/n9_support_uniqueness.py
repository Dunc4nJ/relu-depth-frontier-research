#!/usr/bin/env python3
import pathlib
from flint import nmod_mat
from cache_contract import load_columns, n9_metadata, write_result

cols,_=load_columns('n9_columns',n9_metadata(),337,required=True)
dirs=sorted(set().union(*(set(h) for _,h in cols))); ri={d:i for i,d in enumerate(dirs)}
off=len(dirs); nr=off+9; p=1000003

def matrix(indices, target=False):
 M=nmod_mat(len(indices)+(1 if target else 0),nr,p)
 for rr,j in enumerate(indices):
  lin,h=cols[j]
  for d,v in h.items():
   if v%p:M[rr,ri[d]]=v%p
  for q,v in enumerate(lin):
   if v%p:M[rr,off+q]=v%p
 if target:M[len(indices),off+8]=1
 return M

results=[]
for removed in (set(),{46},{171},{46,171}):
 ids=[i for i in range(len(cols)) if i not in removed]
 r=matrix(ids).rank(); ra=matrix(ids,True).rank()
 print('removed',sorted(removed),'ncols',len(ids),'rank',r,'rank+target',ra,'target_in_span',r==ra)
 results.append({'removed':sorted(removed),'candidate_count':len(ids),'rank_mod_1000003':r,'rank_aug_mod_1000003':ra,'target_in_span_mod_1000003':r==ra})
write_result('n9_support_uniqueness',{'results':results})
