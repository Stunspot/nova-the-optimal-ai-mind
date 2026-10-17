from pathlib import Path
import sys,tempfile,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import dunbar
class DossierScopeTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.db=Path(self.temp.name)/'people.sqlite';dunbar.initialize_store(self.db);self.connection=dunbar.connect(self.db);self.addCleanup(self.connection.close)
  for key in ['one','two']:
   dunbar.put_person(self.connection,{'person_id':'person.'+key,'display_name':'Fixture '+key,'aliases':[key],'sensitivity':'private','source':{'source_kind':'user_supplied','label':'Synthetic test'}})
 def item(self,key,person,text,sensitivity='private'):
  return dunbar.put_item(self.connection,{'item_id':key,'person':person,'category':'preference','text':text,'evidence_state':'reported','sensitivity':sensitivity,'source':{'source_kind':'user_supplied','label':'Synthetic test'}})
 def ids(self,level,restricted=False):
  result=dunbar.recall(self.connection,'one','meeting',level,restricted);return {x['item_id'] for x in result['packet']['items']}
 def test_context_ranks_dossier_without_excluding_unrelated_history(self):
  self.item('item.meeting','person.one','Prefers a short meeting brief.')
  self.item('item.past','person.one','Previously preferred early travel.')
  dunbar.supersede_item(self.connection,{'supersedes_item_id':'item.past','revision_reason':'Synthetic correction','replacement':{'item_id':'item.current','text':'Now prefers late travel.','source':{'source_kind':'user_supplied','label':'Synthetic test'}}})
  self.item('item.secret','person.one','Restricted unrelated travel note.','restricted')
  self.item('item.other','person.two','Other person meeting preference.')
  self.assertEqual(self.ids('cue'),{'item.meeting'});self.assertEqual(self.ids('brief'),{'item.meeting'})
  self.assertEqual(self.ids('dossier'),{'item.meeting','item.past','item.current'})
  self.assertEqual(self.ids('dossier',True),{'item.meeting','item.past','item.current','item.secret'})
  self.assertTrue(dunbar.check_store(self.connection)['healthy'])
 def test_restricted_only_candidates_do_not_break_or_leak_fallback(self):
  self.item('item.secret','person.one','Restricted meeting note.','restricted')
  self.item('item.other','person.two','Other person meeting note.')
  self.assertEqual(self.ids('dossier'),set());self.assertEqual(self.ids('dossier',True),{'item.secret'})
if __name__=='__main__':unittest.main()
