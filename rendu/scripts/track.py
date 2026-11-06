import glob,numpy as np,cv2
fs=sorted(glob.glob('src/*.png')); N=len(fs)
def g(i): return cv2.cvtColor(cv2.imread(fs[i]),cv2.COLOR_BGR2GRAY)
def bgmask(i):
    m=cv2.imread(fs[i].replace('src','u2m'),0)>40
    m=cv2.dilate(m.astype(np.uint8),np.ones((41,41),np.uint8))
    return (1-m).astype(np.uint8)*255
Ms=[np.eye(3)]; info=[]
prev=g(0); pm=bgmask(0)
for i in range(1,N):
    cur=g(i)
    p0=cv2.goodFeaturesToTrack(prev,800,0.005,8,mask=pm)
    p1,st,_=cv2.calcOpticalFlowPyrLK(prev,cur,p0,None,winSize=(31,31),maxLevel=4)
    p0b,st2,_=cv2.calcOpticalFlowPyrLK(cur,prev,p1,None,winSize=(31,31),maxLevel=4)
    ok=(st[:,0]==1)&(st2[:,0]==1)&(np.linalg.norm(p0-p0b,axis=2)[:,0]<1)
    A,inl=cv2.estimateAffinePartial2D(p0[ok],p1[ok],method=cv2.RANSAC,ransacReprojThreshold=2)
    if A is None: A=np.eye(2,3)
    info.append((i,int(ok.sum()),int(inl.sum()) if inl is not None else 0))
    Ms.append(np.vstack([A,[0,0,1]]))   # maps prev->cur
    prev=cur; pm=bgmask(i)
np.save('motion.npy',np.array(Ms))
a=np.array(Ms); print('min inliers',min(x[2] for x in info)); 
tx=a[:,0,2];ty=a[:,1,2];sc=np.sqrt(a[:,0,0]**2+a[:,1,0]**2);rot=np.degrees(np.arctan2(a[:,1,0],a[:,0,0]))
print('cum tx',tx.sum(),'ty',ty.sum(),'scale',np.prod(sc),'rot',rot.sum())
for i in range(0,N,20): print(i,round(tx[i],1),round(ty[i],1),round(sc[i],4),round(rot[i],2),info[i-1] if i else '')
