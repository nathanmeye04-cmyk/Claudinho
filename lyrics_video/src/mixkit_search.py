import re, json, subprocess, sys
terms = sys.argv[1:]
res = json.load(open("mixkit_index.json")) if __import__("os").path.exists("mixkit_index.json") else {}
for t in terms:
    for page in ["", "?page=2"]:
        url = f"https://mixkit.co/free-stock-video/{t}/{page}"
        html = subprocess.run(["curl","-s","-A","Mozilla/5.0",url],capture_output=True,text=True).stdout
        for slug,i in re.findall(r'href="/free-stock-video/([a-z0-9-]+)-([0-9]+)/"', html):
            res.setdefault(i, {"slug":slug,"terms":[]})
            if t not in res[i]["terms"]: res[i]["terms"].append(t)
json.dump(res, open("mixkit_index.json","w"), indent=0)
print(len(res))
