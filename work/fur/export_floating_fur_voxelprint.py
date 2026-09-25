from __future__ import annotations
import hashlib,json,math,shutil
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[2]; OUT=ROOT/"work/fur/floating_fur_voxelprint_staging"; CACHE=ROOT/"work/fur/floating_fur_native_labels.dat"
SEED=77171; DSEED=np.uint32(20260903); PX,PY,PZ=.0254/600,.0254/300,.014e-3; W,H,NZ=math.ceil(.060/PX-1e-6),math.ceil(.030/PY-1e-6),math.ceil(.005/PZ-1e-6)
RES=[("VeroPureWht",(240,240,240)),("VeroBlack_or_VeroFlexBK",(26,26,29)),("VeroClear_or_VeroFlexCLR",(227,233,253)),("VeroCyan_or_VeroFlexCY",(0,90,158)),("VeroMgnt_or_VeroFlexMGT",(166,33,98)),("VeroYellow_or_VeroFlexYL",(200,189,3))]
REC={1:[0,0,1,0,0,0],2:[.18,0,.82,0,0,0],3:[.32,0,.68,0,0,0],4:[.48,0,.52,0,0,0],5:[.25,.015,.735,0,0,0],6:[.10,.055,.845,0,0,0],7:[.06,.10,.84,0,0,0]}
NAMES={1:"透明母材",2:"半透明白／下毛",3:"柔らかい白毛",4:"明るい白毛",5:"銀白毛",6:"半透明チャコール毛",7:"半透明黒毛"}
def sha(p):
 h=hashlib.sha256()
 with Path(p).open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def noise(x,y,z):
 with np.errstate(over="ignore"):
  q=x.astype(np.uint32)*np.uint32(0x9E3779B1)^y.astype(np.uint32)*np.uint32(0x85EBCA77)^np.uint32(z)*np.uint32(0xC2B2AE3D)^DSEED;q^=q>>np.uint32(16);q*=np.uint32(0x7FEB352D);q^=q>>np.uint32(15);q*=np.uint32(0x846CA68B);q^=q>>np.uint32(16)
 return(q.astype(float)+.5)/4294967296
def draw(vol,p,d,mid):
 maxr=d.max()/2
 for oz in range(-math.ceil(maxr/(PZ*1000)),math.ceil(maxr/(PZ*1000))+1):
  for oy in range(-math.ceil(maxr/(PY*1000)),math.ceil(maxr/(PY*1000))+1):
   for ox in range(-math.ceil(maxr/(PX*1000)),math.ceil(maxr/(PX*1000))+1):
    keep=(ox*PX*1000)**2+(oy*PY*1000)**2+(oz*PZ*1000)**2<=(d/2)**2
    if not keep.any():continue
    a=p[keep];ix=np.floor(a[:,0]/(PX*1000)).astype(int)+ox;iy=np.floor(a[:,1]/(PY*1000)).astype(int)+oy;iz=np.floor(a[:,2]/(PZ*1000)).astype(int)+oz;v=(ix>=0)&(ix<W)&(iy>=0)&(iy<H)&(iz>=0)&(iz<NZ);vol[iz[v],iy[v],ix[v]]=mid
def hairs():
 rng=np.random.default_rng(SEED);v=np.memmap(CACHE,dtype=np.uint8,mode="w+",shape=(NZ,H,W));v[:]=0;darkn=0
 for _ in range(6800):
  face=int(rng.choice(6,p=[.08,.08,.28,.28,.14,.14]));r=np.array([rng.uniform(5,53),rng.uniform(5,25),rng.uniform(1.15,3.85)]);n=np.zeros(3)
  if face==0:r[0],n[0]=rng.uniform(5,8),-1
  elif face==1:r[0],n[0]=rng.uniform(50,53),1
  elif face==2:r[1],n[1]=rng.uniform(5,7),-1
  elif face==3:r[1],n[1]=rng.uniform(23,25),1
  elif face==4:r[2],n[2]=rng.uniform(1.15,1.35),-1
  else:r[2],n[2]=rng.uniform(3.65,3.85),1
  sx=1 if rng.random()<.82 else-1;f=np.array([sx,rng.normal(0,.34),rng.normal(0,.16)]);f/=np.linalg.norm(f);L=rng.uniform(.8,3.2)if face<4 else rng.uniform(.4,1);ph=rng.uniform(0,2*np.pi);t=np.linspace(0,1,max(8,int(L/.009)));b=t*t*(3-2*t);dire=(1-b[:,None])*n+b[:,None]*f;tr=np.c_[.11*np.sin(ph+5.7*t),.32*np.sin(ph+7.2*t)+.10*np.sin(ph*1.7+17*t),.13*np.cos(ph*.7+8.1*t)];p=np.clip(r+L*t[:,None]*dire+tr,[.65,.65,.65],[59.35,29.35,4.35]);dark=rng.random()<.15;darkn+=dark;mid=(7 if rng.random()<.28 else 6)if dark else int(rng.choice([2,3,4,5],p=[.18,.34,.31,.17]));rd=rng.uniform(.10,.16);draw(v,p,rd+(.06-rd)*t,mid)
 v.flush();return v,darkn
def main():
 if OUT.exists():shutil.rmtree(OUT)
 OUT.mkdir(parents=True);hair,darkn=hairs();xs=(np.arange(W)+.5)*PX*1000;ys=(np.arange(H)+.5)*PY*1000;xx,yy=np.meshgrid(xs,ys);gx=np.broadcast_to(np.arange(W,dtype=np.uint32)[None,:],(H,W));gy=np.broadcast_to(np.arange(H,dtype=np.uint32)[:,None],(H,W));rgba=np.asarray([(0,0,0,0),*((*rgb,255)for _,rgb in RES)],dtype=np.uint8);thr={k:np.cumsum(v)for k,v in REC.items()};counts=np.zeros(7,dtype=np.int64);records=[]
 for zi in range(NZ):
  z=(zi+.5)*PZ*1000;core=(np.abs((xx-29)/25)**6+np.abs((yy-15)/10.4)**6+abs((z-2.5)/1.35)**6<1)&(np.sin(xx*2.1+yy*1.3+z*4.7)+np.sin(xx*.43-yy*1.8)>1.25);sem=np.ones((H,W),np.uint8);sem[core]=2;hm=np.asarray(hair[zi]);sem[hm>0]=hm[hm>0];u=noise(gx,gy,zi);idx=np.zeros((H,W),np.uint8)
  for mid,q in thr.items():m=sem==mid;idx[m]=np.searchsorted(q,u[m],side="right").astype(np.uint8)+1
  fn=f"slice_{zi:04d}.png";p=OUT/fn;im=Image.fromarray(rgba[idx],mode="RGBA");im.save(p,compress_level=9);counts+=np.bincount(idx.ravel(),minlength=7);records.append({"file":fn,"sha256":sha(p)})
 man={"format":"vdbmat.print-slices","format_version":"1.0.0","name":"floating_fur","source":{"generator":"pj-voxel3dprint.floating-fur-native-print","seed":SEED,"hair_tip_diameter_mm":.06,"hair_root_diameter_mm_range":[.10,.16],"dark_strand_fraction":darkn/6800},"printer":{"profile":"Stratasys J750 PNG method High Quality","dpi_x":600.,"dpi_y":300.,"pitch_x_mm":PX*1000,"pitch_y_mm":PY*1000,"layer_thickness_mm":PZ*1000},"grid":{"width_px":W,"height_px":H,"slice_count":NZ,"physical_mm":{"x":W*PX*1000,"y":H*PY*1000,"z":NZ*PZ*1000}},"palette":{str(i):{"material":n,"rgb":list(rgb),"voxel_count":int(counts[i])}for i,(n,rgb)in enumerate(RES,1)},"halftone":{"method":"deterministic-3d-hash","recipes_by_material_id":REC},"slices":records};(OUT/"floating_fur.printslices.json").write_text(json.dumps(man,indent=2)+"\n",encoding="utf-8");(OUT/"floating_fur.resin-recipes.json").write_text(json.dumps({"resin_order":[x[0]for x in RES],"material_names":NAMES,"recipes_by_material_id":REC},indent=2,ensure_ascii=False)+"\n",encoding="utf-8");memo=["# floating_fur — Stratasys Voxel Print 材料対応メモ","",f"- X: 600 DPI ({PX*1000:.6f} mm/px)",f"- Y: 300 DPI ({PY*1000:.6f} mm/px)","- 積層: 0.014 mm",f"- PNG: {W} × {H} px、{NZ}層","- PNG: 32-bit RGBA（各8 bit、Alpha=255）","- 毛先直径: 0.060 mm（プリンタ格子へ直接描画）","- 根元直径: 0.10〜0.16 mm","- 黒系毛束: 約15%","","|Index|RGB|GrabCAD想定材料|","|---:|---|---|"]+[f"|{i}|{rgb[0]}, {rgb[1]}, {rgb[2]}|{n}|"for i,(n,rgb)in enumerate(RES,1)];(OUT/"材料対応メモ.md").write_text("\n".join(memo)+"\n",encoding="utf-8");print(json.dumps({"width":W,"height":H,"slices":NZ,"dark_strands":darkn,"counts":counts.tolist()}))
if __name__=="__main__":main()
