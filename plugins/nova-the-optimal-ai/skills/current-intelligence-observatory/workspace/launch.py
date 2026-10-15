"""Start or reconnect to the local app, preserving work outside installed files."""
import argparse,hashlib,json,os,subprocess,sys,tempfile,time,urllib.request,webbrowser
from pathlib import Path
sys.dont_write_bytecode=True
from work_io import select_home
ROOT=Path(__file__).resolve().parent
PRODUCT='current-intelligence-observatory'

def main():
 p=argparse.ArgumentParser();p.add_argument('--no-browser',action='store_true');p.add_argument('--data-home',type=Path);p.add_argument('--port',type=int,default=0);a=p.parse_args()
 base=Path(os.environ.get('LOCALAPPDATA',str(Path.home()/'.local/share')))/'Collaborative Dynamics'/PRODUCT
 root=select_home(PRODUCT,base,a.data_home)
 identity=hashlib.sha256((str(ROOT)+str(root)).encode()+b''.join((ROOT/n).read_bytes() for n in ['launch.py','work-host.py','work_io.py'])).hexdigest()[:16]
 run=Path(tempfile.gettempdir())/('cd-app-'+identity+'.json')
 result=None
 if run.exists():
  try:
   old=json.loads(run.read_text('utf-8'));health=json.load(urllib.request.urlopen(old['url']+'health',timeout=1))
   if health.get('product')==PRODUCT and health.get('source')==str(ROOT):result=old
  except Exception:pass
 if result is None:
  ready=Path(tempfile.gettempdir())/('cd-ready-'+os.urandom(10).hex()+'.json')
  log=open(root/'.app-host.log','ab')
  proc=subprocess.Popen([sys.executable,'-B',str(ROOT/'work-host.py'),'--data-home',str(root),'--port',str(a.port),'--ready-file',str(ready)],stdin=subprocess.DEVNULL,stdout=log,stderr=log,creationflags=(0x08000000|0x00000008 if os.name=='nt' else 0),start_new_session=os.name!='nt');log.close()
  for _ in range(100):
   if ready.exists():
    try:result=json.loads(ready.read_text('utf-8'));break
    except ValueError:pass
   if proc.poll() is not None:raise SystemExit('The app could not start. See '+str(root/'.app-host.log'))
   time.sleep(.05)
  if result is None:raise SystemExit('The app did not finish starting. See '+str(root/'.app-host.log'))
  ready.unlink(missing_ok=True);run.write_text(json.dumps(result),encoding='utf-8')
 if not a.no_browser:webbrowser.open(result['url'])
 print(json.dumps(result),flush=True)
if __name__=='__main__':main()
