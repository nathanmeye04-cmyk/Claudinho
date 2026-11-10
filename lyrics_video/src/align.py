import json, re, unicodedata, difflib
W=json.load(open("whisper_words_medium.json"))
def norm(s):
    s=unicodedata.normalize("NFD",s.lower()); s="".join(c for c in s if unicodedata.category(c)!="Mn")
    s=s.replace("œ","oe"); return re.sub(r"[^a-z]","",s)
# split whisper words on apostrophes for tokens
wt=[]
for w in W:
    parts=[p for p in re.split(r"[’']",w["w"]) if norm(p)]
    if not parts: continue
    d=(w["e"]-w["s"])/len(parts)
    for k,p in enumerate(parts): wt.append({"n":norm(p),"s":w["s"]+k*d,"e":w["s"]+(k+1)*d})
lines=[l.strip() for l in open("paroles.txt",encoding="utf-8") if l.strip()]
# lyric display words (keep punctuation attached); tokens for matching split on apostrophes
L=[]
for li,l in enumerate(lines):
    for wi,word in enumerate(l.split()):
        toks=[p for p in re.split(r"[’']",word) if norm(p)]
        for t in toks: L.append({"line":li,"word":wi,"n":norm(t)})
a=[x["n"] for x in L]; b=[x["n"] for x in wt]
sm=difflib.SequenceMatcher(None,a,b,autojunk=False)
for tag,i1,i2,j1,j2 in sm.get_opcodes():
    if tag=="equal":
        for k in range(i2-i1): L[i1+k]["s"]=wt[j1+k]["s"]; L[i1+k]["e"]=wt[j1+k]["e"]
    elif tag=="replace" and j2>j1:
        s0,e0=wt[j1]["s"],wt[j2-1]["e"]; n=i2-i1
        for k in range(n): L[i1+k]["s"]=s0+(e0-s0)*k/n; L[i1+k]["e"]=s0+(e0-s0)*(k+1)/n
# interpolate unmatched
idx=[i for i,x in enumerate(L) if "s" in x]
for i,x in enumerate(L):
    if "s" not in x:
        p=max([j for j in idx if j<i],default=None); q=min([j for j in idx if j>i],default=None)
        ps=L[p]["e"] if p is not None else L[q]["s"]-0.3; qs=L[q]["s"] if q is not None else ps+0.3
        x["s"]=x["e"]=None; x["interp"]=(ps,qs,p,q)
for i,x in enumerate(L):
    if x["s"] is None:
        ps,qs,p,q=x["interp"]; run=[j for j in range(len(L)) if L[j].get("interp")==x["interp"]]
        k=run.index(i); n=len(run); x["s"]=ps+(qs-ps)*k/n; x["e"]=ps+(qs-ps)*(k+1)/n
# word-level output
out=[]
for li,l in enumerate(lines):
    words=l.split(); ws=[]
    for wi,word in enumerate(words):
        t=[x for x in L if x["line"]==li and x["word"]==wi]
        if t: ws.append({"t":word,"s":round(min(x["s"] for x in t),3),"e":round(max(x["e"] for x in t),3)})
        else: ws.append({"t":word,"s":None,"e":None})
    for k,w in enumerate(ws):  # punctuation-only words
        if w["s"] is None: w["s"]=w["e"]=ws[k-1]["e"] if k else ws[k+1]["s"]
    out.append({"line":l,"s":ws[0]["s"],"e":ws[-1]["e"],"words":ws})
json.dump(out,open("sync_paroles.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
for i,o in enumerate(out): print(f"{i:2d} {o['s']:7.2f} {o['e']:7.2f}  {o['line']}")
print("unmatched tokens:",sum(1 for x in L if "interp" in x),"/",len(L))
