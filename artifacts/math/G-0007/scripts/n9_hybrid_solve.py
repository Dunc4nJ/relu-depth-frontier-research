#!/usr/bin/env python3
from __future__ import annotations
import json,pathlib,time
from fractions import Fraction
from flint import nmod_mat,fmpq_mat,fmpq
from cache_contract import RUN_DIR, atomic_write, bridge_metadata, load_columns, n9_metadata, secure_read, sha256_bytes, write_result

ROOT=pathlib.Path('/data/projects/relu-depth-frontier-research')
bridge,_=load_columns('n9_bridge_columns',bridge_metadata(),710,required=True)
pub,_=load_columns('n9_columns',n9_metadata(),337,required=True)
cert=json.loads((ROOT/'literature/repos/max-relu-certificates/certificates/certificate_9_4.json').read_text())
bridge_pairs=json.loads(secure_read(RUN_DIR/'max9_bridge_reps.json'))

non_idx=[]
for i,t in enumerate(cert['terms']):
 edges=[tuple(e) for s in t['pair'] for e in s];vs={v for e in edges for v in e};simple=len(set(edges))==len(edges) and all(a!=b for a,b in edges)
 adj={v:set() for v in vs}
 for a,b in edges:adj[a].add(b);adj[b].add(a)
 seen=set();stack=[next(iter(vs))]
 while stack:
  v=stack.pop()
  if v in seen:continue
  seen.add(v);stack.extend(adj[v]-seen)
 if not (len(vs)==9 and simple and len(seen)==9 and len(edges)==8):non_idx.append(i)

cols=bridge+[pub[i] for i in non_idx]
meta=[{'kind':'bridge','bridge_index':i,'pair':bridge_pairs[i]} for i in range(len(bridge))]
meta += [{'kind':'published_non_tree','source_term_index':i,'pair':cert['terms'][i]['pair']} for i in non_idx]
dirs=sorted(set().union(*(set(h) for _,h in cols)));ri={d:i for i,d in enumerate(dirs)};off=len(dirs);nr=off+9;p=1000003

def val(j,q):
 lin,h=cols[j]
 if q<off:return h.get(dirs[q],0)
 return lin[q-off]

t=time.time();M=nmod_mat(len(cols),nr,p)
for j,(lin,h) in enumerate(cols):
 for d,v in h.items():
  if v%p:M[j,ri[d]]=v%p
 for q,v in enumerate(lin):
  if v%p:M[j,off+q]=v%p
print('mod matrix built',time.time()-t,flush=True)

# Pivot columns of M^T select independent generator rows of M.
t=time.time();RT,rank=M.transpose().rref();basis=[]
for r in range(rank):
 for c in range(len(cols)):
  if RT[r,c]:basis.append(c);break
assert len(basis)==rank==505
print('generator basis selected',time.time()-t,flush=True)

BM=nmod_mat(rank,nr,p)
for r,j in enumerate(basis):
 for q in range(nr):
  v=M[j,q]
  if v:BM[r,q]=v
t=time.time();RB,rank2=BM.rref();pivq=[]
for r in range(rank2):
 for q in range(nr):
  if RB[r,q]:pivq.append(q);break
assert len(pivq)==rank2==rank
print('coordinate pivots selected',time.time()-t,'targetcoord?',off+8 in pivq,flush=True)

A=fmpq_mat(rank,rank);b=fmpq_mat(rank,1)
for rr,q in enumerate(pivq):
 for cc,j in enumerate(basis):
  v=val(j,q)
  if v:A[rr,cc]=v
 if q==off+8:b[rr,0]=1
t=time.time();x=A.solve(b);print('exact square solve',time.time()-t,flush=True)

# Verify all exact residual coordinates without constructing a second dense matrix.
t=time.time()
for q in range(nr):
 s=fmpq(0)
 for cc,j in enumerate(basis):
  v=val(j,q)
  if v:s += x[cc,0]*v
 want=1 if q==off+8 else 0
 if s!=want:raise SystemExit(f'exact verification failed coordinate {q}: {s} != {want}')
print('exact all-coordinate verification OK',time.time()-t,flush=True)

sol=[]
for cc,j in enumerate(basis):
 if x[cc,0]:sol.append({**meta[j],'coefficient':str(x[cc,0])})
out={'n':9,'family':'bridge-trees-plus-published-nontree-corrections','candidate_count':len(cols),'rank':rank,'nonzero_terms':len(sol),'direction_rows':off,'linear_rows':9,'solution':sol}
path=RUN_DIR/'n9_hybrid_solution.json';solution_bytes=(json.dumps(out,separators=(',',':'))+'\n').encode();atomic_write(path,solution_bytes)
print('solution',path,'nonzero',len(sol),'bytes',path.stat().st_size,flush=True)
outcert={'n':9,'terms':[{'coefficient':t['coefficient'],'pair':t['pair']} for t in sol]}
certpath=RUN_DIR/'n9_hybrid_certificate.json';certificate_bytes=(json.dumps(outcert,separators=(',',':'))+'\n').encode();atomic_write(certpath,certificate_bytes)
print('certificate',certpath,'terms',len(outcert['terms']),'bytes',certpath.stat().st_size,flush=True)
write_result('n9_hybrid_solve',{
 'candidate_count':len(cols),'rank':rank,'nonzero_terms':len(sol),
 'direction_rows':off,'linear_rows':9,'all_coordinate_verification':True,
 'solution_sha256':sha256_bytes(solution_bytes),
 'certificate_sha256':sha256_bytes(certificate_bytes),
})
