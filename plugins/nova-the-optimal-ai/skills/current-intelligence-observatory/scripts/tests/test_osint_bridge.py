"""Focused native OSINT attachment checks: provenance, partial state, and preservation."""
import copy,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from osint_bridge import attach,workbench,digest
from observatory_guardrail import canonical_url,validate_case,project_case,verify_projection_invariants
SKILL=Path(__file__).resolve().parents[2]

class OsintBridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.home=Path(self.temp.name)/'home';self.home.mkdir();(self.home/'osint.py').write_text('');(self.home/'registry.json').write_text('{"tools":[]}')
        self.run=self.home/'runs/test-run';self.run.mkdir(parents=True)
        self.report=[{'module':'sfp_email','type':'EMAILADDR','data':'fixture@example.test','hash':'synthetic-event'}]
        (self.run/'spiderfoot-events.json').write_text(json.dumps(self.report))
        (self.run/'run.json').write_text(json.dumps({'target':'example.test','completed_at':'2026-10-05T23:00:00+00:00','exit_code':0,'command':['python','fixture','--fixture']}))
        self.case=json.loads((SKILL/'assets/observatory-case.template.json').read_text(encoding='utf-8'))
        self.case.update(title='Synthetic domain inquiry',question='What does the supplied report say?',audience_or_decision='Review offline wiring',time_horizon='2026-10-05',scope='Supplied synthetic report only',collection_authority='Local supplied fixtures only',harm_model='Avoid converting a name or address into identity evidence',evidence_burden='Preserve raw reports; independently verify before claims',stop_condition='Stop after offline attachment')
        self.case['claims']=[{'id':'CLM-EXISTING','statement':'Existing fixture judgment','status':'provisional','confidence':'low','uncertainty':'Existing unresolved issue'}]
        self.original=Path(self.temp.name)/'case.json';self.original.write_text(json.dumps(self.case))
        self.output=Path(self.temp.name)/'case-attached.json'
    def test_native_case_provenance_without_truth_upgrade(self):
        before=self.original.read_bytes();result=attach(self.home,self.original,self.run,self.output)
        case=json.loads(self.output.read_text())
        self.assertEqual([],validate_case(case));self.assertEqual(before,self.original.read_bytes())
        self.assertEqual(self.case['claims'],case['claims']);self.assertEqual([],case['entities']);self.assertEqual([],case['relations'])
        self.assertTrue(all(item['confidence']=='unrated' and item['status']=='tool-reported' for item in case['observations']))
        for capture in case['captures']:
            self.assertEqual(capture['sha256'].lower(),digest(self.output.parent/capture['artifact_path']))
            self.assertTrue(capture['original_url'].startswith('file:///'))
        self.assertEqual([],verify_projection_invariants(case,project_case(case)))
    def test_new_evidence_reopens_ready_case_review(self):
        self.case.update(posture='watch-ready',watch={'cadence':'manual fixture'})
        self.case['checks']=[{'id':'CHECK-SPEC','check_type':'watch-specification','status':'passed'},{'id':'CHECK-BASELINE','check_type':'baseline-integrity','status':'passed'}]
        self.original.write_text(json.dumps(self.case))
        attach(self.home,self.original,self.run,self.output)
        revised=json.loads(self.output.read_text())
        self.assertEqual('provisional',revised['posture'])
        self.assertEqual('needs-review',revised['checks'][1]['status'])
    def test_case_location_preserves_existing_relative_paths(self):
        with self.assertRaises(ValueError):attach(self.home,self.original,self.run,Path(self.temp.name)/'other/case.json')
        self.assertFalse((Path(self.temp.name)/'other/case.json').exists())
    def test_partial_run_stays_partial(self):
        run=json.loads((self.run/'run.json').read_text());run['exit_code']=3;(self.run/'run.json').write_text(json.dumps(run))
        result=attach(self.home,self.original,self.run,self.output)
        self.assertEqual('partial-or-failed',result['run_state'])
        self.assertEqual('partial-or-failed',json.loads(self.output.read_text())['sources'][-1]['run_state'])
    def test_existing_case_and_output_are_preserved(self):
        self.output.write_text('existing owner output');before=self.original.read_bytes()
        with self.assertRaises(ValueError):attach(self.home,self.original,self.run,self.output)
        self.assertEqual('existing owner output',self.output.read_text());self.assertEqual(before,self.original.read_bytes())
    def test_outside_run_is_rejected(self):
        with self.assertRaises(ValueError):attach(self.home,self.original,Path(self.temp.name),self.output)
        self.assertFalse(self.output.exists())
    def test_missing_explicit_workbench_fails_without_fallback(self):
        with self.assertRaises(ValueError):workbench(Path(self.temp.name)/'missing')
    def test_file_uri_and_web_capture_rules(self):
        self.assertEqual('file:///E:/local/report.json',canonical_url('file:///E:/local/report.json#view'))
        self.assertEqual('https://example.com/source',canonical_url('https://EXAMPLE.com/source?utm_source=fixture'))
        for value in ['file://remote/report.json','file:///tmp/report.json?query=yes','https://user:secret@example.com']:
            with self.assertRaises(ValueError):canonical_url(value)

if __name__=='__main__':unittest.main()
