import re, json, sys

SRC="/data/projects/relu-depth-frontier-research/literature/papers/2608.25221.txt"
lines=open(SRC).read().split("\n")

def stream(lo,hi,split):
    left=[]; right=[]
    for i in range(lo-1,hi):
        L=lines[i]
        left.append(L[:split]); right.append(L[split:])
    return "\n".join(left), "\n".join(right)

PAT=re.compile(r'^[a-h]{2}(?: [a-h]{2})+$')
def parse(txt, npairs):
    # tokenize
    toks=[]
    for ln in txt.split("\n"):
        # capture pattern strings first
        m=re.search(r'([a-h]{2}(?: [a-h]{2}){%d}) \| ([a-h]{2}(?: [a-h]{2}){%d})'%(npairs-1,npairs-1), ln)
        if m:
            pre=ln[:m.start()]; post=ln[m.end():]
            toks+= pre.split()
            toks.append(("PAT", m.group(1), m.group(2)))
            toks+= post.split()
        else:
            toks+= ln.split()
    entries={}
    i=0
    lastnum=None
    while i<len(toks):
        t=toks[i]
        if isinstance(t,tuple):
            lastnum=None; i+=1; continue
        if re.fullmatch(r'\d+\.',t):
            j=int(t[:-1])
            num=lastnum
            i+=1
            sign=1
            if i<len(toks) and toks[i]=='−':
                sign=-1; i+=1
            den=toks[i]; i+=1
            # next token should be PAT
            assert isinstance(toks[i],tuple), (j,toks[i-3:i+3])
            _,l,r=toks[i]; i+=1
            entries[j]=(sign,int(num),int(den),l.split(),r.split())
            lastnum=None
            continue
        if re.fullmatch(r'\d+',t):
            lastnum=t
        i+=1
    return entries

# MAX7 table: lines 586..865, k=3
l7,r7=stream(586,865,48)
e7=parse(l7,3); e7.update(parse(r7,3))
print("MAX7 entries:",len(e7),"min",min(e7),"max",max(e7),"missing",[j for j in range(1,110) if j not in e7])

l8,r8=stream(875,4145,51)
e8=parse(l8,4); e8.update(parse(r8,4))
print("MAX8 entries:",len(e8),"min",min(e8),"max",max(e8))
miss=[j for j in range(1,1291) if j not in e8]
print("missing:",miss[:20], len(miss))

json.dump({"max7":{str(k):v for k,v in e7.items()},"max8":{str(k):v for k,v in e8.items()}},
          open("/home/ubuntu/.cache/tmp/claude-1000/-data-projects-relu-depth-frontier-research/e3c7772e-be35-41c0-9f1a-451dc7cbd45b/scratchpad/wb_tables.json","w"))
print("sample7", e7[1], e7[46], e7[109])
print("sample8", e8[1], e8[34], e8[1290])
