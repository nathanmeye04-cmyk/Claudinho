import glob,os,time,numpy as np,cv2,onnxruntime as ort
so=ort.SessionOptions(); so.enable_cpu_mem_arena=False; so.enable_mem_pattern=False; so.intra_op_num_threads=4
s=ort.InferenceSession('/root/.rembg/models/birefnet-general/birefnet-general.onnx',so,providers=['CPUExecutionProvider'])
mean=np.array([.485,.456,.406],np.float32); std=np.array([.229,.224,.225],np.float32)
for f in sorted(glob.glob('src/*.png')):
    out='alpha/'+os.path.basename(f)
    if os.path.exists(out): continue
    t=time.time(); im=cv2.imread(f)[:,:,::-1]; h,w=im.shape[:2]
    x=cv2.resize(im,(1024,1024),interpolation=cv2.INTER_AREA).astype(np.float32)/255
    x=((x-mean)/std).transpose(2,0,1)[None]
    p=s.run(None,{'input_image':x})[0][0,0]; p=1/(1+np.exp(-p))
    a=cv2.resize(p,(w,h),interpolation=cv2.INTER_CUBIC).clip(0,1)
    cv2.imwrite(out,(a*65535).round().astype(np.uint16)); print(out,round(time.time()-t,1),flush=True)
