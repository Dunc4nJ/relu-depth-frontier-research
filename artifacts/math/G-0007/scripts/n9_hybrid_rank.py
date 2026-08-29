#!/usr/bin/env python3
import json,pathlib,time
from flint import nmod_mat,fmpz_mat
from cache_contract import bridge_metadata, load_columns, n9_metadata, write_result

R=pathlib.Path('/data/projects/relu-depth-frontier-research')
bridge,_=load_columns('n9_bridge_columns',bridge_metadata(),710,required=True)
pub,_=load_columns('n9_columns',n9_metadata(),337,required=True)
d=json.loads((R/'literature/repos/max-relu-certificates/certificates/certificate_9_4.json').read_text())
non=[]
for i,t in enumerate(d['terms']):
 edges=[tuple(e) for s in t['pair'] for e in s]; vs={v for e in edges for v in e}
 simple=len(set(edges))==len(edges) and all(a!=b for a,b in edges)
 adj={v:set() for v in vs}
 for a,b in edges:adj[a].add(b);adj[b].add(a)
 seen=set(); stack=[next(iter(vs))]
 while stack:
  v=stack.pop()
  if v in seen:continue
  seen.add(v);stack.extend(adj[v]-seen)
 fulltree=len(vs)==9 and simple and len(seen)==9 and len(edges)==8
 if not fulltree: non.append(pub[i])
cols=bridge+non
dirs=sorted(set().union(*(set(h) for _,h in cols)));ri={d:i for i,d in enumerate(dirs)};off=len(dirs);nr=off+9
print('bridge',len(bridge),'non_tree_corrections',len(non),'total',len(cols),'directions',off,'rows',nr,flush=True)
def build(cls,mod=None,target=False):
 args=(len(cols)+(1 if target else 0),nr) if mod is None else (len(cols)+(1 if target else 0),nr,mod)
 M=cls(*args)
 for rr,(lin,h) in enumerate(cols):
  for dd,v in h.items():
   if v:M[rr,ri[dd]]=v
  for q,v in enumerate(lin):
   if v:M[rr,off+q]=v
 if target:M[len(cols),off+8]=1
 return M
p=1000003;t=time.time();M=build(nmod_mat,p);r=M.rank();A=build(nmod_mat,p,True);ra=A.rank();print('mod',p,'rank',r,'aug',ra,'in_span',r==ra,'sec',time.time()-t,flush=True)
t=time.time();Q=build(fmpz_mat);rq=Q.rank();AQ=build(fmpz_mat,target=True);raq=AQ.rank();print('exact rank',rq,'aug',raq,'in_span',rq==raq,'sec',time.time()-t,flush=True)
write_result('n9_hybrid_rank',{'candidate_count':len(cols),'hinge_directions':off,'coordinate_count':nr,'rank_Q':rq,'rank_aug_Q':raq,'target_in_span':rq==raq})
