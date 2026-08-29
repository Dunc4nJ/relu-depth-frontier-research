#!/usr/bin/env python3
from __future__ import annotations
import itertools,json,pathlib,time
from fractions import Fraction
import networkx as nx
from cache_contract import (
 RUN_DIR,TREE_MANIFEST,TREE_SCHEMA,atomic_json,atomic_write,sha256_bytes,sha256_path,
)

ROOT=pathlib.Path('/data/projects/relu-depth-frontier-research/literature/repos/max-relu-certificates/certificates')
OUT={}

def emit(name,filename,reps):
 data=json.dumps([[[list(e) for e in s] for s in p] for p in reps],separators=(',',':')).encode()
 atomic_write(RUN_DIR/filename,data)
 OUT[name]={'filename':filename,'count':len(reps),'sha256':sha256_bytes(data),'bytes':len(data)}

def load(n):
 d=json.loads((ROOT/f'certificate_{n}_{(n-1)//2}.json').read_text())
 return [(tuple(tuple(tuple(e) for e in s) for s in t['pair']),Fraction(t['coefficient'])) for t in d['terms']]

def nxg(pair):
 g=nx.Graph()
 for col,s in enumerate(pair):
  for a,b in s:
   if g.has_edge(a,b): return None # a tree cannot have parallel edges
   g.add_edge(a,b,color=col)
 return g

def centers(g):
 deg=dict(g.degree()); leaves=[v for v,d in deg.items() if d<=1]; remain=len(deg)
 while remain>2:
  new=[]; remain-=len(leaves)
  for v in leaves:
   for w in g.neighbors(v):
    if deg[w]>0:
     deg[w]-=1
     if deg[w]==1:new.append(w)
   deg[v]=0
  leaves=new
 return sorted(leaves)

def rooted(g,v,parent,sw):
 kids=[]
 for w,d in g[v].items():
  if w==parent:continue
  col=d['color']^sw
  kids.append(str(col)+rooted(g,w,v,sw))
 return '('+''.join(sorted(kids))+')'

def code(pair):
 g=nxg(pair)
 if g is None or not nx.is_tree(g):raise ValueError('not tree')
 vals=[]
 for sw in (0,1): vals.append(min(rooted(g,c,None,sw) for c in centers(g)))
 return min(vals)

def source_forests(n):
 out=[]
 for p,c in load(n):
  gm=nx.MultiGraph()
  for s in p:
   for a,b in s:gm.add_edge(a,b)
  r=gm.number_of_nodes(); cc=nx.number_connected_components(gm); beta=gm.number_of_edges()-r+cc
  if (r,cc,beta)==(n,2,0):out.append((p,c))
 return out

def closure(n):
 src=source_forests(n); N=n+1; edges=[(a,b) for a in range(1,N+1) for b in range(a+1,N+1)]
 reps={}; raw=0;t=time.time()
 for si,(p,c) in enumerate(src):
  A,B=p
  for ea in edges:
   for eb in edges:
    if N not in ea and N not in eb:continue
    cand=(tuple(sorted((*A,ea))),tuple(sorted((*B,eb))))
    g=nxg(cand)
    if g is None or g.number_of_nodes()!=N or not nx.is_tree(g):continue
    raw+=1; reps.setdefault(code(cand),cand)
 print('closure',n,'->',N,'source_forests',len(src),'raw',raw,'unique',len(reps),'elapsed',round(time.time()-t,2))
 return reps

def universe(N):
 k=(N-1)//2; reps={};t=time.time()
 for tree in nx.generators.nonisomorphic_trees(N):
  es=list(tree.edges())
  for Aidx in itertools.combinations(range(len(es)),k):
   aset=set(Aidx)
   A=tuple(sorted(tuple(sorted((a+1,b+1))) for i,(a,b) in enumerate(es) if i in aset))
   B=tuple(sorted(tuple(sorted((a+1,b+1))) for i,(a,b) in enumerate(es) if i not in aset))
   p=(A,B); reps.setdefault(code(p),p)
 print('universe N',N,'unique colored trees',len(reps),'elapsed',round(time.time()-t,2))
 return reps

for n in (8,10):
 c=closure(n); u=universe(n+1)
 ck=set(c); uk=set(u)
 actual={code(p) for p,_ in load(n+1) if (lambda g:g and g.number_of_nodes()==n+1 and nx.is_tree(g))(nxg(p))} if n+1<=10 else set()
 print(' coverage universe',len(ck&uk),'/',len(uk),float(len(ck&uk)/len(uk)))
 if actual: print(' coverage actual full trees',len(ck&actual),'/',len(actual),'closure extras',len(ck-actual))
 if n==10:
  emit('max11_bridge','max11_bridge_reps.json',list(c.values()))
 if n==8:
  emit('max9_bridge','max9_bridge_reps.json',list(c.values()))
  emit('max9_all_trees','max9_all_tree_reps.json',list(u.values()))
  emit('max9_extra_trees','max9_extra_tree_reps.json',[u[k] for k in u if k not in c])
 if n==10:
  emit('max11_all_trees','max11_all_tree_reps.json',list(u.values()))

manifest={
 'schema':TREE_SCHEMA,
 'generator_sha256':sha256_path(pathlib.Path(__file__).resolve()),
 'source_sha256':{p.name:sha256_path(p) for p in (
  ROOT/'certificate_8_3.json',
  ROOT/'certificate_9_4.json',
  ROOT/'certificate_10_4.json',
 )},
 'outputs':OUT,
}
atomic_json(TREE_MANIFEST,manifest)
print('tree representative manifest',TREE_MANIFEST)
