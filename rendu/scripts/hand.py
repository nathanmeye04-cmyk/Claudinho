import numpy as np,cv2
def box(x,r): return cv2.boxFilter(x,-1,(2*r+1,2*r+1))
def guided(I,p,r,eps):
    mI,mp=box(I,r),box(p,r); cov=box(I*p,r)-mI*mp; var=box(I*I,r)-mI*mI
    a=cov/(var+eps); b=mp-a*mI; return box(a,r)*I+box(b,r)
for k in range(47,55):
    a=cv2.imread(f'alpha/{k:04d}.png',-1)/65535.
    bgr=cv2.imread(f'src/{k:04d}.png'); hsv=cv2.cvtColor(bgr,cv2.COLOR_BGR2HSV).astype(np.float32)
    S=hsv[...,1]/255; H=hsv[...,0]; V=hsv[...,2]/255
    hue=((H<22)|(H>172)); skin=((S>0.42)&(V>0.5)&hue).astype(np.uint8)
    roi=np.zeros_like(skin); roi[300:576,480:820]=1; skin&=roi
    skin=cv2.morphologyEx(skin,cv2.MORPH_OPEN,np.ones((3,3),np.uint8))
    n,lab,st,_=cv2.connectedComponentsWithStats(skin); keep=np.zeros_like(skin)
    for c in range(1,n):
        if st[c,4]>800: keep|=(lab==c).astype(np.uint8)
    keep=cv2.morphologyEx(keep,cv2.MORPH_CLOSE,np.ones((11,11),np.uint8))
    soft=np.clip((S-0.30)/0.16,0,1)*np.clip((V-0.38)/0.14,0,1)*cv2.GaussianBlur(hue.astype(np.float32),(0,0),1.5)
    region=cv2.GaussianBlur(cv2.dilate(keep,np.ones((9,9),np.uint8)).astype(np.float32),(0,0),2)
    h=cv2.GaussianBlur(soft*region,(0,0),0.8)
    # bridge wrist: convex hull of hand + nearby body, keep only non-wall pixels inside it
    hb=(h>0.5).astype(np.uint8)
    if hb.sum()>500:
        ys=np.nonzero(hb)[0]; cyh=int(np.median(ys))
        hlow=hb.copy(); hlow[:cyh]=0
        near=cv2.dilate(hlow,np.ones((91,91),np.uint8))&(a>0.5).astype(np.uint8); near[:cyh]=0
        pts=cv2.findNonZero(hlow|near); hull=np.zeros_like(hb); cv2.fillConvexPoly(hull,cv2.convexHull(pts),1)
        hull=cv2.erode(hull,np.ones((5,5),np.uint8))
        wall=((S<0.36)&(V>0.33)).astype(np.float32)
        fill=cv2.GaussianBlur(hull.astype(np.float32)*(1-cv2.GaussianBlur(wall,(0,0),1.5)),(0,0),1.2)
        h=np.maximum(h,np.clip((fill-0.35)/0.4,0,1))
    out=np.maximum(a,h)
    cv2.imwrite(f'alpha_fix/{k:04d}.png',(out*65535).astype(np.uint16))
    print(k,int(keep.sum()))
