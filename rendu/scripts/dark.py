import numpy as np,cv2
def darkness(i):
    I=cv2.imread(f'src/{i:04d}.png').astype(np.float32)/255
    L=cv2.cvtColor(I,cv2.COLOR_BGR2GRAY)
    a=cv2.imread(f'alpha_fix/{i:04d}.png',-1)/65535.
    Ls=cv2.GaussianBlur(L,(0,0),3)
    ref=cv2.GaussianBlur(cv2.dilate(Ls,np.ones((91,91),np.uint8)),(0,0),45)
    D=np.clip(1-Ls/(ref+1e-4),0,1)
    gx=cv2.Sobel(Ls,cv2.CV_32F,1,0,ksize=3); gy=cv2.Sobel(Ls,cv2.CV_32F,0,1,ksize=3)
    tex=cv2.GaussianBlur(np.sqrt(gx*gx+gy*gy),(0,0),6)
    Wt=np.exp(-(tex/0.025)**2)                     # plain-wall weight (furniture has strong edges)
    Wt*= (cv2.GaussianBlur(L,(0,0),4)>0.28)        # very dark objects are not shadow
    Wt*= 1-np.clip(cv2.dilate((a>0.03).astype(np.uint8),np.ones((25,25),np.uint8)),0,1)
    return D,Wt,a
if __name__=='__main__':
    r=[]
    for i in (1,60,115,286,305,330):
        D,Wt,a=darkness(i)
        r.append(cv2.resize(np.hstack([cv2.imread(f'src/{i:04d}.png'),cv2.cvtColor((np.clip(D*Wt*3,0,1)*255).astype(np.uint8),cv2.COLOR_GRAY2BGR)]),(1024,288)))
    cv2.imwrite('peek/d.jpg',np.vstack([np.hstack(r[k:k+2]) for k in (0,2,4)]))
