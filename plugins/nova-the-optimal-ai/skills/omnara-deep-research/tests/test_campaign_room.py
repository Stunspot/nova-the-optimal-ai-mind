import io, zipfile, json, tempfile, unittest, sys
from pathlib import Path
sys.path[:0]=[str(Path(__file__).parents[1]/'workspace'),str(Path(__file__).parents[1]/'scripts')]
from campaign import CampaignRoom

class CampaignRoomTests(unittest.TestCase):
    def test_native_save_conflict_import_and_reopen(self):
        with tempfile.TemporaryDirectory() as tmp:
            room=CampaignRoom(Path(tmp)/'home'); room.root.mkdir()
            v=room.request('POST','/api/create',{'title':'A bounded question','question':'Which observation separates the hypotheses?'})
            old=v['revision']; c=json.loads(v['files']['campaign.json']); c['resume_point']='Find the original measurement';v['files']['campaign.json']=json.dumps(c)
            v['files']['source-ledger.jsonl']=json.dumps({'id':'S001','title':'Original observation','identifier':'fixture-source','states':['discovered']})+'\n'
            v['files']['claim-ledger.jsonl']=json.dumps({'id':'C001','claim':'The fixture supplies an observation, not a conclusion.','source_ids':['S001']})+'\n'
            saved=room.request('POST','/api/save',v)
            self.assertEqual(saved['validation'],[])
            self.assertEqual(json.loads(saved['files']['campaign.json'])['counters']['discovered'],1)
            with self.assertRaises(room.Conflict): room.save(v['key'],v['files'],old)
            self.assertEqual(CampaignRoom(room.root).load(v['key'])['revision'],saved['revision'])
            self.assertIn('Find the original measurement',room.request('POST','/api/handoff',{'key':v['key']})[0])
            imported=room.request('POST','/api/import',{'path':str(room.directory(v['key']))})
            self.assertEqual(imported['files'],saved['files'])
            self.assertGreater(len(room.request('POST','/api/export',{'key':v['key']})[0]),500)
    def test_unearned_states_and_paths_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            room=CampaignRoom(Path(tmp));v=room.request('POST','/api/create',{'title':'Fixture','question':'Is it supported?'})
            v['files']['source-ledger.jsonl']=json.dumps({'id':'S001','identifier':'fixture','states':['deeply-read']})
            with self.assertRaisesRegex(ValueError,'prerequisite'): room.request('POST','/api/save',v)
            with self.assertRaises(ValueError):room.checked_name('../escape.json')

    def test_campaign_text_boundary_preserves_external_corpora(self):
        with tempfile.TemporaryDirectory() as tmp:
            room=CampaignRoom(Path(tmp));v=room.request('POST','/api/create',{'title':'Custody','question':'What does the evidence establish?'})
            path=room.directory(v['key']);(path/'nested-study').mkdir()
            (path/'nested-study'/'report.md').write_text('A separate finished study',encoding='utf-8')
            (path/'case-snapshot.json').write_text('{"unrelated":"archive"}',encoding='utf-8')
            (path/'notes'/'S001.md').write_text('# Evidence\n\nA recorded observation.',encoding='utf-8')
            loaded=room.load(v['key'])
            self.assertNotIn('nested-study/report.md',loaded['files'])
            self.assertNotIn('case-snapshot.json',loaded['files'])
            self.assertIn('notes/S001.md',loaded['files'])
            loaded['files']['research-brief.md']+='\nA bounded follow-up.\n'
            saved=room.request('POST','/api/save',loaded)
            self.assertIn('A bounded follow-up.',saved['files']['research-brief.md'])
            self.assertEqual((path/'nested-study'/'report.md').read_text(encoding='utf-8'),'A separate finished study')
            self.assertEqual((path/'case-snapshot.json').read_text(encoding='utf-8'),'{"unrelated":"archive"}')
            blob=room.request('POST','/api/export',{'key':v['key']})[0]
            with zipfile.ZipFile(io.BytesIO(blob)) as z:
                self.assertEqual({n.split('/',1)[1] for n in z.namelist()},set(saved['files']))
            imported=room.request('POST','/api/import',{'path':str(path)})
            self.assertEqual(imported['files'],saved['files'])
            with self.assertRaises(ValueError): room.checked_name('case-snapshot.json')
