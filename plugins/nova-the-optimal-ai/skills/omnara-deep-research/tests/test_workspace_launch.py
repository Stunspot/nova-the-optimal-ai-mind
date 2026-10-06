import json,os,signal,socket,subprocess,sys,tempfile,unittest,urllib.request,urllib.error
from pathlib import Path
OPEN=Path(__file__).parents[1]/'workspace'/'open.py'
class LauncherTests(unittest.TestCase):
    def test_collision_identity_access_repeat_and_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); occupied=socket.socket();occupied.bind(('127.0.0.1',0));occupied.listen()
            port=occupied.getsockname()[1]
            command=[sys.executable,'-B',str(OPEN),'--no-browser','--data-root',tmp,'--port',str(port)]
            record=None
            try:
                first=subprocess.check_output(command,text=True,timeout=20).strip()
                record=json.loads(next((root/'.workspace').glob('instance-*.json')).read_text())
                self.assertNotEqual(int(record['url'].rsplit(':',1)[1]),port)
                self.assertEqual(subprocess.check_output(command,text=True,timeout=20).strip(),first)
                def request(action,data=None,headers=None):
                    req=urllib.request.Request(record['url']+'/api/'+action,json.dumps(data or {}).encode(),{'Content-Type':'application/json',**(headers or {})})
                    with urllib.request.urlopen(req,timeout=5) as response:return json.load(response)
                with self.assertRaises(urllib.error.HTTPError) as e:request('list')
                self.assertEqual(e.exception.code,403)
                with self.assertRaises(urllib.error.HTTPError):request('list',headers={'X-Workspace-Token':record['token'],'Origin':'https://example.invalid'})
                with self.assertRaises(urllib.error.HTTPError):request('list',headers={'X-Workspace-Token':record['token'],'Host':'example.invalid'})
                token={'X-Workspace-Token':record['token']}
                vault=request('create',{'title':'Restart fixture','question':'What survives a process restart?'},token)
                os.kill(record['pid'],signal.SIGTERM);record=None
                second=subprocess.check_output(command,text=True,timeout=20).strip()
                record=json.loads(next((root/'.workspace').glob('instance-*.json')).read_text())
                self.assertNotEqual(first,second)
                reopened=request('load',{'key':vault['key']},{'X-Workspace-Token':record['token']})
                self.assertEqual(reopened['files'],vault['files'])
            finally:
                occupied.close()
                if record:
                    try:os.kill(record['pid'],signal.SIGTERM)
                    except OSError:pass
