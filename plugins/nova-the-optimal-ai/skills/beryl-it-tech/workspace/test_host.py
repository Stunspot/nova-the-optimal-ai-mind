"""Checks native validation and actual private-loopback/reconnect boundaries."""
import json,subprocess,sys,unittest,urllib.request,urllib.error,socket
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
ROOT=Path(__file__).resolve().parent
class DeskTest(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  with socket.socket() as available:available.bind(('127.0.0.1',0));port=available.getsockname()[1]
  cls.command=[sys.executable,'-B','-X','utf8',str(ROOT/'host.py'),'--no-browser','--port',str(port)]
  cls.process=subprocess.Popen(cls.command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8')
  cls.receipt=json.loads(cls.process.stdout.readline());parts=urlsplit(cls.receipt['url']);cls.base=f'{parts.scheme}://{parts.netloc}';cls.token=parse_qs(parts.fragment)['session'][0]
 @classmethod
 def tearDownClass(cls):
  cls.process.terminate();cls.process.wait(timeout=5);cls.process.stdout.close();cls.process.stderr.close()
 def request(self,path,body=None,token=True,origin=None):
  headers={'Content-Type':'application/json'}
  if token:headers['X-Desk-Token']=self.token
  if origin:headers['Origin']=origin
  return urllib.request.urlopen(urllib.request.Request(self.base+path,data=json.dumps(body).encode() if body is not None else None,headers=headers),timeout=20)
 def test_native_valid_invalid_unknown_fields(self):
  with self.request('/api/sample') as response:sample=json.load(response)
  sample['owner_extra']={'must':'survive'}
  with self.request('/api/validate',sample) as response:self.assertTrue(json.load(response)['valid'])
  sample['status']='invented' if 'case_id' in sample else sample.get('status')
  if 'baseline' in sample:sample['baseline']['authority']='pretend_approved'
  with self.request('/api/validate',sample) as response:self.assertFalse(json.load(response)['valid'])
 def test_private_sample_and_cross_origin(self):
  with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/sample',token=False)
  self.assertEqual(error.exception.code,403);error.exception.close()
  with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/validate',{},origin='https://untrusted.example')
  self.assertEqual(error.exception.code,403);error.exception.close()
 def test_no_save_endpoint(self):
  with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/save',{})
  self.assertEqual(error.exception.code,404);error.exception.close()
 def test_reload_with_httponly_credential(self):
  with self.request('/api/session',{}) as response:cookie=response.headers['Set-Cookie']
  self.assertIn('HttpOnly',cookie);self.assertIn('SameSite=Strict',cookie)
  request=urllib.request.Request(self.base+'/api/session',headers={'Cookie':cookie.split(';',1)[0]})
  with urllib.request.urlopen(request,timeout=3) as response:self.assertTrue(json.load(response)['authenticated'])
  with urllib.request.urlopen(urllib.request.Request(self.base+'/api/sample',headers={'Cookie':cookie.split(';',1)[0]}),timeout=3) as response:self.assertIsInstance(json.load(response),dict)
  with urllib.request.urlopen(self.base+'/',timeout=3) as response:
   self.assertIn('charset=utf-8',response.headers['Content-Type']);html=response.read().decode('utf-8');self.assertNotIn('Â·',html);self.assertNotIn('â€”',html)
 def test_simultaneous_cookie_isolation(self):
  with self.request('/api/session',{}) as response:first=response.headers['Set-Cookie'].split(';',1)[0]
  with socket.socket() as available:available.bind(('127.0.0.1',0));port=available.getsockname()[1]
  command=self.command[:-1]+[str(port)]
  child=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8')
  try:
   receipt=json.loads(child.stdout.readline());parts=urlsplit(receipt['url']);base=f'{parts.scheme}://{parts.netloc}';token=parse_qs(parts.fragment)['session'][0]
   with urllib.request.urlopen(urllib.request.Request(base+'/api/session',data=b'{}',headers={'X-Desk-Token':token}),timeout=3) as response:second=response.headers['Set-Cookie'].split(';',1)[0]
   self.assertNotEqual(first.split('=',1)[0],second.split('=',1)[0])
   both=first+'; '+second
   for endpoint in (self.base,base):
    with urllib.request.urlopen(urllib.request.Request(endpoint+'/api/session',headers={'Cookie':both}),timeout=3) as response:self.assertTrue(json.load(response)['authenticated'])
   with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(urllib.request.Request(base+'/api/session',headers={'Cookie':first}),timeout=3)
   error.exception.close()
   self.assertEqual(error.exception.code,403);error.exception.close()
  finally:child.terminate();child.wait(timeout=5);child.stdout.close();child.stderr.close()
 def test_identity_reconnect_and_health_no_token(self):
  with self.request('/api/health',token=False) as response:health=json.load(response)
  self.assertNotIn('token',health);self.assertEqual(health['workspace'],str(ROOT))
  second=subprocess.run(self.command,capture_output=True,text=True,encoding='utf-8',timeout=5)
  reconnect=json.loads(second.stdout);self.assertTrue(reconnect['reconnected']);self.assertEqual(reconnect['url'],self.receipt['url'])
 def test_occupied_port_uses_private_fallback_and_reconnects(self):
  from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
  import threading
  class Occupied(BaseHTTPRequestHandler):
   def log_message(self,*args):pass
   def do_GET(self):
    self.send_response(200);self.end_headers();self.wfile.write(b'{}')
  occupied=ThreadingHTTPServer(('127.0.0.1',0),Occupied)
  worker=threading.Thread(target=occupied.serve_forever,daemon=True);worker.start()
  command=self.command[:-1]+[str(occupied.server_port)]
  child=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8')
  timeout=threading.Timer(8,child.terminate);timeout.start()
  try:
   line=child.stdout.readline()
   if not line:
    child.wait(timeout=2);self.fail('Launcher produced no receipt for occupied port: '+child.stderr.read())
   receipt=json.loads(line);parts=urlsplit(receipt['url'])
   self.assertNotEqual(parts.port,occupied.server_port)
   with urllib.request.urlopen(f'{parts.scheme}://{parts.netloc}/api/health',timeout=3) as response:
    health=json.load(response);self.assertEqual(health['runtime_sha256'],receipt['runtime_sha256'])
   second=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',timeout=5)
   reconnect=json.loads(second.stdout);self.assertTrue(reconnect['reconnected']);self.assertEqual(reconnect['url'],receipt['url'])
  finally:
   timeout.cancel();child.terminate();child.wait(timeout=5);child.stdout.close();child.stderr.close();occupied.shutdown();occupied.server_close();worker.join(timeout=3)
 def test_theme_assets_are_exact_and_routes_are_allowlisted(self):
  for skin in ('moss','night','porcelain'):
   with self.request('/assets/'+skin+'-surface.png',token=False) as response:
    expected=(ROOT/'assets'/(skin+'-surface.png')).read_bytes()
    self.assertEqual(response.headers['Content-Type'],'image/png')
    self.assertEqual(int(response.headers['Content-Length']),len(expected))
    self.assertEqual(response.read(),expected)
  for path in ('/assets/host.py','/assets/../host.py','/assets/missing.png'):
   with self.assertRaises(urllib.error.HTTPError) as error:self.request(path)
   self.assertEqual(error.exception.code,404);error.exception.close()
if __name__=='__main__':unittest.main()
