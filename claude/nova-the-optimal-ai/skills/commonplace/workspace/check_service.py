"""Optional read-only current-estate service smoke test, no personal output."""
import argparse,json,subprocess,sys,urllib.request,urllib.error,socket
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
parser=argparse.ArgumentParser();parser.add_argument('--nova-operations',required=True);parser.add_argument('--estate-root',required=True);args=parser.parse_args()
root=Path(__file__).resolve().parent
with socket.socket() as available:available.bind(('127.0.0.1',0));port=available.getsockname()[1]
command=[sys.executable,'-B','-X','utf8',str(root/'host.py'),'--nova-operations',args.nova_operations,'--estate-root',args.estate_root,'--port',str(port),'--no-browser']
process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8')
try:
 line=process.stdout.readline()
 if not line:raise RuntimeError(process.stderr.read())
 receipt=json.loads(line);parts=urlsplit(receipt['url']);base=f'{parts.scheme}://{parts.netloc}';token=parse_qs(parts.fragment)['session'][0]
 def post(body,origin=None):
  headers={'Content-Type':'application/json','X-Desk-Token':token}
  if origin:headers['Origin']=origin
  return urllib.request.urlopen(urllib.request.Request(base+'/api/read',data=json.dumps(body).encode(),headers=headers),timeout=30)
 with urllib.request.urlopen(base+'/api/health',timeout=3) as response:health=json.load(response)
 assert 'token' not in health and health['read_only'] and health['estate']==str(Path(args.estate_root).resolve()) and health['operations']==str(Path(args.nova_operations).resolve())
 with urllib.request.urlopen(urllib.request.Request(base+'/api/session',data=b'{}',headers={'X-Desk-Token':token}),timeout=3) as response:cookie=response.headers['Set-Cookie']
 assert 'HttpOnly' in cookie and 'SameSite=Strict' in cookie
 with urllib.request.urlopen(urllib.request.Request(base+'/api/session',headers={'Cookie':cookie.split(';',1)[0]}),timeout=3) as response:assert json.load(response)['authenticated']
 with urllib.request.urlopen(base+'/',timeout=3) as response:
  assert 'charset=utf-8' in response.headers['Content-Type'];html=response.read().decode('utf-8');assert 'Â·' not in html and 'â€”' not in html
 with post({'action':'status'}) as response:state=json.load(response)
 assert state['read_only'] and 'native' in state
 try:post({'action':'capture','body':'not a real note'})
 except urllib.error.HTTPError as error:assert error.code==400
 else:raise AssertionError('Mutation command was admitted')
 try:post({'action':'status'},origin='https://untrusted.example')
 except urllib.error.HTTPError as error:assert error.code==403
 else:raise AssertionError('Cross-origin read was admitted')
 second=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',timeout=5);reconnected=json.loads(second.stdout);assert reconnected['reconnected'] and reconnected['url']==receipt['url']
 print(json.dumps({'service':'nova-knowledge-desk','health_identity':'passed','session_origin':'passed','mutation_refusal':'passed','reconnect':'passed','native_status_exit':state['exit_code'],'record_contents_emitted':False}))
finally:
 process.terminate();process.wait(timeout=5)
