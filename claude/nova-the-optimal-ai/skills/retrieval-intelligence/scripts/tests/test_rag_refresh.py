from pathlib import Path
import sys,tempfile,unittest,sqlite3
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from contextlib import closing
import rag
class RefreshTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name);self.corpus=self.root/'corpus';self.corpus.mkdir();self.db=self.root/'index.sqlite'
 def index(self,size=512,overlap=0):return rag.sync_index(self.corpus,self.db,{'.md'},100000,size,overlap)
 def chunks(self):
  with closing(sqlite3.connect(self.db)) as c:return c.execute('SELECT id,start_line,end_line,content FROM chunks ORDER BY chunk_index').fetchall()
 def test_changed_policy_rechunks_unchanged_sources_and_rebinds_identity(self):
  text='\n'.join('Observation '+str(i)+': supply and restart are separate events.' for i in range(24));(self.corpus/'observations.md').write_text(text,encoding='utf-8')
  first=self.index(512);before=self.chunks();second=self.index(128);after=self.chunks()
  self.assertEqual(second['updated_sources'],1);self.assertNotEqual(first['index_id'],second['index_id']);self.assertGreater(len(after),len(before))
  expected=[(c.start_line,c.end_line,c.content) for c in rag.chunk_text(text,128,0)];self.assertEqual([r[1:] for r in after],expected)
  old_ids={r[0] for r in before};new_ids={r[0] for r in after}
  with closing(sqlite3.connect(self.db)) as c:self.assertEqual({r[0] for r in c.execute('SELECT chunk_id FROM chunk_fts')},new_ids)
  self.assertNotEqual(old_ids,new_ids);third=self.index(128);self.assertEqual(third['unchanged_sources'],1);self.assertEqual(third['inserted_chunks'],0);self.assertEqual(third['index_id'],second['index_id'])
 def test_invalid_options_on_empty_corpus_do_not_publish_index(self):
  for size,overlap in [(64,0),(128,128),(128,-1)]:
   with self.assertRaises(ValueError):self.index(size,overlap)
   self.assertFalse(self.db.exists())
 def test_source_refresh_and_deletion_remove_stale_fts_rows(self):
  p=self.corpus/'observation.md';p.write_text('Old turbine chronology.',encoding='utf-8');self.index();p.write_text('New supply chronology.',encoding='utf-8');updated=self.index();self.assertEqual(updated['updated_sources'],1)
  self.assertEqual(rag.search_index(self.db,'turbine')['results'],[]);self.assertTrue(rag.search_index(self.db,'supply')['results']);p.unlink();deleted=self.index();self.assertEqual(deleted['deleted_sources'],1);self.assertEqual(rag.search_index(self.db,'supply')['results'],[])
 def test_unicode_cli_outputs_utf8_under_windows_legacy_encoding(self):
  import os,subprocess,json
  (self.corpus/'観測.md').write_text('計測した電圧 supply remained stable.',encoding='utf-8');self.index()
  env=os.environ.copy();env['PYTHONIOENCODING']='cp1252';script=Path(rag.__file__)
  p=subprocess.run([sys.executable,'-B',str(script),'search','--db',str(self.db),'--query','supply','--json'],env=env,capture_output=True)
  self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(json.loads(p.stdout.decode('utf-8'))['results'][0]['source'],'観測.md')
  cases=self.root/'cases.json';cases.write_text(json.dumps({'schema':'retrieval-eval-cases-v1','cases':[{'id':'観測','query':'supply','relevant_sources':['観測.md']}]}),encoding='utf-8')
  p=subprocess.run([sys.executable,'-B',str(script.parent/'evaluate_retrieval.py'),'--db',str(self.db),'--cases',str(cases)],env=env,capture_output=True)
  self.assertEqual(p.returncode,0,p.stderr);self.assertTrue(json.loads(p.stdout.decode('utf-8'))['passed'])
if __name__=='__main__':unittest.main()
