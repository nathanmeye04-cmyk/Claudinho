import numpy as np,cv2,shutil,glob,os
def box(x,r): return cv2.boxFilter(x,-1,(2*r+1,2*r+1))
def guided(I,p,r,eps):
    mI,mp=box(I,r),box(p,r); cov=box(I*p,r)-mI*mp; var=box(I*I,r)-mI*mI
    a=cov/(var+eps); b=mp-a*mI; return box(a,r)*I+box(b,r)
for f in sorted(glob.glob('alpha/*.png')): shutil.copy(f,'alpha_fix/'+os.path.basename(f))
for i in range(283,346):
    out=f'alpha_fix/{i:04d}.png'
    if i>=319: cv2.imwrite(out,np.zeros((576,1024),np.uint16)); continue
    I=cv2.cvtColor(cv2.imread(f'src/{i:04d}.png'),cv2.COLOR_BGR2GRAY).astype(np.float32)/255
    u=cv2.imread(f'u2m/{i:04d}.png',0).astype(np.float32)/255
    dark=(cv2.GaussianBlur(I,(0,0),3)<0.30).astype(np.uint8)
    seed=((u>0.5)|((dark>0)&((i>=314)|(i in (309,311))))).astype(np.uint8)
    n,lab,st,_=cv2.connectedComponentsWithStats(seed)
    keep=np.zeros_like(seed)
    for k in range(1,n):
        x,y,w,h,area=st[k]
        if x+w>=1020 and area>1500 and (i<314 or x>780) and (i not in (309,311) or x>500): keep|=(lab==k).astype(np.uint8)
    keep=cv2.morphologyEx(keep,cv2.MORPH_CLOSE,np.ones((15,15),np.uint8))
    a=guided(I,keep.astype(np.float32),12,1e-3)
    a=np.clip((a-0.15)/0.7,0,1)
    core=cv2.GaussianBlur(cv2.erode(keep,np.ones((19,19),np.uint8)).astype(np.float32),(0,0),3)
    if i<295:
        b=cv2.imread(f'alpha/{i:04d}.png',-1)/65535.
        a=np.maximum(b,core)          # BiRefNet edges, solid interior
    else:
        a=np.maximum(a,core)
    cv2.imwrite(out,(a*65535).astype(np.uint16))
