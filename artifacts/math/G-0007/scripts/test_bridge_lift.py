#!/usr/bin/env python3
from __future__ import annotations
import json
from collections import defaultdict, Counter
from pathlib import Path
from fractions import Fraction
import networkx as nx
from networkx.algorithms.isomorphism import MultiGraphMatcher, categorical_multiedge_match

ROOT=Path('/data/projects/relu-depth-frontier-research/literature/repos/max-relu-certificates/certificates')
EM=categorical_multiedge_match('color',None)

def load(n):
 d=json.loads((ROOT/f'certificate_{n}_{(n-1)//2}.json').read_text())
 return [(tuple(tuple(tuple(e) for e in s) for s in t['pair']),Fraction(t['coefficient'])) for t in d['terms']]

def graph(pair,swap=False):
 g=nx.MultiGraph()
 sides=pair[::-1] if swap else pair
 for col,s in enumerate(sides):
  for a,b in s:g.add_edge(a,b,color=col)
 return g

def iso(p,q):
 gp=graph(p)
 return MultiGraphMatcher(gp,graph(q),edge_match=EM).is_isomorphic() or MultiGraphMatcher(gp,graph(q,True),edge_match=EM).is_isomorphic()

def sig(pair):
 g=graph(pair)
 r=g.number_of_nodes(); c=nx.number_connected_components(g); beta=g.number_of_edges()-r+c
 # swap-invariant colored degree profile
 prof=[]
 for sw in (False,True):
  h=graph(pair,sw); rows=[]
  for v in h.nodes:
   ca=sum(1 for _,_,d in h.edges(v,data=True) if d['color']==0)
   cb=sum(1 for _,_,d in h.edges(v,data=True) if d['color']==1)
   rows.append((ca,cb,h.degree(v)))
  prof.append(tuple(sorted(rows)))
 return r,c,beta,min(prof)

def bridge_candidates(pair,newv):
 g=graph(pair)
 comps=[sorted(c) for c in nx.connected_components(g)]
 if len(comps)!=2:return
 A,B=pair
 seen=[]
 for C0,C1 in ((comps[0],comps[1]),(comps[1],comps[0])):
  for u in C0:
   for v in C1:
    aa=tuple(sorted((*A,tuple(sorted((newv,u))))))
    bb=tuple(sorted((*B,tuple(sorted((newv,v))))))
    yield (aa,bb)

def general_two_edge_candidates(pair,newv):
    A,B=pair
    verts=sorted(set(v for side in pair for e in side for v in e)|{newv})
    edges=[(a,b) for a in verts for b in verts if a<=b]
    for ea in edges:
      for eb in edges:
        if newv not in ea and newv not in eb: continue
        aa=tuple(sorted((*A,ea))); bb=tuple(sorted((*B,eb)))
        cand=(aa,bb)
        if sig(cand)[:3]==(newv,1,0): yield cand

def test(srcn,tgtn):
 src=load(srcn); tgt=load(tgtn)
 src=[(p,c) for p,c in src if sig(p)[:3]==(srcn,2,0)]
 tgt=[(p,c) for p,c in tgt if sig(p)[:3]==(tgtn,1,0)]
 print(f'{srcn}->{tgtn} source full forests={len(src)}, target full trees={len(tgt)}')
 buckets=defaultdict(list)
 for j,(q,c) in enumerate(tgt):buckets[sig(q)].append((j,q,c))
 matched=defaultdict(list); generated=[]
 for i,(p,c) in enumerate(src):
  for cand in bridge_candidates(p,tgtn):
   generated.append((i,cand))
   for j,q,cq in buckets[sig(cand)]:
    if iso(cand,q):matched[j].append(i)
 print(' raw candidates',len(generated),'matched target types',len(matched),'/',len(tgt))
 print(' target preimage multiplicity',Counter(len(set(v)) for v in matched.values()))
 print(' source templates used',len({i for v in matched.values() for i in v}),'/',len(src))
 print(' target coeff signs matched',Counter('+' if tgt[j][1]>0 else '-' for j in matched))
 missing=[j for j in range(len(tgt)) if j not in matched]
 print(' missing indices',missing[:30])

 # More general parity lift: add one edge of each color, require the new
 # vertex to appear, and retain only full-support trees.
 matched2=defaultdict(list); raw2=0
 for i,(p,c) in enumerate(src):
  for cand in general_two_edge_candidates(p,tgtn):
   raw2+=1
   for j,q,cq in buckets[sig(cand)]:
    if iso(cand,q):matched2[j].append(i)
 print(' general +one-edge-per-color candidates',raw2,'matched',len(matched2),'/',len(tgt),'sources used',len({i for v in matched2.values() for i in v}))
 print(' general preimage multiplicity',Counter(len(set(v)) for v in matched2.values()))
 print(' general missing', [j for j in range(len(tgt)) if j not in matched2][:30])
 for j in [j for j in range(len(tgt)) if j not in matched2]:
  print('  MISSING_TARGET',j,'coeff',tgt[j][1],'pair',tgt[j][0])
 used2={i for v in matched2.values() for i in v}
 for i in range(len(src)):
  if i not in used2: print('  UNUSED_SOURCE',i,'coeff',src[i][1],'pair',src[i][0])

test(6,7)
test(8,9)
