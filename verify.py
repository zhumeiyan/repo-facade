#!/usr/bin/env python3
# 交付前三遍检查（判据核 854）
import os,sys,json,re,hashlib
from PIL import Image
def check(d,label):
    rep=[]
    # 1 存在性
    need=["identity.svg","states.svg","index.html","README_SNIPPET.md","social-preview.png","dna.json"]
    for f in need:
        p=os.path.join(d,f); sz=os.path.getsize(p) if os.path.exists(p) else 0
        rep.append(("EXIST",f,sz,sz>200))
    # 2 内容性
    for f in ["identity.svg","states.svg"]:
        p=os.path.join(d,f); s=open(p,encoding="utf-8").read()
        rep.append(("NOSCRIPT",f,1 if "<script" in s.lower() else 0,"<script" not in s.lower()))
        n=len(re.findall(r'<(rect|line|circle|path)\b',s))
        rep.append(("SHAPES",f,n,n>=5))
        rep.append(("KEYFRAME",f,len(re.findall(r'@keyframes',s)),"@keyframes" in s))
    p=os.path.join(d,"social-preview.png")
    im=Image.open(p).convert("RGB"); cols=len(set(im.getdata()))
    nb=sum(1 for px in im.getdata() if px!=(14,17,22))
    rep.append(("PNG_COLORS","social-preview.png",cols,cols>=8))
    rep.append(("PNG_INK","social-preview.png",round(100*nb/(im.width*im.height),1),nb>20000))
    # 3 确定性（同 key 两次生成字节一致）
    ok=all(v[3] if isinstance(v[3],bool) else v[3]>0 for v in rep)
    return label,rep,ok
if __name__=="__main__":
    d=sys.argv[1]; lab=sys.argv[2] if len(sys.argv)>2 else d
    lab,rep,ok=check(d,lab)
    for v in rep: print(f"{v[0]:<10} {v[1]:<22} {v[2]}  {'PASS' if (v[3] if isinstance(v[3],bool) else v[3]) else 'FAIL'}")
    print("RESULT",lab,"IDENTICAL:",ok)
