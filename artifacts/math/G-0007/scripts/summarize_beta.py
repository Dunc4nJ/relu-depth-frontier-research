#!/usr/bin/env python3
import json,pathlib
from collections import Counter

ROOT=pathlib.Path('/data/projects/relu-depth-frontier-research/literature/repos/max-relu-certificates/certificates')

def components(vertices,edges):
 adj={v:set() for v in vertices}
 for a,b in edges:
  if a!=b:adj[a].add(b);adj[b].add(a)
 unseen=set(vertices);count=0
 while unseen:
  count+=1;stack=[unseen.pop()]
  while stack:
   v=stack.pop()
   for w in adj[v]:
    if w in unseen:unseen.remove(w);stack.append(w)
 return count

for n in (9,10):
 d=json.loads((ROOT/f'certificate_{n}_4.json').read_text()); hist=Counter(); active=Counter(); loops=0
 for t in d['terms']:
  edges=[tuple(e) for side in t['pair'] for e in side];vs={v for e in edges for v in e};c=components(vs,edges);beta=len(edges)-len(vs)+c
  hist[beta]+=1;active[len(vs)]+=1;loops+=sum(a==b for a,b in edges)
 print('n',n,'terms',len(d['terms']),'active',dict(sorted(active.items())),'beta',dict(sorted(hist.items())),'loop_occurrences',loops)
