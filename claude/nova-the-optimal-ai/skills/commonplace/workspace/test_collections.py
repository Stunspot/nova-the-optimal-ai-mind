"""Whole-app collection reads stay inside original registered sources."""
import importlib.util,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import host
class CollectionReads(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.estate=Path(self.temp.name);self.root=self.estate/'original';self.root.mkdir();(self.root/'Home.md').write_text('# Original notebook\nThis is the original.',encoding='utf-8')
  for i in range(205):(self.root/f'page-{i:03}.md').write_text(str(i))
  catalog={'schema':'giles-knowledge-catalog/v1','revision':1,'stores':[{'id':'notebook','name':'A notebook','location':str(self.root),'entrypoint':'Home.md','kind':'folder'}]}
  directory=self.estate/'knowledge/giles';directory.mkdir(parents=True);self.catalog=directory/'catalog.json';self.catalog.write_text(json.dumps(catalog))
  host.ESTATE=self.estate
  reader_path=Path(__file__).resolve().parents[2]/'rupert-giles-knowledge-steward/scripts/giles.py'
  if not reader_path.is_file():reader_path=Path(__file__).resolve().parents[4]/'rupert-giles-knowledge-steward/scripts/giles.py'
  spec=importlib.util.spec_from_file_location('desk_test_giles',reader_path);self.reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.reader)
  self.patch=patch.object(host,'collection_reader',return_value=self.reader);self.patch.start();self.addCleanup(self.patch.stop)
 def test_catalog_and_original_document_reads_do_not_change_source(self):
  before=self.catalog.read_bytes();source=(self.root/'Home.md').read_bytes()
  result=host.read_collection('catalog',{});self.assertEqual(result['stores'][0]['name'],'A notebook')
  result=host.read_collection('preview',{'id':'notebook','path':'Home.md'});self.assertIn('original',result['text'])
  self.assertEqual(self.catalog.read_bytes(),before);self.assertEqual((self.root/'Home.md').read_bytes(),source)
 def test_paths_and_unregistered_stores_cannot_escape_catalog(self):
  for payload in ({'id':'other','path':'Home.md'},{'id':'notebook','path':'../secret.md'},{'id':'notebook','path':str(self.estate/'secret.md')}):
   with self.assertRaises(ValueError):host.read_collection('preview',payload)
 def test_folder_pagination_keeps_every_entry_available(self):
  first=host.read_collection('browse',{'id':'notebook'});second=host.read_collection('browse',{'id':'notebook','offset':first['next_offset']})
  paths=[x['path'] for x in first['entries']+second['entries']]
  self.assertEqual(len(paths),206);self.assertEqual(len(set(paths)),206);self.assertEqual(first['total'],206);self.assertIsNone(second['next_offset'])
 def test_private_saved_notes_are_included_without_restricted_records(self):
  import subprocess
  with patch('host.subprocess.run',return_value=subprocess.CompletedProcess([],0,'{"records":[{"title":"Visible"}]}','')) as run:
   host.read_owner('notes',{})
   self.assertEqual(json.loads(run.call_args.kwargs['input'])['allowed_sensitivities'],['public','personal','private'])
 def test_catalog_stamp_reads_revision_without_browsing_sources(self):
  with patch.object(self.reader,'browse',side_effect=AssertionError('Stamp must not scan source files')):
   self.assertEqual(host.read_collection('catalog-status',{}),{'revision':1,'store_count':1})
  value=json.loads(self.catalog.read_text());value['revision']=2;self.catalog.write_text(json.dumps(value))
  self.assertEqual(host.read_collection('catalog-status',{})['revision'],2)
 def test_section_kind_uses_actual_filesystem_and_preserves_bounds(self):
  (self.root/'Sections.v2').mkdir();(self.root/'README').write_text('Plain extensionless document')
  self.assertTrue(host.read_collection('locate',{'id':'notebook','path':'Sections.v2'})['directory'])
  self.assertFalse(host.read_collection('locate',{'id':'notebook','path':'README'})['directory'])
  with self.assertRaises(ValueError):host.read_collection('locate',{'id':'notebook','path':'../secret'})

if __name__=='__main__':unittest.main()

