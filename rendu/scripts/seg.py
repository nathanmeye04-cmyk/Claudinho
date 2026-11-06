import sys,glob,os,time,numpy as np,cv2,torch
from transformers import SegformerImageProcessor, SegformerForSemanticSegmentation
torch.set_num_threads(4)
name='nvidia/segformer-b5-finetuned-ade-640-640'
proc=SegformerImageProcessor.from_pretrained(name); model=SegformerForSemanticSegmentation.from_pretrained(name).eval()
frames=[int(x) for x in sys.argv[1].split(',')] if len(sys.argv)>1 else range(1,346)
for k in frames:
    out=f'seg/{k:04d}.png'
    if os.path.exists(out): continue
    t=time.time(); im=cv2.imread(f'src/{k:04d}.png')[:,:,::-1].copy()
    x=proc(images=im,return_tensors='pt')
    with torch.no_grad(): lg=model(**x).logits
    lg=torch.nn.functional.interpolate(lg,size=im.shape[:2],mode='bilinear',align_corners=False)[0]
    pr=torch.softmax(lg,0)
    lab=pr.argmax(0).numpy().astype(np.uint8)
    np.save(f'seg/{k:04d}_p.npy',torch.stack([pr[0],pr[5],pr[3]]).numpy().astype(np.float16))  # wall, ceiling, floor probs
    cv2.imwrite(out,lab); print(k,round(time.time()-t,1),flush=True)
