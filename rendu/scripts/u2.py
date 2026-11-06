import glob,os,numpy as np,cv2,onnxruntime as ort
so=ort.SessionOptions(); so.intra_op_num_threads=1
s=ort.InferenceSession('/root/.rembg/models/u2net_human_seg/u2net_human_seg.onnx' if os.path.exists('/root/.rembg/models/u2net_human_seg/u2net_human_seg.onnx') else '/root/.u2net/u2net_human_seg.onnx',so)
mean=np.array([.485,.456,.406],np.float32); std=np.array([.229,.224,.225],np.float32)
n=s.get_inputs()[0].name
for f in sorted(glob.glob('src/*.png')):
    im=cv2.imread(f)[:,:,::-1]; h,w=im.shape[:2]
    x=((cv2.resize(im,(320,320)).astype(np.float32)/255-mean)/std).transpose(2,0,1)[None]
    p=s.run(None,{n:x})[0][0,0]; p=(p-p.min())/(p.max()-p.min()+1e-6)
    cv2.imwrite('u2m/'+os.path.basename(f),(cv2.resize(p,(w,h))*255).astype(np.uint8))
