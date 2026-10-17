"""Consequential isolated task/custody counterexamples; no provider requests."""
import copy,hashlib,io,json,sys,tempfile,unittest,zipfile,subprocess,contextlib
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import observatory_guardrail as g
import setup_osint as setup
from safe_io import loads,load,write_new,namespace
from osint_bridge import attach,workbench
from test_observatory_guardrail import case

def h(data):return hashlib.sha256(data).hexdigest()

def reviewed_case(root):
    c=case();(root/'report.txt').write_bytes(b'known source');c['captures'][0]['sha256']=h(b'known source')
    (root/'brief.md').write_text('The supplied source says X. [CAP-1]')
    (root/'review.md').write_text('Fictional review of the exact source and narrow supplied-source brief, no independent person or model trial.')
    c['artifacts']=[{'id':'ART-P','artifact_type':'publication-package','path':'brief.md','sha256':g.sha256(root/'brief.md')}]
    c['publication_artifact_id']='ART-P';c['posture']='publication-ready';c['checks']=[]
    for kind in ('provenance','citation-integrity','redaction','editorial-challenge'):
        c['checks'].append({'id':'CHK-'+kind,'check_type':kind,'status':'passed','artifact_id':'ART-P','subject_sha256':g.subject_sha256(c),'reviewer':'Authored fictional test reviewer','method':'Read supplied source and exact brief span','rationale':'Checks the stated document, not live reality or publication authority.','reviewed_at':'2026-07-19T13:00:00Z','evidence_files':[{'path':'review.md','sha256':g.sha256(root/'review.md')}]})
    return c

class ContractCases(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
    def test_exact_ready_and_posture_transition(self):
        c=reviewed_case(self.root);self.assertEqual([],g.validate_case(c,self.root));d=g.subject_sha256(c);c['posture']='reviewable';self.assertEqual(d,g.subject_sha256(c))
    def test_readiness_cannot_survive_changed_question_claim_or_package(self):
        for field in ('question','claim','report'):
            c=reviewed_case(self.root)
            if field=='question':c['question']='A different decision'
            elif field=='claim':c['claims'][0]['statement']='An altered claim'
            else:c['artifacts'][0]['sha256']='a'*64
            self.assertTrue(any('stale' in e for e in g.validate_case(c)),field)
    def test_missing_report_and_changed_review_evidence(self):
        c=reviewed_case(self.root);(self.root/'brief.md').unlink();self.assertTrue(g.validate_case(c,self.root))
        c=reviewed_case(self.root);(self.root/'review.md').write_text('changed');self.assertTrue(g.validate_case(c,self.root))
    def test_failed_or_unbound_review_cannot_pass(self):
        c=reviewed_case(self.root);c['checks'].append(dict(c['checks'][0],id='FAILED',status='failed'));self.assertTrue(g.validate_case(c))
        c=reviewed_case(self.root);c['checks'][0].pop('subject_sha256');self.assertTrue(g.validate_case(c))
    def test_review_before_access_rejected_valid_crosszone_accepted(self):
        c=reviewed_case(self.root);c['checks'][0]['reviewed_at']='2026-07-19T11:59:00Z';self.assertTrue(g.validate_case(c))
        c['checks'][0]['reviewed_at']='2026-07-19T08:30:00-04:00';self.assertEqual([],g.validate_case(c))
    def test_provisional_case_does_not_require_review_ceremony(self):self.assertEqual([],g.validate_case(case()))
    def test_malformed_types_controlled(self):
        for key,value in [('phase',[]),('checks',None),('sources','bad'),('posture',{})]:
            c=case();c[key]=value;self.assertTrue(g.validate_case(c))
        c=case();c['claims'][0]['capture_ids']=[{}];self.assertTrue(g.validate_case(c))
    def test_typed_references_and_relation_endpoints(self):
        c=case();c['captures'][0]['source_ids']=['CLM-1'];self.assertTrue(g.validate_case(c))
        c=case();c['relations']=[{'id':'REL','from_id':'SRC-1','to_id':'MISSING','relation_type':'reports'}];self.assertTrue(g.validate_case(c))
    def test_readiness_flags_require_booleans(self):
        for value in ('true',1,[],{}):
            c=case();c['claims'][0]['high_risk']=value;self.assertTrue(g.validate_case(c))
            c=case();c['entities']=[{'id':'E','resolution_status':'collision','material_to_publication':value}];self.assertTrue(g.validate_case(c))
        c=case();c['claims'][0]['high_risk']=False;self.assertEqual([],g.validate_case(c))
    def test_valid_heterogeneous_provenance(self):
        c=case();c['assessments']=[{'id':'ASM','summary':'Bounded','provenance_ids':['CLM-1','CAP-1']}];self.assertEqual([],g.validate_case(c))
    def test_raw_ambiguity_and_nonfinite_rejected(self):
        for raw in ['{"x":1,"x":2}','{"x":1,"\\u0078":2}','{"x":NaN}','{"x":1e400}','['*100+'0'+']'*100]:
            with self.assertRaises(ValueError):loads(raw)
        self.assertEqual({'x':1},loads('\ufeff{"x":1}'))
    def test_clock_contract(self):
        for raw in ['2026-07-19T12:00:00-05:99','2026-07-19T12:00:00-00:00','2026-02-30T12:00:00Z','2026-07-19T24:00:00Z']:
            c=case();c['captures'][0]['retrieved_at']=raw;self.assertTrue(g.validate_case(c),raw)
        c=case();c['captures'][0]['retrieved_at']='2026-07-19T18:00:00+05:30';self.assertEqual([],g.validate_case(c))
    def test_clock_range_is_host_independent_without_implicit_date_rollover(self):
        for raw in ['2026-07-19T24:00:00Z','2026-07-19T24:00:00.000000+05:30','2026-07-19T24:01:00Z','2026-07-19T23:60:00Z','2026-07-19T23:59:60Z']:
            errors=[];self.assertIsNone(g.parse_time(raw,'event_start',errors,'E'),raw);self.assertTrue(errors,raw)
        for raw,date,hour in [('2026-07-19T23:59:59Z','2026-07-19',23),('2026-07-20T00:00:00Z','2026-07-20',0),('2026-07-20T00:00:00+05:30','2026-07-20',0),('2026-07-19T00:00:00.000001-05:30','2026-07-19',0)]:
            errors=[];parsed=g.parse_time(raw,'event_start',errors,'E');self.assertEqual([],errors,raw);self.assertEqual(date,parsed.date().isoformat(),raw);self.assertEqual(hour,parsed.hour,raw)
    def test_cutoff_distinguishes_retrieval_and_scheduled_event(self):
        c=case();c['evidence_as_of']='2026-07-19T11:59:00Z';self.assertTrue(g.validate_case(c))
        c['evidence_as_of']='2026-07-19T13:00:00Z';c['events']=[{'id':'E','event_start':'2026-07-20T12:00:00Z','status':'scheduled'}];self.assertEqual([],g.validate_case(c))
    def test_every_clock_and_actual_instant_order(self):
        c=case();c['captures'][0]['published_at']='2026-07-19T06:00:00-05:00';c['observations']=[{'id':'O','observed_at':'2026-07-19T13:00:00+02:00'}]
        p=g.project_case(c);clocks=[x['time_kind'] for x in p['timeline']['items']];self.assertIn('retrieved_at',clocks);self.assertIn('published_at',clocks);self.assertIn('observed_at',clocks)
        self.assertEqual([],g.verify_projection_invariants(c,p))
    def test_projection_omission_and_self_certification(self):
        c=case();p=g.project_case(c);p['ledger']['items']=[];self.assertTrue(g.verify_projection_invariants(c,p))
        p=g.project_case(c)
        for view in [p['ledger']['items'],p['graph']['nodes'],p['timeline']['items']]:
            for x in view:
                if x['id']=='CLM-1':x['confidence']='certain'
        p['registry']['CLM-1']['confidence']='certain';self.assertTrue(g.verify_projection_invariants(c,p))
    def test_projection_geometry_and_edge_changed(self):
        c=case();c['events']=[{'id':'E','location':{'latitude':1,'longitude':2}}];p=g.project_case(c);p['map']['features'][0]['geometry']['coordinates']=[20,10];self.assertTrue(g.verify_projection_invariants(c,p))
    def test_delta_deletion_is_not_disproof(self):
        c=case();d=copy.deepcopy(c);d['claims']=[];classes=g.delta_report(c,d)['classes'];self.assertIn('CLM-1',classes['no_longer_represented']);self.assertNotIn('CLM-1',classes['newly_unsupported'])
    def test_freshness_visible_and_unrelated_case_rejected(self):
        c=case();d=copy.deepcopy(c);d['captures'][0]['retrieved_at']='2026-07-19T14:00:00Z';self.assertIn('CAP-1',g.delta_report(c,d)['classes']['currentness_changed']);d['case_id']='OTHER'
        with self.assertRaises(ValueError):g.delta_report(c,d)
    def test_support_checks_exact_capture_excerpt(self):
        c=reviewed_case(self.root);c['posture']='reviewable';c['claims'][0]['support']=[{'capture_id':'CAP-1','relation':'supports','locator':'paragraph1','excerpt':'known source','rationale':'Scope-bound source text'}];self.assertEqual([],g.validate_case(c,self.root));c['claims'][0]['support'][0]['excerpt']='not present';self.assertTrue(g.validate_case(c,self.root))
    def test_existing_output_preserved(self):
        p=self.root/'owner.json';p.write_bytes(b'owner')
        with self.assertRaises(ValueError):g.write_json(p,{'x':1})
        self.assertEqual(b'owner',p.read_bytes())
    def test_capture_escape_and_tamper(self):
        c=reviewed_case(self.root);c['posture']='reviewable';c['captures'][0]['artifact_path']='../outside.txt';self.assertTrue(g.validate_case(c,self.root))
        c=reviewed_case(self.root);(self.root/'report.txt').write_text('changed');self.assertTrue(g.validate_case(c,self.root))
    def test_url_preserves_query_order_and_ipv6(self):
        self.assertEqual('https://[::1]/a?x=2&x=1',g.canonical_url('https://[::1]:443/a?x=2&x=1&utm_source=t'))
    def test_cli_malformed_input_controlled_and_no_write(self):
        p=self.root/'bad.json';p.write_text('{"format":{},"phase":[]}');out=self.root/'projection'
        command=[sys.executable,'-B',str(Path(g.__file__)),'project',str(p),str(out)];r=subprocess.run(command,capture_output=True,text=True);self.assertEqual(1,r.returncode);self.assertNotIn('Traceback',r.stderr);self.assertFalse(out.exists())

class InstallerCases(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
    def test_archive_bad_names_preflight(self):
        for index,names in enumerate([['root/a','root/A'],['root/a','root/a/b'],['root/a/','root/a'],['root/A/','root/a/b'],['root/A/b','root/a/c'],['root/../outside'],['root/CON.txt'],['root/a:stream'],['root/x.']]):
            archive=self.root/(str(index)+'.zip')
            with zipfile.ZipFile(archive,'w') as z:
                for n in names:z.writestr(n,'data')
            output=self.root/('out'+str(index))
            with self.assertRaises(ValueError):setup.unpack(archive,output)
            self.assertFalse(output.exists())
    def test_archive_valid_and_existing_source_preserved(self):
        archive=self.root/'good.zip'
        with zipfile.ZipFile(archive,'w') as z:z.writestr('root/LICENSE','original');z.writestr('root/module/a.py','pass')
        out=self.root/'source';setup.unpack(archive,out);self.assertEqual('original',(out/'LICENSE').read_text())
        with self.assertRaises(ValueError):setup.unpack(archive,out)
    def test_dry_run_without_uv_or_network(self):
        with patch.object(setup.urllib.request,'urlopen',side_effect=AssertionError('No network')),contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(0,setup.main(['--home',str(self.root/'new'),'--uv','','--dry-run']))
        self.assertFalse((self.root/'new').exists());self.assertIn('provider_queries',output.getvalue())
    def test_nonempty_independent_home_preserved(self):
        home=self.root/'owner';home.mkdir();(home/'owner.txt').write_text('retain')
        with contextlib.redirect_stderr(io.StringIO()):result=setup.main(['--home',str(home),'--uv','unused'])
        self.assertEqual(2,result);self.assertEqual(['owner.txt'],[p.name for p in home.iterdir()])
    def test_failed_new_install_has_resumable_receipt_and_no_complete_claim(self):
        home=self.root/'new'
        with patch.object(setup.subprocess,'run',side_effect=OSError('isolated unavailable tool')),contextlib.redirect_stderr(io.StringIO()):result=setup.main(['--home',str(home),'--tools','shodan','--uv','fake'])
        self.assertEqual(2,result);receipt=load(home/'setup-receipt.json');self.assertEqual('partial-or-failed',receipt['state'])
        with self.assertRaises(ValueError):workbench(home)
        with patch.object(setup.subprocess,'run',return_value=subprocess.CompletedProcess([],0)),contextlib.redirect_stdout(io.StringIO()):self.assertEqual(0,setup.main(['--home',str(home),'--tools','shodan','--uv','fake','--resume']))
        self.assertEqual('complete',load(home/'setup-receipt.json')['state'])
    def test_changed_source_or_plan_prevents_resume(self):
        home=self.root/'new'
        with patch.object(setup.subprocess,'run',side_effect=OSError('unavailable')),contextlib.redirect_stderr(io.StringIO()):setup.main(['--home',str(home),'--tools','shodan','--uv','fake'])
        original=(home/'osint.py').read_bytes();(home/'osint.py').write_text('owner edit')
        with contextlib.redirect_stderr(io.StringIO()):self.assertEqual(2,setup.main(['--home',str(home),'--tools','shodan','--uv','fake','--resume']))
        self.assertEqual('owner edit',(home/'osint.py').read_text())

if __name__=='__main__':unittest.main()
