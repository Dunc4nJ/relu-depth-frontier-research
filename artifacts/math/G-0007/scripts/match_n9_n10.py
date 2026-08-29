#!/usr/bin/env python3
import json
import math
from pathlib import Path
from fractions import Fraction
from collections import defaultdict, Counter
import networkx as nx
from networkx.algorithms.isomorphism import MultiGraphMatcher, categorical_multiedge_match

ROOT=Path('/data/projects/relu-depth-frontier-research/literature/repos/max-relu-certificates/certificates')

def load(n):
 d=json.loads((ROOT/f'certificate_{n}_{(n-1)//2}.json').read_text())
 return [(t['pair'],Fraction(t['coefficient'])) for t in d['terms']]

def graph(pair,swap=False):
 g=nx.MultiGraph()
 sides=pair[::-1] if swap else pair
 used={v for s in sides for e in s for v in e}
 g.add_nodes_from(used)
 for col,s in enumerate(sides):
  for a,b in s:g.add_edge(a,b,color=col)
 return g

def cheap(pair):
 gs=[]
 for sw in (False,True):
  g=graph(pair,sw)
  nodes=sorted(g.nodes)
  per=[]
  for v in nodes:
   ca=cb=0
   for _,_,d in g.edges(v,data=True):
    # networkx degree counts loops twice, edges iterator presents loops once;
    # use endpoint multiplicity separately below only for bucketing.
    if d['color']==0:ca+=1
    else:cb+=1
   per.append((ca,cb,g.degree(v)))
  loops=Counter(d['color'] for a,b,d in g.edges(data=True) if a==b)
  gs.append((g.number_of_nodes(),tuple(sorted(per)),tuple(sorted(loops.items())),tuple(sorted(len(c) for c in nx.connected_components(g)))))
 return min(gs)

em=categorical_multiedge_match('color',None)
def iso(p,q):
 gp=graph(p)
 return MultiGraphMatcher(gp,graph(q),edge_match=em).is_isomorphic() or MultiGraphMatcher(gp,graph(q,True),edge_match=em).is_isomorphic()

A=load(9); B=load(10)
buckets=defaultdict(list)
for j,(q,c) in enumerate(B):buckets[cheap(q)].append((j,q,c))
matches=[]; ambiguous=[]
for i,(p,c9) in enumerate(A):
 ms=[(j,c10) for j,q,c10 in buckets[cheap(p)] if iso(p,q)]
 if ms: matches.append((i,c9,ms))
 if len(ms)>1: ambiguous.append((i,ms))
print('matched n9 types',len(matches),'of',len(A),'ambiguous',len(ambiguous),'matched pairs',sum(len(x[2]) for x in matches))
rat=Counter()
normalized_rat=Counter()
active=Counter()
for i,c9,ms in matches:
 for j,c10 in ms:
  rat[c10/c9]+=1
  r=len(graph(A[i][0]).nodes)
  normalized_rat[(c10*math.factorial(10-r))/(c9*math.factorial(9-r))]+=1
  active[r]+=1
print('active matched',active)
print('ratio top',rat.most_common(25),'distinct',len(rat))
print('injection-normalized ratio distinct',len(normalized_rat))
print('unmatched9 active',Counter(len(graph(p).nodes) for i,(p,c) in enumerate(A) if all(i!=x[0] for x in matches)))
matchedj={j for _,_,ms in matches for j,_ in ms}
print('unmatched10 active',Counter(len(graph(p).nodes) for j,(p,c) in enumerate(B) if j not in matchedj))
