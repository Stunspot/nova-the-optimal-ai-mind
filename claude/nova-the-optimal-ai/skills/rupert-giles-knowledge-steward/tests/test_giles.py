import copy, importlib.util, json, os, sys, tempfile, threading, unittest, urllib.request, urllib.error
from pathlib import Path
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('giles',Path(__file__).resolve().parents[1]/'scripts/giles.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)

def row(root):
    return {'id':'stooges','name':'Three Stooges Knowledge Archive','summary':'A fictional fixture of comedy history, not an actual owned archive.','location':str(root),'kind':'folder','role':'unresolved','lifecycle':'retained','inspection':'description_reviewed','aliases':['Moe Larry Curly'],'topics':['comedy','film'],'use_when':['Compare the Shemp era'],'entrypoint':'INDEX.md','provenance':'Synthetic test fixture','owner':'Test','favorite':False,'sections':[{'id':'shemp','title':'Shemp Studies','path':'Shemp Studies/README.md','summary':'Film chronology and biography','topics':['Shemp']}]}
def document(root): return g.validate({'schema':g.SCHEMA,'revision':0,'stores':[row(root)]})

class Core(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.source=self.root/'source';self.source.mkdir();(self.source/'INDEX.md').write_text('Source index — café 💠',encoding='utf-8');(self.source/'Shemp Studies').mkdir();(self.source/'Shemp Studies/README.md').write_text('Shemp chronology: 1947–1955.\n',encoding='utf-8',newline='\n');self.path=self.root/'catalog/catalog.json';self.cat=g.Catalog(self.path);self.doc=document(self.source)
    def test_read_does_not_initialize(self): self.assertEqual(self.cat.read(),g.empty());self.assertFalse(self.path.parent.exists())
    def test_exact_persistence_roundtrip_unicode(self):
        self.doc['stores'][0]['summary']='Read café, 世界 and 💠';saved=self.cat.save(self.doc,0);self.assertEqual(g.Catalog(self.path).read(),saved);self.assertEqual(saved['revision'],1);self.assertEqual(saved['stores'][0]['summary'],'Read café, 世界 and 💠')
    def test_conflicting_save_preserves_newer_record(self):
        first=self.cat.save(self.doc,0);new=copy.deepcopy(first);new['stores'][0]['summary']='New evidence';self.cat.save(new,1)
        with self.assertRaises(g.Conflict): self.cat.save(first,1)
        self.assertEqual(self.cat.read()['stores'][0]['summary'],'New evidence')
    def test_process_lock_prevents_second_writer(self):
        with g.process_lock(self.path.with_suffix('.lock')):
            with self.assertRaises(g.Conflict): g.Catalog(self.path).save(self.doc,0)
        self.assertFalse(self.path.exists())
    def test_atomic_write_failure_preserves_original(self):
        saved=self.cat.save(self.doc,0);new=copy.deepcopy(saved);new['stores'][0]['summary']='Should not land'
        with patch.object(g.os,'replace',side_effect=OSError('simulated disk failure')):
            with self.assertRaises(OSError):self.cat.save(new,1)
        self.assertEqual(self.cat.read(),saved);self.assertEqual(list(self.path.parent.glob('*.tmp')),[])
    def test_import_export_merge_roundtrip(self):
        saved=self.cat.save(self.doc,0);restored=g.Catalog(self.root/'restored.json').merge(json.loads(json.dumps(saved,ensure_ascii=False)),0);self.assertEqual(restored['stores'],saved['stores'])
    def test_conflicting_import_is_atomic(self):
        old=self.cat.save(self.doc,0);incoming=copy.deepcopy(old);incoming['stores'][0]['name']='A conflicting name'
        with self.assertRaises(g.CatalogError):self.cat.merge(incoming,1)
        self.assertEqual(self.cat.read(),old)
        replaced=self.cat.merge(incoming,1,True);self.assertEqual(replaced['stores'][0]['name'],'A conflicting name')
    def test_invalid_import_does_not_create_catalog(self):
        bad=copy.deepcopy(self.doc);bad['stores'][0]['sections'][0]['path']='../secret.md'
        with self.assertRaises(g.CatalogError):self.cat.merge(bad,0)
        self.assertFalse(self.path.exists())
    def test_ids_types_roles_and_unknown_fields(self):
        for transform in [lambda d:d['stores'].append(copy.deepcopy(d['stores'][0])),lambda d:d.update(revision=True),lambda d:d['stores'][0].update(favorite='yes'),lambda d:d['stores'][0].update(role='latest'),lambda d:d['stores'][0].update(executable='delete sources')]:
            d=copy.deepcopy(self.doc);transform(d)
            with self.assertRaises(g.CatalogError):g.validate(d)
    def test_cli_unicode_survives_windows_default_encoding(self):
        import subprocess
        d=copy.deepcopy(self.doc);d['stores'][0]['name']='Café 世界 💠';self.cat.save(d,0)
        env=dict(os.environ,PYTHONIOENCODING='cp1252')
        result=subprocess.run([sys.executable,'-B',str(g.ROOT/'scripts/giles.py'),'--catalog',str(self.path),'list'],capture_output=True,env=env)
        self.assertEqual(result.returncode,0,result.stderr);self.assertIn('Café 世界 💠',result.stdout.decode('utf-8'))

    def test_full_inventory_is_searchable_above_fifty(self):
        d=copy.deepcopy(self.doc);d['stores']=[]
        for i in range(75):
            r=row(self.source);r.update(id=f'store-{i:03}',name=f'Store {i:03}',favorite=i==74,topics=['rare'] if i==74 else ['common']);d['stores'].append(r)
        self.assertEqual(len(g.search(d,'')),75);self.assertEqual(g.search(d,'Store 074')[0]['store']['id'],'store-074')

    def test_aggregate_limit_keeps_catalog_editable(self):
        d=copy.deepcopy(self.doc);d['stores']=[]
        for i in range(250):
            r=row(self.source);r.update(id=f'store-{i}',summary='A'*2000,provenance='B'*2000,sections=[{'id':'s','title':'Section','path':'','summary':'C'*2000,'topics':[]}]);d['stores'].append(r)
        with self.assertRaisesRegex(g.CatalogError,'1.5 MB'):self.cat.merge(d,0)
        self.assertFalse(self.path.exists())

    def test_relative_paths_and_windows_backslashes(self):
        self.assertEqual(g.relative('Shemp Studies\\README.md'),'Shemp Studies/README.md')
        for path in ('../secret','C:/secret','/secret','a/../../secret','..\\secret'):
            with self.assertRaises(g.CatalogError):g.relative(path)
    def test_alias_partial_memory_and_typo(self):
        self.assertEqual(g.search(self.doc,'Moe Larry')[0]['store']['id'],'stooges');self.assertEqual(g.search(self.doc,'Shemp')[0]['matched_sections'],['shemp']);self.assertEqual(g.search(self.doc,'Stoges')[0]['store']['id'],'stooges');self.assertEqual(g.search(self.doc,'unrelated quantum'),[])
    def test_filters_and_favorites(self):
        self.assertEqual(len(g.search(self.doc,topic='comedy')),1);self.assertEqual(g.search(self.doc,life='current'),[]);self.assertEqual(g.search(self.doc,favorites=True),[])
        self.doc['stores'][0]['favorite']=True;self.assertEqual(len(g.search(self.doc,favorites=True)),1)
    def test_rank_favors_specific_title_over_general_description(self):
        other=copy.deepcopy(self.doc['stores'][0]);other.update(id='other',name='General documents',aliases=[],topics=[],use_when=[],sections=[],summary='Shemp');self.doc['stores'].append(other);self.assertEqual(g.search(self.doc,'Shemp')[0]['store']['id'],'stooges')
    def test_brief_exact_section_and_limits(self):
        text=g.brief(self.doc['stores'][0],'shemp','Which films?');self.assertIn('under Shemp Studies.',text);self.assertIn(str(self.source)+'/Shemp Studies/README.md',text);self.assertIn('Current question: Which films?',text);self.assertIn('not checked',text);self.assertIn('do not prove content',text)
        with self.assertRaises(g.CatalogError):g.brief(self.doc['stores'][0],'imaginary')
    def test_source_reads_do_not_change_sources(self):
        before={p.relative_to(self.source).as_posix():p.read_bytes() for p in self.source.rglob('*') if p.is_file()};b=g.browse(self.doc['stores'][0]);self.assertEqual(b['entries'][0]['name'],'Shemp Studies');p=g.preview(self.doc['stores'][0],'INDEX.md');self.assertEqual(p['text'],'Source index — café 💠');self.assertFalse(p['truncated']);self.assertEqual(before,{p.relative_to(self.source).as_posix():p.read_bytes() for p in self.source.rglob('*') if p.is_file()})
    def test_preview_and_directory_bounds(self):
        (self.source/'large.md').write_text('A'*40000,encoding='utf-8');p=g.preview(self.doc['stores'][0],'large.md');self.assertTrue(p['truncated']);self.assertEqual(p['bytes_loaded'],32768);self.assertEqual(p['text'],'A'*32768)
        for i in range(202):(self.source/f'file-{i:03d}.txt').write_text('x')
        b=g.browse(self.doc['stores'][0]);self.assertEqual(len(b['entries']),200);self.assertTrue(b['truncated'])
    def test_traversal_and_binary_are_rejected(self):
        (self.source/'picture.png').write_bytes(b'PNG')
        with self.assertRaises(g.CatalogError):g.preview(self.doc['stores'][0],'picture.png')
        with self.assertRaises(g.CatalogError):g.preview(self.doc['stores'][0],'../secret.txt')
    def test_missing_and_remote_are_distinct(self):
        self.cat.save(self.doc,0);checked=self.cat.check('stooges',1);self.assertEqual(checked['stores'][0]['availability']['state'],'present');self.assertIn('not been verified',checked['stores'][0]['availability']['detail']);changed=copy.deepcopy(checked);changed['stores'][0]['location']=str(self.root/'missing');changed=self.cat.save(changed,2);self.assertNotIn('availability',changed['stores'][0]);missing=self.cat.check('stooges',3);self.assertEqual(missing['stores'][0]['availability']['state'],'missing')
    def test_websites_are_not_fetched(self):
        d=copy.deepcopy(self.doc);d['stores'][0].update(kind='website',location='https://example.invalid/archive');self.cat.save(d,0);self.assertEqual(self.cat.check('stooges',1)['stores'][0]['availability']['state'],'remote_unchecked')
        with self.assertRaises(g.CatalogError):g.browse(d['stores'][0])
        for url in ('http://example.com','javascript:alert(1)','https://user:secret@example.com'):
            with self.assertRaises(g.CatalogError):g.locator(url,'website')
    def test_malformed_catalog_is_preserved(self):
        self.path.parent.mkdir();self.path.write_text('{not json');before=self.path.read_bytes()
        with self.assertRaises(g.CatalogError):self.cat.save(self.doc,0)
        self.assertEqual(self.path.read_bytes(),before)
    def test_file_store_preview(self):
        s=copy.deepcopy(self.doc['stores'][0]);s.update(location=str(self.source/'INDEX.md'),kind='markdown',entrypoint='',sections=[]);self.assertEqual(g.preview(s)['text'],'Source index — café 💠');self.assertTrue(g.browse(s)['file'])
    def test_read_cli_has_bounded_usable_routes(self):
        import subprocess
        self.cat.save(self.doc,0);r=subprocess.run([sys.executable,'-B','-X','utf8',str(g.ROOT/'scripts/giles.py'),'--catalog',str(self.path),'find','Shemp'],capture_output=True,text=True,encoding='utf-8');self.assertEqual(r.returncode,0);self.assertIn('Shemp Studies',r.stdout);self.assertIn('metadata, not source reading',r.stdout)

class HTTP(Core):
    def setUp(self):
        super().setUp();self.cat.save(self.doc,0);self.server=g.make_server(self.path);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.addCleanup(self.shutdown);self.url=f'http://127.0.0.1:{self.server.server_port}'
    def shutdown(self):self.server.shutdown();self.server.server_close();self.thread.join()
    def request(self,path,body=None,token=True,headers=None):
        h=headers or {};data=None
        if body is not None:data=json.dumps(body).encode();h.update({'Content-Type':'application/json'});h.update({'X-Giles-Token':self.server.token} if token else {})
        req=urllib.request.Request(self.url+path,data,headers=h)
        try:
            with urllib.request.urlopen(req) as r:return r.status,r.read(),dict(r.headers)
        except urllib.error.HTTPError as e:
            try:return e.code,e.read(),dict(e.headers)
            finally:e.close()
    def test_api_write_roundtrip_and_export(self):
        d=json.loads(self.request('/api/catalog')[1]);d['stores'][0]['favorite']=True;code,data,_=self.request('/api/save',{'catalog':d,'expected_revision':1});self.assertEqual(code,200);self.assertEqual(json.loads(data)['revision'],2);self.assertTrue(g.Catalog(self.path).read()['stores'][0]['favorite']);self.assertEqual(json.loads(self.request('/api/export')[1]),g.Catalog(self.path).read())
    def test_denied_mutation_preserves_catalog(self):
        before=self.path.read_bytes();code,_,_=self.request('/api/save',{'catalog':self.doc,'expected_revision':1},token=False);self.assertEqual(code,400);self.assertEqual(self.path.read_bytes(),before)
        code,_,_=self.request('/api/check',{'id':'stooges','expected_revision':1},headers={'Origin':'https://hostile.invalid'});self.assertEqual(code,400);self.assertEqual(self.path.read_bytes(),before)
    def test_api_conflict_and_invalid_body_preserve_catalog(self):
        before=self.path.read_bytes();self.assertEqual(self.request('/api/save',{'catalog':self.doc,'expected_revision':0})[0],409);self.assertEqual(self.request('/api/import',{'catalog':{'schema':'no'},'expected_revision':1})[0],400);self.assertEqual(self.path.read_bytes(),before)
    def test_api_source_reads_and_exact_preview(self):
        code,data,_=self.request('/api/preview?id=stooges&path=Shemp%20Studies%2FREADME.md');self.assertEqual(code,200);self.assertEqual(json.loads(data)['text'],'Shemp chronology: 1947–1955.\n');self.assertEqual(self.request('/api/preview?id=stooges&path=..%2Fsecret')[0],400)
    def test_local_assets_security_and_host(self):
        code,html,headers=self.request('/');self.assertEqual(code,200);self.assertIn(self.server.token.encode(),html);self.assertIn("frame-ancestors 'none'",headers['Content-Security-Policy']);self.assertEqual(self.request('/app.js')[0],200);self.assertEqual(self.request('/style.css')[0],200);self.assertEqual(self.request('/api/catalog',headers={'Host':'hostile.invalid'})[0],400);self.assertEqual(self.request('/unknown')[0],404)
    def test_material_assets_are_real_local_png_bytes_and_confined(self):
        before=self.path.read_bytes()
        self.assertIn(b'/skins.css',self.request('/')[1])
        self.assertIn('text/css',self.request('/skins.css')[2]['Content-Type'])
        for name in ('atlas','blackglass','mirrorloop'):
            code,body,headers=self.request('/assets/'+name+'-material.png')
            self.assertEqual(code,200);self.assertEqual(headers['Content-Type'],'image/png')
            self.assertEqual(body,(g.ROOT/'workspace/assets'/ (name+'-material.png')).read_bytes())
            self.assertTrue(body.startswith(b'\x89PNG\r\n\x1a\n'));self.assertGreater(len(body),10000)
        for route in ('/assets/../scripts/giles.py','/assets/%2e%2e/scripts/giles.py','/assets/catalog.json','/assets/arbitrary.png'):
            self.assertEqual(self.request(route)[0],404)
        self.assertEqual(self.path.read_bytes(),before)
    # Core cases run only in Core; HTTP subclasses it solely to reuse the fixture.
for name in list(Core.__dict__):
    if name.startswith('test_') and name not in HTTP.__dict__:setattr(HTTP,name,None)
if __name__=='__main__':unittest.main()
