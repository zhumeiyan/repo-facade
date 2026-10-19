import json,os,base64,subprocess,sys,time
TK=open('/data/workspace/exp214_sample3k/.gh_token').read().strip()
REPO='repo-facade'; OWNER='zhumeiyan'
def api(m,u,body=None):
    c=['curl','-s','-m','30','-X',m,'-H','Authorization: token '+TK,
       '-H','Accept: application/vnd.github+json','https://api.github.com'+u]
    if body is not None: c+=['-d',json.dumps(body)]
    for _ in range(3):
        p=subprocess.run(c,capture_output=True,text=True)
        try: return json.loads(p.stdout)
        except Exception: time.sleep(2)
    return {}
r=api('POST','/user/repos',{'name':REPO,'public':True,'auto_init':False,
    'description':'Repo Facade — 给任意仓库生成一套活的状态立面（无面 / 零JS / 身份连续）'})
print('create:',r.get('full_name') or r.get('message'))
files={}
for root,dirs,fs in os.walk('/data/workspace/repo-facade'):
    dirs[:]=[d for d in dirs if d not in ('.git','__pycache__')]
    for f in fs:
        p=os.path.join(root,f)
        rel=os.path.relpath(p,'/data/workspace/repo-facade')
        if rel in ('.gh_token',) or rel.endswith('.pyc'): continue
        b=open(p,'rb').read()
        files[rel]={'content':base64.b64encode(b).decode()}
print('files:',len(files))
tree=api('GET',f'/repos/{OWNER}/{REPO}/git/refs/heads/main')
base=tree.get('object',{}).get('sha')
items=[{'path':k,'mode':'100644','type':'blob','sha':None} for k in files]
# 逐个用 contents API 提交（稳定，先传到 main）
ok=0
for k,v in files.items():
    v['message']='add '+k
    if base: v['branch']='main'
    r=api('PUT',f'/repos/{OWNER}/{REPO}/contents/{k}',v)
    if 'content' in r and r['content'].get('sha'): ok+=1
    else: print('FAIL',k,str(r)[:120])
print('pushed',ok,'/',len(files))
time.sleep(2)
pg=api('POST',f'/repos/{OWNER}/{REPO}/pages',{'source':{'branch':'main','path':'/'}})
print('pages:',pg.get('status') or pg.get('message') or 'enabled')
