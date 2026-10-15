"""Consequential Officefile v2 regression contrasts; synthetic local data only."""
import copy, hashlib, json, sys, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from init_officefile import initialize
from validate_officefile import validate_officefile
from inspect_office_artifacts import inspect_officefile
from officefile_relationships import current_basis, basis_digest
from capture_artifact_binding import capture
from migrate_officefile import migrate


def load(path):return json.loads(path.read_text(encoding='utf-8'))
def save(path,data):path.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8',newline='\n')
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def byteset(root):return {p.relative_to(root).as_posix():p.read_bytes()for p in root.rglob('*')if p.is_file()}


def family(root):
    initialize(root)
    (root/'sources/budget.md').write_text('Approved budget: USD100.\n',encoding='utf-8')
    sources={'S':{'source_id':'S','path':'sources/budget.md','source_type':'notes','custody_status':'user_supplied','content_status':'authoritative'}}
    ledger={'L':{'item_id':'L','kind':'metric','value':'USD100','source_ids':['S'],'source_status':'sourced'},'U':{'item_id':'U','kind':'term','value':'unrelated','source_ids':[],'source_status':'illustrative'}}
    arts={}
    for aid in ['A','B','C']:
        (root/f'output/{aid}.md').write_text('# Budget\n\nUSD100\n',encoding='utf-8')
        arts[aid]={'artifact_id':aid,'path':f'output/{aid}.md','format':'MD','role':'editable_source'if aid=='A'else'derivative','editable':True,'status':'produced','check_evidence':[],'canonical_source_id':None if aid=='A'else'A'if aid=='B'else'B'}
    arts['A'].update(source_ids=['S'],ledger_item_ids=['L'])
    for aid in arts:arts[aid]['input_basis']=current_basis(root,aid,arts,sources,ledger)
    save(root/'sources/manifest.json',{'format':'officecraft-source-manifest/v1','sources':list(sources.values())})
    save(root/'state/content-ledger.json',{'format':'officecraft-content-ledger/v1','items':list(ledger.values())})
    write_register(root,arts)
    return arts,sources,ledger


def write_register(root,arts):save(root/'state/artifact-register.json',{'format':'officecraft-artifact-register/v2','artifacts':list(arts.values())})


class RevisionTests(unittest.TestCase):
    def assertValid(self,root):
        r=validate_officefile(root);self.assertTrue(r['valid'],r['errors'])
    def assertInvalid(self,root,needle):
        r=validate_officefile(root);self.assertFalse(r['valid']);self.assertTrue(any(needle in e for e in r['errors']),r['errors'])

    def test_graph_legitimate_planned_then_cycle_duplicate_and_missing_parent(self):
        with tempfile.TemporaryDirectory()as t:
            root=Path(t)/'office';arts,_,_=family(root);self.assertValid(root)
            for mutate,needle in [(lambda x:x['A'].update(canonical_source_id='A'),'cycle'),(lambda x:x['A'].update(canonical_source_id='C'),'cycle'),(lambda x:x['B'].update(path='output/A.md'),'duplicate'),(lambda x:x['B'].update(canonical_source_id=None),'requires its canonical')]:
                bad=copy.deepcopy(arts);mutate(bad);write_register(root,bad);self.assertInvalid(root,needle)
            planned=copy.deepcopy(arts);planned['B'].update(status='planned',canonical_source_id='FUTURE',input_basis=None);planned.pop('C');write_register(root,planned);self.assertValid(root)

    def test_source_ledger_and_transitive_change_invalidate_only_actual_basis(self):
        with tempfile.TemporaryDirectory()as t:
            root=Path(t)/'office';arts,sources,ledger=family(root);self.assertValid(root)
            ledger['U']['value']='unrelated changed';save(root/'state/content-ledger.json',{'format':'officecraft-content-ledger/v1','items':list(ledger.values())});self.assertValid(root)
            ledger['L']['value']='USD200';save(root/'state/content-ledger.json',{'format':'officecraft-content-ledger/v1','items':list(ledger.values())});self.assertInvalid(root,'basis')
            ledger['L']['value']='USD100';save(root/'state/content-ledger.json',{'format':'officecraft-content-ledger/v1','items':list(ledger.values())})
            (root/'sources/budget.md').write_text('Approved budget: USD200.\n',encoding='utf-8');self.assertInvalid(root,'basis')
            (root/'sources/budget.md').write_text('Approved budget: USD100.\n',encoding='utf-8');self.assertValid(root)
            (root/'output/A.md').write_text('# Changed analytical source\nUSD200\n',encoding='utf-8');self.assertInvalid(root,'artifact B: production input basis');self.assertInvalid(root,'artifact C: production input basis')

    def test_migration_preserves_original_outputs_history_and_refuses_reuse(self):
        with tempfile.TemporaryDirectory()as t:
            root=Path(t)/'old';family(root)
            for name,fmt in [('state/artifact-register.json','officecraft-artifact-register/v1'),('review/officecraft-review.json','officecraft-review/v1')]:
                x=load(root/name);x['format']=fmt;save(root/name,x)
            original=byteset(root);new=Path(t)/'new';migrate(root,new);self.assertEqual(original,byteset(root))
            for name in ['output/A.md','output/B.md','output/C.md']:self.assertEqual(original[name],(new/name).read_bytes())
            self.assertEqual(original['review/officecraft-review.json'],(new/'history/pre-v2/review/officecraft-review.json').read_bytes());self.assertValid(new)
            self.assertEqual({'working'},{x['status']for x in load(new/'state/artifact-register.json')['artifacts']})
            with self.assertRaises(ValueError):migrate(root,new)
            self.assertEqual(original,byteset(root))

    def test_capture_records_current_inputs_without_rewriting_register_or_claiming_review(self):
        with tempfile.TemporaryDirectory()as t:
            root=Path(t)/'office';family(root);before=byteset(root);binding=capture(root,'B','produced','fictional build record')
            self.assertEqual(before,byteset(root));self.assertEqual(binding['sha256'],digest(root/'output/B.md'));self.assertEqual(binding['input_basis']['artifacts']['A']['sha256'],digest(root/'output/A.md'));self.assertNotIn('reviewed',binding)
    def test_conditional_review_is_useful_but_approval_requires_scoped_closure(self):
        with tempfile.TemporaryDirectory()as t:
            root=Path(t)/'office';arts,sources,ledger=family(root)
            save(root/'review/inspection.json',inspect_officefile(root));arts['B'].update(status='reviewed',check_evidence=[{'path':'review/inspection.json'}]);write_register(root,arts)
            brief=load(root/'state/brief.json');brief.update(state='reviewable',approval_owner='Casey');save(root/'state/brief.json',brief)
            binding={'artifact_id':'B','sha256':digest(root/'output/B.md'),'input_basis_sha256':basis_digest(arts['B'])}
            condition={'id':'C1','statement':'Confirm budget authority before client use','artifact_ids':['B'],'intended_use':'client briefing','status':'open'}
            entry={'record_version':'officecraft-review-entry/v2','status':'PASS_WITH_CONDITIONS','officefile_state':'reviewable','intended_use':'client briefing','reviewer_role':'fictional operator','reviewed_at':'2026-07-21T13:00:00Z','reviewed_artifacts':[binding],'material_findings':[],'conditions':[condition]}
            review={'format':'officecraft-review/v2','operator_review':entry,'independent_review':{'status':'not_run'},'approval_records':[]};save(root/'review/officecraft-review.json',review);self.assertValid(root)
            arts['B']['status']='approved';write_register(root,arts);approval={**binding,'approval_owner':'Casey','authority_kind':'user','approved_use':'client briefing','approved_at':'2026-07-21T14:00:00Z'};review['approval_records']=[approval];save(root/'review/officecraft-review.json',review);self.assertInvalid(root,'approved artifact lacks')
            condition.update(status='met',resolution_evidence='fictional owner budget confirmation');save(root/'review/officecraft-review.json',review);self.assertValid(root)
            condition.update(status='residual_accepted',acceptance={'owner':'Another person','authority_kind':'user','approved_use':'client briefing','accepted_at':'2026-07-21T14:00:00Z','rationale':'Accept stated unresolved budget risk'});save(root/'review/officecraft-review.json',review);self.assertInvalid(root,'approved artifact lacks')
            condition['acceptance']['owner']='Casey';save(root/'review/officecraft-review.json',review);self.assertValid(root)
            entry['status']='PASS';save(root/'review/officecraft-review.json',review);self.assertInvalid(root,'unconditional PASS')
            entry['status']='PASS_WITH_CONDITIONS';entry['material_findings']=[{'id':'F1','status':'open','required_disposition':'REVISE','finding':'Incorrect value'}];save(root/'review/officecraft-review.json',review);self.assertInvalid(root,'open material finding')
            entry['material_findings']=[];approval['approved_use']='public campaign';save(root/'review/officecraft-review.json',review);self.assertInvalid(root,'approved artifact lacks')
            approval['approved_use']='client briefing';save(root/'review/officecraft-review.json',review)
            ledger['L']['value']='USD200';save(root/'state/content-ledger.json',{'format':'officecraft-content-ledger/v1','items':list(ledger.values())})
            for aid in arts:arts[aid]['input_basis']=current_basis(root,aid,arts,sources,ledger)
            write_register(root,arts);self.assertInvalid(root,'reviewed production basis differs')

    def test_current_reviews_compose_by_scope_without_bypassing_constraints(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)/'office';arts,_,_=family(root)
            save(root/'review/inspection.json',inspect_officefile(root))
            arts['B'].update(status='approved',check_evidence=[{'path':'review/inspection.json'}]);write_register(root,arts)
            brief=load(root/'state/brief.json');brief.update(state='reviewable',approval_owner='Casey');save(root/'state/brief.json',brief)
            bindings={aid:{'artifact_id':aid,'sha256':digest(root/f'output/{aid}.md'),'input_basis_sha256':basis_digest(arts[aid])} for aid in arts}
            passed={'record_version':'officecraft-review-entry/v2','status':'PASS','officefile_state':'reviewable','intended_use':'client briefing','reviewer_role':'fictional reviewer','reviewed_at':'2026-07-21T13:00:00Z','reviewed_artifacts':[bindings['B']],'material_findings':[],'conditions':[]}
            conditional=copy.deepcopy(passed);conditional.update(status='PASS_WITH_CONDITIONS',conditions=[{'id':'QUOTE','statement':'Confirm the budget before client use','artifact_ids':['B'],'intended_use':'client briefing','status':'open'}])
            approval={**bindings['B'],'approval_owner':'Casey','authority_kind':'user','approved_use':'client briefing','approved_at':'2026-07-21T14:00:00Z'}
            def check(name,operator,independent,expected,status='approved'):
                with self.subTest(name=name):
                    arts['B']['status']=status;write_register(root,arts)
                    review={'format':'officecraft-review/v2','operator_review':operator,'independent_review':independent,'approval_records':[approval] if status=='approved' else []}
                    save(root/'review/officecraft-review.json',review);result=validate_officefile(root)
                    self.assertEqual(result['valid'],expected,result['errors'])
            check('useful conditional review',passed,conditional,True,'reviewed')
            check('operator pass cannot bypass independent open',passed,conditional,False)
            check('independent pass cannot bypass operator open',conditional,passed,False)
            closed=copy.deepcopy(conditional);closed['conditions'][0].update(status='met',resolution_evidence='fictional actual budget confirmation')
            check('both current constraints closed',passed,closed,True)
            accepted=copy.deepcopy(conditional);accepted['conditions'][0].update(status='residual_accepted',acceptance={'owner':'Casey','authority_kind':'user','approved_use':'client briefing','accepted_at':'2026-07-21T14:00:00Z','rationale':'Accept the identified budget uncertainty'})
            check('same owner accepts scoped residual',passed,accepted,True)
            wrong=copy.deepcopy(accepted);wrong['conditions'][0]['acceptance']['owner']='Another owner'
            check('another pass cannot borrow wrong owner acceptance',passed,wrong,False)
            for disposition in ['REVISE','BLOCKED']:
                rejected=copy.deepcopy(passed);rejected['status']=disposition
                check(disposition+' defeats current approved claim',passed,rejected,False)
                check(disposition+' defeats current reviewed claim',passed,rejected,False,'reviewed')
                check(disposition+' remains effective in operator field',rejected,passed,False)
                other=copy.deepcopy(rejected);other['intended_use']='public campaign'
                check(disposition+' for another use does not defeat client use',passed,other,True)
                old=copy.deepcopy(rejected);old['reviewed_artifacts'][0]['sha256']='0'*64
                check(disposition+' for earlier bytes is not current evidence',passed,old,True)
            other_use=copy.deepcopy(conditional);other_use['intended_use']='public campaign';other_use['conditions'][0]['intended_use']='public campaign'
            check('unrelated-use condition stays scoped',passed,other_use,True)
            other_artifact=copy.deepcopy(conditional);other_artifact['reviewed_artifacts']=[bindings['A']];other_artifact['conditions'][0]['artifact_ids']=['A']
            check('unrelated-artifact condition stays scoped',passed,other_artifact,True)
            check('not-run is neutral',passed,{'status':'not_run'},True)

if __name__=='__main__':unittest.main()