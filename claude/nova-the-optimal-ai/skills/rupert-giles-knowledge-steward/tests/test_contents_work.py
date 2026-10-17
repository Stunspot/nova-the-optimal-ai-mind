import base64, copy, importlib.util, io, json, os, sqlite3, tempfile, threading, unittest, urllib.error, urllib.parse, urllib.request, zipfile
from pathlib import Path
from unittest.mock import patch
from xml.sax.saxutils import escape

spec=importlib.util.spec_from_file_location('giles_contents',Path(__file__).resolve().parents[1]/'scripts/giles.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
PNG=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+j5N0AAAAASUVORK5CYII=')

def pdf_file(path,paragraphs):
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
    writer=PdfWriter()
    for content in paragraphs:
        page=writer.add_blank_page(width=612,height=792)
        font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
        page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):font})})
        stream=DecodedStreamObject();literal=content.replace('\\','\\\\').replace('(','\\(').replace(')','\\)')
        stream.set_data(('BT /F1 12 Tf 40 700 Td ('+literal+') Tj ET').encode('ascii'))
        page[NameObject('/Contents')]=writer._add_object(stream)
    with path.open('wb') as f:writer.write(f)

def docx_file(path,paragraphs):
    body=''.join('<w:p><w:r><w:t>'+escape(p)+'</w:t></w:r></w:p>' for p in paragraphs)
    xml='<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'+body+'</w:body></w:document>'
    with zipfile.ZipFile(path,'w') as z:z.writestr('word/document.xml',xml)

class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.source=self.root/'sources';self.source.mkdir()
        (self.source/'INDEX.md').write_text('Actual index: Read the original source.\n',encoding='utf-8',newline='\n')
        (self.source/'record.md').write_text('  Quoted evidence — café 世界.\nKeep source whitespace.\n',encoding='utf-8',newline='\n')
        (self.source/'image.png').write_bytes(PNG)
        self.cat=g.Catalog(self.root/'custody/catalog.json')
        self.doc=self.cat.save({'schema':g.SCHEMA,'revision':0,'stores':[{'id':'archive','name':'Real Fixture Archive','location':str(self.source),'entrypoint':'INDEX.md','summary':'Catalog description differs from source contents.','kind':'folder','role':'canonical','lifecycle':'current','inspection':'metadata_only','owner':'Fixture owner','provenance':'Fixture registration'}]},0)
        self.store=self.doc['stores'][0];self.work=g.Workbench(self.cat)
    def collect_body(self,path='record.md',selected=None,offset=0,page=0,work_revision=None):
        sample=g.preview(self.store,path,offset,page)
        return {'id':'archive','path':path,'text':sample['text'] if selected is None else selected,'note':'My annotation, not the author’s statement.','anchor':sample['anchor'],'sample_sha256':sample['sample_sha256'],'expected_revision':self.cat.read()['revision'],'expected_workbench_revision':self.work.read()['revision'] if work_revision is None else work_revision}
    def contents(self):return {p.relative_to(self.source).as_posix():p.read_bytes() for p in self.source.rglob('*') if p.is_file()}

class ContentTests(Fixture):
    def test_overview_reads_actual_index_and_root_brief_preserves_distinction(self):
        view=g.overview(self.store);self.assertEqual(view['index']['text'],'Actual index: Read the original source.\n');self.assertNotIn('Catalog description differs',view['index']['text'])
        default=g.brief(self.store);root=g.brief(self.store,path='')
        self.assertIn('Source route: '+str(self.source)+'/INDEX.md\n',default);self.assertIn('Source route: '+str(self.source)+'\n',root);self.assertNotIn('/INDEX.md',root)
    def test_long_unicode_text_roundtrips_all_chunks(self):
        original='Beginning\n'+('café 世界💠 ' *9000)+'\nFINAL EVIDENCE'
        (self.source/'long.md').write_text(original,encoding='utf-8',newline='\n')
        chunks=[];offset=0
        while True:
            sample=g.preview(self.store,'long.md',offset);self.assertLessEqual(sample['bytes_loaded'],32768);self.assertNotIn('\ufffd',sample['text']);chunks.append(sample['text'])
            if sample['next_offset'] is None:break
            self.assertGreater(sample['next_offset'],offset);offset=sample['next_offset']
        self.assertGreater(len(chunks),2);self.assertEqual(''.join(chunks),original)
    def test_navigation_positions_and_confined_paths(self):
        for offset,page in [(-1,0),(False,0),(0,-1),(0,True),(1_000_000_001,0),(999,0)]:
            with self.assertRaises(g.CatalogError):g.preview(self.store,'record.md',offset,page)
        for path in ['../outside.txt','/outside.txt','C:/outside.txt','nested/../../outside']:
            with self.assertRaises(g.CatalogError):g.preview(self.store,path)
    def test_symlink_escape_is_not_read(self):
        target=self.root/'private.txt';target.write_text('Private content')
        link=self.source/'linked.md'
        try:link.symlink_to(target)
        except OSError:self.skipTest('Host does not permit symlinks')
        with self.assertRaises(g.CatalogError):g.preview(self.store,'linked.md')
    def test_pdf_real_text_page_windows_and_long_page(self):
        pdf_file(self.source/'pages.pdf',[f'Real PDF page {n}' for n in range(1,9)])
        first=g.preview(self.store,'pages.pdf');self.assertEqual(first['format'],'pdf');self.assertEqual(first['pages_read'],6);self.assertEqual(first['page_count'],8);self.assertEqual(first['next_page'],6)
        self.assertIn('Real PDF page 1',first['text']);self.assertIn('Real PDF page 6',first['text']);self.assertNotIn('Real PDF page 7',first['text']);self.assertIn('does not establish complete',first['notes'][0])
        last=g.preview(self.store,'pages.pdf',page=6);self.assertIn('Real PDF page 8',last['text']);self.assertIsNone(last['next_page'])
        pdf_file(self.source/'long.pdf',['START '+('Evidence '*6000)+'END'])
        one=g.preview(self.store,'long.pdf');two=g.preview(self.store,'long.pdf',one['next_offset']);self.assertIn('END',two['text']);self.assertLessEqual(one['bytes_loaded'],32768)
        with self.assertRaises(g.CatalogError):g.preview(self.store,'pages.pdf',page=8)
    def test_pdf_encrypted_malformed_and_size_limits(self):
        from pypdf import PdfWriter
        writer=PdfWriter();writer.add_blank_page(width=100,height=100);writer.encrypt('secret')
        with (self.source/'encrypted.pdf').open('wb') as f:writer.write(f)
        with self.assertRaisesRegex(g.CatalogError,'Encrypted'):g.preview(self.store,'encrypted.pdf')
        (self.source/'bad.pdf').write_bytes(b'not a PDF')
        with self.assertRaisesRegex(g.CatalogError,'could not be read'):g.preview(self.store,'bad.pdf')
        with (self.source/'huge.pdf').open('wb') as f:f.truncate(g.FILE_BYTES+1)
        with self.assertRaisesRegex(g.CatalogError,'50 MB'):g.preview(self.store,'huge.pdf')
    def test_docx_actual_xml_text_navigation_and_entities_rejected(self):
        docx_file(self.source/'source.docx',['Actual source — café','Second paragraph <&>', 'L'*40000])
        sample=g.preview(self.store,'source.docx');self.assertIn('Actual source — café\nSecond paragraph <&>\n',sample['text']);self.assertEqual(sample['format'],'docx');self.assertIsNotNone(sample['next_offset'])
        later=g.preview(self.store,'source.docx',sample['next_offset']);self.assertTrue(later['text']);self.assertIsNone(later['next_offset'])
        with zipfile.ZipFile(self.source/'entity.docx','w') as z:z.writestr('word/document.xml','<!DOCTYPE x [<!ENTITY secret "boom">]><x/>')
        with self.assertRaisesRegex(g.CatalogError,'entity'):g.preview(self.store,'entity.docx')
        with zipfile.ZipFile(self.source/'expanded.docx','w',compression=zipfile.ZIP_DEFLATED) as z:z.writestr('word/document.xml','X'*100000)
        with self.assertRaisesRegex(g.CatalogError,'expansion'):g.preview(self.store,'expanded.docx')
    def test_actual_image_and_unsupported_or_disguised_binary(self):
        sample=g.preview(self.store,'image.png');self.assertEqual(sample['format'],'image');self.assertEqual(sample['text'],'');self.assertEqual(sample['bytes_loaded'],len(PNG));self.assertIn('source_fingerprint',sample['media_url'])
        self.assertEqual(g.image_data(self.store,'image.png')[0],PNG)
        for name,data in [('fake.png',b'<svg onload="alert(1)"/>'),('active.svg',b'<svg/>'),('app.html',b'<script>bad()</script>'),('data.sqlite3',b'SQLite format 3')]:
            (self.source/name).write_bytes(data)
            with self.assertRaises(g.CatalogError):g.preview(self.store,name)
        with (self.source/'huge.png').open('wb') as f:f.write(PNG);f.truncate(g.IMAGE_BYTES+1)
        with self.assertRaisesRegex(g.CatalogError,'20 MB'):g.preview(self.store,'huge.png')
    def test_source_change_during_bounded_read_is_conflict(self):
        original=g.Path.open;target=self.source/'record.md';old=target.read_bytes()
        class ChangingRead(io.BytesIO):
            def read(self,*args):
                data=super().read(*args)
                with original(target,'wb') as f:f.write(b'Changed during actual file reading')
                return data
        def changing(path,*args,**kwargs):
            return ChangingRead(old) if path==target and args and args[0]=='rb' else original(path,*args,**kwargs)
        with patch.object(g.Path,'open',changing):
            with self.assertRaises(g.Conflict):g.preview(self.store,'record.md')

class WorkTests(Fixture):
    def test_collection_exact_source_and_packet_separates_notes(self):
        before=self.contents();body=self.collect_body(selected='  Quoted evidence — café 世界.\n');saved=self.work.collect(body);item=saved['excerpts'][0]
        self.assertEqual(item['text'],body['text']);self.assertEqual(item['location'],str(self.source));self.assertEqual(item['path'],'record.md');self.assertEqual(item['store_name'],self.store['name']);self.assertEqual(item['anchor'],{'offset':0,'page':0});self.assertEqual(item['verification']['status'],'verified_match')
        md=g.packet(saved);self.assertIn(body['text'],md);self.assertIn('Source route: '+str(self.source)+'/record.md',md);self.assertIn('### User annotation (not source text)',md);self.assertIn(body['note'],md);self.assertIn('no semantic synthesis',md);self.assertEqual(self.contents(),before)
        self.assertEqual(self.work.path,self.cat.path.parent/'workbench.json');self.assertFalse(self.work.path.is_relative_to(g.ROOT))
    def test_collect_rejects_invented_or_stale_sample_and_stale_revisions(self):
        forged=self.collect_body(selected='Invented claim')
        with self.assertRaisesRegex(g.CatalogError,'verbatim'):self.work.collect(forged)
        self.assertFalse(self.work.path.exists())
        stale=self.collect_body();(self.source/'record.md').write_text('Changed actual source',encoding='utf-8',newline='\n')
        with self.assertRaises(g.Conflict):self.work.collect(stale)
        body=self.collect_body();body['expected_revision']=0
        with self.assertRaises(g.Conflict):self.work.collect(body)
        body=self.collect_body();saved=self.work.collect(body)
        with self.assertRaises(g.Conflict):self.work.collect(body)
        self.assertEqual(self.work.read(),saved)
    def test_image_reference_collection_contains_citation_not_ocr(self):
        body=self.collect_body('image.png',selected='');saved=self.work.collect(body);item=saved['excerpts'][0]
        self.assertEqual(item['format'],'image');self.assertEqual(item['text'],'');self.assertIn('no textual excerpt or OCR',g.packet(saved));self.assertIn('image.png',g.packet(saved))
        body=self.collect_body('image.png',selected='Imagined OCR')
        with self.assertRaisesRegex(g.CatalogError,'OCR'):self.work.collect(body)
    def test_save_annotation_order_removal_and_immutable_source(self):
        one=self.work.collect(self.collect_body());two=self.work.collect(self.collect_body('INDEX.md'))
        candidate=copy.deepcopy(two);candidate['title']='A durable knowledge packet';candidate['goal']='Answer a specific question';candidate['excerpts'].reverse();candidate['excerpts'][0]['note']='My revised note'
        saved=self.work.save(candidate,1,2);self.assertEqual(saved['revision'],3);self.assertEqual(saved['excerpts'][0]['path'],'INDEX.md');self.assertEqual(saved['goal'],'Answer a specific question')
        forged=copy.deepcopy(saved);forged['excerpts'][0]['text']='Fabrication'
        with self.assertRaisesRegex(g.CatalogError,'immutable'):self.work.save(forged,1,3)
        reduced=copy.deepcopy(saved);reduced['excerpts']=[];self.assertEqual(self.work.save(reduced,1,3)['excerpts'],[])
    def test_atomic_failure_locks_and_reopen_preserve_records(self):
        saved=self.work.collect(self.collect_body());candidate=copy.deepcopy(saved);candidate['goal']='Do not persist failure'
        with patch.object(g.os,'replace',side_effect=OSError('disk failed')):
            with self.assertRaises(OSError):self.work.save(candidate,1,1)
        self.assertEqual(self.work.read(),saved);self.assertEqual(list(self.work.path.parent.glob('*.tmp')),[])
        with g.process_lock(self.work.path.with_suffix('.lock')):
            with self.assertRaises(g.Conflict):g.Workbench(g.Catalog(self.cat.path)).save(candidate,1,1)
        self.assertEqual(g.Workbench(g.Catalog(self.cat.path)).read(),saved)
    def test_export_import_preserves_historical_evidence_when_changed_missing_or_removed(self):
        saved=self.work.collect(self.collect_body());export=json.loads(json.dumps(saved,ensure_ascii=False));original=export['excerpts'][0]
        restored=self.work.restore(export,1,1);self.assertEqual(restored['excerpts'][0]['verification']['status'],'verified_match')
        (self.source/'record.md').write_text('This source changed',encoding='utf-8',newline='\n');changed=self.work.restore(export,1,2)
        self.assertEqual(changed['excerpts'][0]['verification']['status'],'changed')
        for key in original:
            if key!='verification':self.assertEqual(changed['excerpts'][0][key],original[key])
        (self.source/'record.md').unlink();missing=self.work.restore(export,1,3);self.assertEqual(missing['excerpts'][0]['verification']['status'],'unavailable');self.assertIn(original['text'],g.packet(missing))
        catalog=self.cat.read();catalog['stores']=[];self.cat.save(catalog,1);removed=self.work.restore(export,2,4);self.assertEqual(removed['excerpts'][0]['verification']['status'],'unavailable');self.assertEqual(removed['excerpts'][0]['text'],original['text'])
    def test_reopen_observation_warns_without_rewriting_stored_excerpt(self):
        saved=self.work.collect(self.collect_body());before=self.work.path.read_bytes();(self.source/'record.md').write_text('Changed',encoding='utf-8',newline='\n')
        observed=self.work.observe(self.work.read(),self.cat.read());self.assertEqual(observed['excerpts'][0]['verification']['status'],'changed');self.assertEqual(observed['excerpts'][0]['text'],saved['excerpts'][0]['text']);self.assertEqual(self.work.path.read_bytes(),before)
    def test_limits_and_malformed_import_are_atomic(self):
        saved=self.work.collect(self.collect_body());before=self.work.path.read_bytes()
        cases=[];bad=copy.deepcopy(saved);bad['excerpts'][0]['path']='../private.txt';cases.append(bad)
        bad=copy.deepcopy(saved);bad['excerpts'][0]['anchor']['offset']=-1;cases.append(bad)
        bad=copy.deepcopy(saved);bad['excerpts']=[dict(copy.deepcopy(saved['excerpts'][0]),id=f'excerpt-{n}') for n in range(21)];cases.append(bad)
        bad=copy.deepcopy(saved);bad['excerpts']=[dict(copy.deepcopy(saved['excerpts'][0]),id=f'excerpt-{n}',text='A'*32768) for n in range(20)];cases.append(bad)
        for bad in cases:
            with self.assertRaises(g.CatalogError):self.work.restore(bad,1,1)
            self.assertEqual(self.work.path.read_bytes(),before)
        with self.assertRaises(g.CatalogError):g.Workbench(g.Catalog(g.ROOT/'catalog.json')).read()
    def test_packet_preserves_literal_markdown_and_fences(self):
        (self.source/'record.md').write_text('Original ```code```\n# Source heading\n[link](javascript:fake)\n',encoding='utf-8',newline='\n')
        saved=self.work.collect(self.collect_body());md=g.packet(saved);self.assertIn('````\n'+saved['excerpts'][0]['text']+'\n````',md)

class HTTPTests(Fixture):
    def setUp(self):
        super().setUp();self.server=g.make_server(self.cat.path);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.addCleanup(self.shutdown);self.url=f'http://127.0.0.1:{self.server.server_port}'
    def shutdown(self):self.server.shutdown();self.server.server_close();self.thread.join()
    def request(self,path,body=None,token=True):
        headers={};data=None
        if body is not None:
            data=json.dumps(body,ensure_ascii=False).encode('utf-8');headers['Content-Type']='application/json'
            if token:headers['X-Giles-Token']=self.server.token
        try:
            with urllib.request.urlopen(urllib.request.Request(self.url+path,data,headers=headers)) as r:return r.status,r.read(),dict(r.headers)
        except urllib.error.HTTPError as e:
            try:return e.code,e.read(),dict(e.headers)
            finally:e.close()
    def value(self,path,body=None):
        status,data,headers=self.request(path,body);return status,json.loads(data),headers
    def test_http_image_exact_bytes_revision_and_fingerprint(self):
        status,sample,_=self.value('/api/preview?id=archive&path=image.png&expected_revision=1');self.assertEqual(status,200)
        status,data,headers=self.request(sample['media_url']);self.assertEqual(status,200);self.assertEqual(data,PNG);self.assertEqual(headers['Content-Type'],'image/png');self.assertEqual(headers['X-Content-Type-Options'],'nosniff')
        self.assertEqual(self.request('/api/media?id=archive&path=image.png')[0],400);self.assertEqual(self.request(sample['media_url'].replace('expected_revision=1','expected_revision=0'))[0],409)
        (self.source/'image.png').write_bytes(PNG+b'changed');self.assertEqual(self.request(sample['media_url'])[0],409)
        self.assertEqual(self.request('/api/media?id=archive&path=..%2Fprivate.png&expected_revision=1')[0],400)
    def test_http_collect_save_packet_export_import_and_source_unchanged(self):
        before=self.contents();status,initial,_=self.value('/api/workbench');self.assertEqual(status,200);self.assertEqual(initial['revision'],0)
        status,saved,_=self.value('/api/collect',self.collect_body(selected='Quoted evidence — café 世界.'));self.assertEqual(status,200);self.assertEqual(saved['revision'],1);self.assertEqual(saved['catalog_revision'],1)
        saved['goal']='Use the evidence';saved['excerpts'][0]['note']='Interpretation belongs here'
        status,saved,_=self.value('/api/workbench/save',{'workbench':saved,'expected_revision':1,'expected_workbench_revision':1});self.assertEqual(status,200);self.assertEqual(saved['revision'],2)
        status,packet,_=self.value('/api/packet?expected_revision=1&expected_workbench_revision=2');self.assertEqual(status,200);self.assertIn('Use the evidence',packet['markdown']);self.assertIn('Quoted evidence — café 世界.',packet['markdown'])
        status,export,_=self.value('/api/workbench/export');self.assertEqual(status,200);self.assertNotIn('catalog_revision',export)
        status,restored,_=self.value('/api/workbench/import',{'workbench':export,'expected_revision':1,'expected_workbench_revision':2});self.assertEqual(status,200);self.assertEqual(restored['revision'],3);self.assertEqual(restored['excerpts'][0]['text'],export['excerpts'][0]['text']);self.assertEqual(self.contents(),before)
    def test_http_conflicts_authentication_and_historical_reopen(self):
        body=self.collect_body();self.assertEqual(self.request('/api/collect',body,token=False)[0],400)
        status,saved,_=self.value('/api/collect',body);self.assertEqual(status,200);self.assertEqual(self.request('/api/collect',body)[0],409)
        self.assertEqual(self.request('/api/packet?expected_workbench_revision=0')[0],409);self.assertEqual(self.request('/api/preview?id=archive&path=record.md&expected_revision=0')[0],409)
        (self.source/'record.md').unlink();status,observed,_=self.value('/api/workbench');self.assertEqual(status,200);self.assertEqual(observed['excerpts'][0]['verification']['status'],'unavailable')
        status,packet,_=self.value('/api/packet');self.assertEqual(status,200);self.assertIn('unavailable',packet['markdown']);self.assertIn(saved['excerpts'][0]['text'],packet['markdown'])
    def test_http_text_pdf_navigation_invalid_positions_and_root_brief(self):
        (self.source/'long.md').write_text('A'*40000);status,first,_=self.value('/api/preview?id=archive&path=long.md&offset=0');self.assertEqual(status,200);self.assertEqual(first['next_offset'],32768)
        status,later,_=self.value('/api/preview?id=archive&path=long.md&offset=32768');self.assertEqual(status,200);self.assertEqual(len(later['text']),7232)
        self.assertEqual(self.request('/api/preview?id=archive&path=long.md&offset=-1')[0],400);self.assertEqual(self.request('/api/preview?id=archive&path=long.md&offset=bad')[0],400)
        status,brief,_=self.value('/api/brief?id=archive&path=&expected_revision=1');self.assertEqual(status,200);self.assertIn('Source route: '+str(self.source)+'\n',brief['text'])

class ArchiveIntegration(Fixture):
    request=HTTPTests.request
    value=HTTPTests.value
    shutdown=HTTPTests.shutdown
    def setUp(self):
        super().setUp();g.archive_reader()._clear_cache();self.addCleanup(g.archive_reader()._clear_cache)
        self.database=self.source/'rag/archive-current.sqlite3';self.database.parent.mkdir()
        connection=sqlite3.connect(self.database)
        connection.executescript("""
            CREATE TABLE documents(id INTEGER PRIMARY KEY, source TEXT, external_id TEXT, title TEXT, created_at TEXT, source_path TEXT, metadata_json TEXT, ingested_at TEXT);
            CREATE TABLE chunks(id INTEGER PRIMARY KEY, document_id INTEGER, ordinal INTEGER, role TEXT, created_at TEXT, content TEXT);
            CREATE VIRTUAL TABLE chunks_fts USING fts5(content, content='chunks', content_rowid='id');
        """)
        connection.execute('INSERT INTO documents VALUES (?,?,?,?,?,?,?,?)',(7,'chatgpt','conversation-世界','Real archive conversation','2026-09-01','originals/export.json','{}','2026-09-02'))
        connection.execute('INSERT INTO chunks VALUES (?,?,?,?,?,?)',(91,7,3,'assistant','2026-09-01','Real archived knowledge — café 世界.\n'+('Further source evidence ' *2000)))
        connection.execute("INSERT INTO chunks_fts(chunks_fts) VALUES ('rebuild')");connection.commit();connection.close()
        self.server=g.make_server(self.cat.path);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.addCleanup(self.shutdown);self.url=f'http://127.0.0.1:{self.server.server_port}'
    def archive_sample(self):
        status,result,_=self.value('/api/archive/search?'+urllib.parse.urlencode({'id':'archive','q':'archived knowledge','expected_revision':1}));self.assertEqual(status,200);self.assertEqual(len(result['hits']),1)
        anchor=result['hits'][0]['anchor'];status,sample,_=self.value('/api/archive/record?'+urllib.parse.urlencode(dict(anchor,id='archive',expected_revision=1)));self.assertEqual(status,200)
        return sample
    def archive_body(self,sample):
        return {'id':'archive','path':sample['path'],'text':'Real archived knowledge — café 世界.','note':'Useful to the current question','anchor':sample['anchor'],'sample_sha256':sample['sample_sha256'],'expected_revision':1,'expected_workbench_revision':0}
    def test_archive_search_record_collection_and_packet_are_real_and_readonly(self):
        before=self.contents();status,view,_=self.value('/api/overview?id=archive&expected_revision=1');self.assertEqual(status,200);self.assertEqual(view['archive']['document_count'],1);self.assertEqual(view['archive']['chunk_count'],1)
        sample=self.archive_sample();self.assertEqual(sample['text'],sample['content']);self.assertEqual(sample['format'],'archive');self.assertIsNotNone(sample['next_offset'])
        status,saved,_=self.value('/api/collect',self.archive_body(sample));self.assertEqual(status,200);item=saved['excerpts'][0];self.assertEqual(item['anchor'],sample['anchor']);self.assertEqual(item['format'],'archive');self.assertEqual(item['source_fingerprint'],sample['source_fingerprint'])
        status,out,_=self.value('/api/packet');self.assertEqual(status,200);self.assertIn('conversation-世界',out['markdown']);self.assertIn('rag/archive-current.sqlite3',out['markdown']);self.assertIn('Real archived knowledge — café 世界.',out['markdown']);self.assertIn('originals/export.json',out['markdown']);self.assertEqual(self.contents(),before)
    def test_archive_stale_snapshot_and_invented_collection_are_rejected(self):
        sample=self.archive_sample();body=self.archive_body(sample);body['text']='An invented archival claim';self.assertEqual(self.request('/api/collect',body)[0],400)
        body=self.archive_body(sample);connection=sqlite3.connect(self.database);connection.execute('UPDATE chunks SET content=? WHERE id=91',('Changed archive source',));connection.commit();connection.close()
        self.assertEqual(self.request('/api/collect',body)[0],409);self.assertFalse(self.work.path.exists())
        self.assertEqual(self.request('/api/archive/search?id=archive&expected_revision=0')[0],409)
    def test_archive_export_reopen_after_cache_reset_and_changed_source_retains_quote(self):
        sample=self.archive_sample();status,saved,_=self.value('/api/collect',self.archive_body(sample));self.assertEqual(status,200);original=saved['excerpts'][0]
        g.archive_reader()._clear_cache();status,observed,_=self.value('/api/workbench');self.assertEqual(status,200);self.assertEqual(observed['excerpts'][0]['verification']['status'],'verified_match');self.assertEqual(observed['excerpts'][0]['anchor'],original['anchor'])
        status,restored,_=self.value('/api/workbench/import',{'workbench':saved,'expected_revision':1,'expected_workbench_revision':1});self.assertEqual(status,200);self.assertEqual(restored['excerpts'][0]['verification']['status'],'verified_match')
        connection=sqlite3.connect(self.database);connection.execute('UPDATE chunks SET content=? WHERE id=91',('New archive state',));connection.commit();connection.close()
        status,observed,_=self.value('/api/workbench');self.assertEqual(status,200);self.assertEqual(observed['excerpts'][0]['verification']['status'],'changed');self.assertEqual(observed['excerpts'][0]['text'],original['text']);self.assertEqual(observed['excerpts'][0]['source_fingerprint'],original['source_fingerprint'])
    def test_archive_pagination_and_guarded_query_validation(self):
        sample=self.archive_sample();anchor=dict(sample['anchor'],offset=sample['next_offset']);status,later,_=self.value('/api/archive/record?'+urllib.parse.urlencode(dict(anchor,id='archive',expected_revision=1)));self.assertEqual(status,200);self.assertIsNone(later['next_offset']);self.assertTrue(later['text'])
        self.assertEqual(self.request('/api/archive/record?id=archive&source=chatgpt&external_id=conversation&ordinal=-1')[0],400);self.assertEqual(self.request('/api/archive/search?id=archive&limit=1000')[0],400)
        status,result,_=self.value('/api/archive/search?id=archive&q=%22%20OR%201%3D1');self.assertEqual(status,200);self.assertEqual(result['hits'],[])

if __name__=='__main__':unittest.main()
