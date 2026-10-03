"""Same-user launch metadata, never an owner-record store."""
import hashlib,json,os,secrets,subprocess,sys,tempfile,threading,time,urllib.request,webbrowser
from pathlib import Path
from http.server import ThreadingHTTPServer
RUNTIME_NONCE=secrets.token_urlsafe(20)
def metadata_path(identity,port):
    key=hashlib.sha256(json.dumps({'identity':identity,'requested_port':port},sort_keys=True).encode()).hexdigest()[:24]
    return Path(tempfile.gettempdir())/'cd-native-desks'/f'{key}.json'
def existing(identity,port):
    path=metadata_path(identity,port)
    try:
        meta=json.loads(path.read_text(encoding='utf-8'))
        if meta.get('identity')!=identity: return None
        endpoint=f"http://127.0.0.1:{int(meta['port'])}"
        with urllib.request.urlopen(endpoint+'/api/health',timeout=1) as response: health=json.load(response)
        if any(health.get(k)!=v for k,v in identity.items()) or health.get('instance')!=meta.get('instance'):return None
        if not isinstance(meta.get('token'),str) or len(meta['token'])<30:return None
        return {**meta,'url':endpoint+'/#session='+meta['token']}
    except (OSError,ValueError,KeyError,TypeError):return None

def launch(handler,args,identity,token,script):
    active=existing(identity,args.port)
    if active:
        print(json.dumps({'reconnected':True,**identity,'url':active['url']}),flush=True)
        if not args.no_browser:webbrowser.open(active['url'])
        return 0
    if os.name=='nt' and not args.no_browser and not args.serve:
        subprocess.Popen([sys.executable,'-B','-X','utf8',str(script),*sys.argv[1:],'--serve','--no-browser'],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW,close_fds=True)
        for _ in range(100):
            time.sleep(.1);active=existing(identity,args.port)
            if active:
                print(json.dumps({'started_detached':True,**identity,'url':active['url']}),flush=True);webbrowser.open(active['url']);return 0
        print('The local desk did not start. Run the same launcher with --no-browser to see the exact Python error.',file=sys.stderr);return 1
    try:server=ThreadingHTTPServer(('127.0.0.1',args.port),handler)
    except OSError:server=ThreadingHTTPServer(('127.0.0.1',0),handler)
    worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
    endpoint=f'http://127.0.0.1:{server.server_port}'
    with urllib.request.urlopen(endpoint+'/api/health',timeout=3) as response:health=json.load(response)
    if any(health.get(k)!=v for k,v in identity.items()) or health.get('instance')!=RUNTIME_NONCE:
        server.shutdown();server.server_close();raise RuntimeError('Local desk identity mismatch; browser not opened')
    path=metadata_path(identity,args.port);path.parent.mkdir(exist_ok=True)
    meta={'identity':identity,'instance':RUNTIME_NONCE,'pid':os.getpid(),'port':server.server_port,'token':token}
    temporary=path.with_suffix('.'+RUNTIME_NONCE+'.tmp')
    fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w',encoding='utf-8') as stream:json.dump(meta,stream)
    os.replace(temporary,path)
    if os.name!='nt':path.chmod(0o600)
    url=endpoint+'/#session='+token
    print(json.dumps({**identity,'url':url,'pid':os.getpid(),'runtime_metadata':str(path)}),flush=True)
    if not args.no_browser:webbrowser.open(url)
    try:worker.join()
    except KeyboardInterrupt:pass
    finally:
        server.shutdown();server.server_close()
        try:
            current=json.loads(path.read_text(encoding='utf-8'))
            if current.get('instance')==RUNTIME_NONCE:path.unlink()
        except (OSError,ValueError):pass
    return 0
