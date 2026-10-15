import copy, json, subprocess, sys, tempfile, unittest
from pathlib import Path
S=Path(__file__).resolve().parents[2];sys.path.insert(0,str(S/'scripts'))
from validate_learner_profile import validate_profile, evidence_notes, load_json
from validate_release import validate
class EvidenceContract(unittest.TestCase):
    def setUp(self):self.p=json.loads((S/'examples/progress-and-return/observed-profile.json').read_text(encoding='utf-8'))
    def test_meaningfully_scoped_declared_transfer(self):self.assertEqual(validate_profile(self.p),[])
    def test_blank_template_has_no_learner_history(self):
        p=json.loads((S/'assets/learner-profile.template.json').read_text());self.assertEqual(p['evidence'],[]);self.assertTrue(validate_profile(p))
    def test_old_profile_readable_but_not_qualified(self):
        p=json.loads((S/'examples/progress-and-return/fictional-profile.json').read_text());self.assertEqual(validate_profile(p),[]);self.assertIn('unverified',evidence_notes(p)[0])
    def test_copied_model_is_not_independent(self):
        self.p['evidence'][1]['state']='independent';self.p['evidence'][1]['observation']['support_kind']='copied-model';self.assertTrue(validate_profile(self.p))
    def test_failed_criterion_is_not_transfer(self):self.p['evidence'][1]['observation']['result']='not-met';self.assertTrue(validate_profile(self.p))
    def test_other_mechanism_same_goal_rejected(self):self.p['evidence'][1]['observation']['criterion']='Name three restaurants';self.assertTrue(validate_profile(self.p))
    def test_recognition_cannot_establish_spoken_transfer(self):self.p['evidence'][1]['observation']['modality']='spoken-production';self.assertTrue(validate_profile(self.p))
    def test_identical_prompt_not_transfer(self):self.p['evidence'][1]['observation']['prompt']=self.p['evidence'][0]['observation']['prompt'];self.assertTrue(validate_profile(self.p))
    def test_unknown_prior_and_goal(self):
        for key in ('prior_evidence_id','goal_id'):
            p=copy.deepcopy(self.p);p['evidence'][1]['observation'][key]='absent';self.assertTrue(validate_profile(p))
    def test_prior_must_be_earlier(self):self.p['evidence'][0]['observed_at']=self.p['evidence'][1]['observed_at'];self.assertTrue(validate_profile(self.p))
    def test_impossible_offset_and_future_cutoff(self):
        for stamp in ('2026-10-06T15:00:00-05:99','2026-10-06T15:00:00+24:00','2026-09-01T00:00:00Z'):
            p=copy.deepcopy(self.p);p['updated_at']=stamp;self.assertTrue(validate_profile(p))
    def test_real_offsets(self):
        for stamp in ('2026-10-07T15:00:00-05:30','2026-10-07T15:00:00+05:45'):
            self.p['updated_at']=stamp;self.assertEqual(validate_profile(self.p),[])
    def test_schema_wrongtypes_and_unknown(self):
        for key,value in [('privacy_notes',[]),('unexpected','x')]:
            p=copy.deepcopy(self.p);p[key]=value;self.assertTrue(validate_profile(p))
        self.p['evidence'][0]['notes']={};self.assertTrue(validate_profile(self.p))
    def test_undeclared_language(self):self.p['evidence'][0]['target_language']='Mandarin';self.assertTrue(validate_profile(self.p))
    def test_duplicate_json_key_and_bom(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'profile.json';p.write_text('{"id":1,"id":2}')
            with self.assertRaises(ValueError):load_json(p)
            p.write_text(json.dumps(self.p),encoding='utf-8-sig');self.assertEqual(validate_profile(load_json(p)),[])
    def test_cli_help(self):
        for script in ('validate_release.py','validate_learner_profile.py'):
            r=subprocess.run([sys.executable,'-B',str(S/'scripts'/script),'--help'],capture_output=True);self.assertEqual(r.returncode,0,r.stderr)
    def test_missing_runtime_dependency(self):
        import shutil
        with tempfile.TemporaryDirectory() as d:
            dest=Path(d)/S.name;shutil.copytree(S,dest);(dest/'scripts/validate_learner_profile.py').unlink();self.assertTrue(validate(dest))
    def test_nonobject_eval_case(self):
        import shutil
        with tempfile.TemporaryDirectory() as d:
            dest=Path(d)/S.name;shutil.copytree(S,dest);p=dest/'evals/core-transfer-cases.yaml';j=json.loads(p.read_text());j['cases']=[1];p.write_text(json.dumps(j));self.assertTrue(validate(dest))
if __name__=='__main__':unittest.main()
