#!/usr/bin/env python3
from __future__ import annotations
import json,pathlib,time
from collections import defaultdict,Counter
import networkx as nx
from networkx.algorithms.isomorphism import GraphMatcher,categorical_node_match

ROOT=pathlib.Path('/data/projects/relu-depth-frontier-research/literature/repos/max-relu-certificates/certificates');NM=categorical_node_match('kind',None)
def load(n):
 d=json.loads((ROOT/f'certificate_{n}_{(n-1)//2}.json').read_text());return [tuple(tuple(tuple(e) for e in s) for s in t['pair']) for t in d['terms']]
def gadget(pair,swap=False):
 g=nx.Graph();vs=sorted({v for s in pair for e in s for v in e})
 for v in vs:g.add_node(('v',v),kind='V')
 eid=0
 for col,s in enumerate(pair[::-1] if swap else pair):
  for a,b in s:
   e=('e',eid);i=('i',eid,0);j=('i',eid,1);eid+=1
   for node,kind in ((e,'E'+str(col)),(i,'I'),(j,'I')):g.add_node(node,kind=kind)
   g.add_edge(e,i);g.add_edge(e,j);g.add_edge(i,('v',a));g.add_edge(j,('v',b))
 return g
def whash(p):return min(nx.weisfeiler_lehman_graph_hash(gadget(p,s),node_attr='kind',iterations=6) for s in (0,1))
def iso(p,q):
 gp=gadget(p);return GraphMatcher(gp,gadget(q),node_match=NM).is_isomorphic() or GraphMatcher(gp,gadget(q,True),node_match=NM).is_isomorphic()
def test(a,b):
 src=load(a);tgt=load(b);buck=defaultdict(list)
 for j,q in enumerate(tgt):buck[whash(q)].append((j,q))
 E=[(u,v) for u in range(1,b+1) for v in range(u,b+1)]
 matched=defaultdict(set);raw=0;t=time.time()
 for i,p in enumerate(src):
  A,B=p
  for ea in E:
   for eb in E:
    cand=(tuple(sorted((*A,ea))),tuple(sorted((*B,eb))));raw+=1
    for j,q in buck.get(whash(cand),[]):
     if iso(cand,q):matched[j].add(i)
 print(a,'->',b,'source',len(src),'target',len(tgt),'raw',raw,'matched',len(matched),'elapsed',round(time.time()-t,2))
 print(' preimage multiplicity',Counter(len(x) for x in matched.values()),'sources used',len(set().union(*matched.values())) if matched else 0)
 print(' missing target indices',[j for j in range(len(tgt)) if j not in matched])
test(6,7)
test(8,9)
