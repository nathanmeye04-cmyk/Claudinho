import numpy as np,cv2,sys
sys.path.insert(0,'scripts'); from dark import darkness
N=345; raw=[]
for i in range(1,N+1):
    S=np.zeros((576,1024),np.float32)
    if i>=262:
        D,Wt,a=darkness(i)
        num=cv2.GaussianBlur(D*Wt,(0,0),6); den=cv2.GaussianBlur(Wt,(0,0),6)
        Sf=np.where(den>0.2,num/(den+1e-6),0).astype(np.float32)
        m=(Sf>0.14).astype(np.uint8); n,lab,st,_=cv2.connectedComponentsWithStats(m)
        if n>1:
            cand=[k for k in range(1,n) if st[k,4]>30000 and st[k,3]>200 and (i<319 or st[k,0]+st[k,2]>=1000)]
            k=max(cand,key=lambda k:st[k,4]) if cand else None
            if k is not None:
                keep=cv2.GaussianBlur(cv2.dilate((lab==k).astype(np.uint8),np.ones((15,15),np.uint8)).astype(np.float32),(0,0),6)
                S=np.clip(Sf*keep,0,0.6)
    raw.append(S)
for i in range(N):
    cv2.imwrite(f'shadow2/{i+1:04d}.png',(np.clip(raw[i],0,1)*65535).astype(np.uint16))
