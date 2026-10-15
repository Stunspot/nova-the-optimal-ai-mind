import copy,json,os,subprocess,sys,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).absolute().parents[1]))
from ledgerlib import *
from io_contract import atomic_bytes
from snapshotlib import snapshot
from fixtures import fixture
NOW=datetime(2026,10,6,12,tzinfo=timezone.utc)
class LedgerTests(unittest.TestCase):
 def setUp(self):self.d=fixture()
 def bad(self,d):self.assertTrue(validate(d,now=NOW))
 def test_valid_adoption_preserves_and_replays(self):
  prior=copy.deepcopy(self.d);new=adopt(self.d,'P1',NOW);self.assertEqual(self.d,prior);self.assertEqual(new['baseline_history'],[prior['baseline']]);self.assertIn('until 16:00',new['baseline']['text']);self.assertEqual(validate(new,prior,NOW),[]);self.assertIsNone(eligible_patch(new,new['patches'][0],now=NOW)[1])
 def test_source_hash_binds(self):
  self.d['sources'][0]['supports'][0]['claim']='Other claim';self.bad(self.d)
 def test_approval_content_binds(self):
  self.d['patches'][0]['after']='until 15:00';self.assertIn('binding',eligible_patch(self.d,self.d['patches'][0],now=NOW)[1])
 def test_withdrawal_wins(self):
  a=copy.deepcopy(self.d['approvals'][0]);a.update(id='A2',action='withdraw',at='2026-09-03');self.d['approvals'].append(a);self.assertIn('withdraw',eligible_patch(self.d,self.d['patches'][0],now=NOW)[1])
 def test_approval_order_retained(self):
  a=copy.deepcopy(self.d['approvals'][0]);a.update(id='A2',action='withdraw');self.d['approvals'].append(a);new=copy.deepcopy(self.d);new['approvals'].reverse();new['revision']+=1;self.assertTrue(validate(new,self.d,NOW))
 def test_expiry(self):
  self.d['approvals'][0]['expires_at']='2026-10-01';self.assertIn('expired',eligible_patch(self.d,self.d['patches'][0],now=NOW)[1])
 def test_local_scope_does_not_adopt(self):
  self.d['approvals'][0]['scope']='local-brief';self.assertIsNone(eligible_patch(self.d,self.d['patches'][0],now=NOW)[1]);self.assertRaises(LedgerError,adopt,self.d,'P1',NOW)
 def test_stale_patch(self):
  new=adopt(self.d,'P1',NOW);self.assertRaises(LedgerError,adopt,new,'P1',NOW)
 def test_before_mismatch(self):
  self.d['patches'][0]['before']='missing';self.d['approvals'][0]['patch_sha256']=patch_hash(self.d['patches'][0]);self.assertIn('starting span',eligible_patch(self.d,self.d['patches'][0],now=NOW)[1])
 def test_ambiguous_span(self):
  self.d['baseline']['text']+=' until 17:00';self.d['patches'][0]['base_sha256']=baseline_hash(self.d);self.d['approvals'][0].update(base_sha256=baseline_hash(self.d),patch_sha256=patch_hash(self.d['patches'][0]));self.assertIn('starting span',eligible_patch(self.d,self.d['patches'][0],now=NOW)[1])
 def test_retired_patch(self):
  self.d['patches'][0]['status']='retired';self.assertIn('status',eligible_patch(self.d,self.d['patches'][0],now=NOW)[1])
 def test_false_adopted_baseline(self):
  new=adopt(self.d,'P1',NOW);new['baseline']['text']+=' unsupported change';self.bad(new)
 def test_retained_history(self):
  new=copy.deepcopy(self.d);new['baseline']['text']='Changed';new['revision']=2;self.assertTrue(validate(new,self.d,NOW))
 def test_removed_evidence(self):
  new=copy.deepcopy(self.d);new['sources']=[];new['patches']=[];new['candidates']=[];new['approvals']=[];new['revision']=2;self.assertTrue(validate(new,self.d,NOW))
 def test_bad_shapes(self):
  for key,value in [('before',[]),('after',{}),('mechanism',None),('base_version',True)]:
   with self.subTest(key=key):d=copy.deepcopy(self.d);d['patches'][0][key]=value;self.bad(d)
 def test_date_profile(self):
  for x in ['2026-02-30','2026-01-01T00:00:00+00:99','2026-01-01T00:00:00+24:00','2026-01-01T00:00:60Z','2026-01-01T00:00:00-00:00']:
   with self.subTest(x=x):self.assertRaises(LedgerError,moment,x,'test')
  self.assertEqual(moment('2024-02-29','test').day,29)
 def test_future_approval(self):self.d['approvals'][0]['at']='2099-01-01';self.bad(self.d)
 def test_unknown_cutoff_not_current(self):
  self.d['patches'][0]['result_as_of']='unknown';self.assertIn('Known',eligible_patch(self.d,self.d['patches'][0],now=NOW)[1])
 def test_unread_source_not_qualified(self):
  self.d['sources'][0]['access_status']='not_examined';self.d['patches'][0]['source_hashes']['S1']=identity({k:v for k,v in self.d['sources'][0].items() if k!='status'});self.assertIn('inspected',eligible_patch(self.d,self.d['patches'][0],now=NOW)[1])
 def test_source_too_new(self):
  self.d['sources'][0]['publication_date']='2026-09-03';self.d['patches'][0]['source_hashes']['S1']=identity({k:v for k,v in self.d['sources'][0].items() if k!='status'});self.assertIn('later',eligible_patch(self.d,self.d['patches'][0],now=NOW)[1])
 def test_qualify_nonobject(self):self.assertTrue(qualify([]))
 def test_watch_decimal_and_unknown(self):
  self.assertTrue(watch_result('9007199254740993','gt','9007199254740992')['triggered']);self.assertIsNone(watch_result(None,'gte','2')['triggered'])
  for x in ['NaN','Infinity','1e999999','-inf']:self.assertRaises(LedgerError,watch_result,x,'gte','2')
 def test_review_overflow(self):self.assertRaises(LedgerError,next_recheck,date(9999,12,31),1)
 def test_strict_json(self):
  for text in ['{"x":1,"x":2}','[NaN]','[Infinity]','\ufeff\ufeff{}','['*65+'0'+']'*65]:self.assertRaises(LedgerError,strict,text)
  self.assertEqual(dumps(strict('{"x":9007199254740993.12345}')),'{"x":9007199254740993.12345}')
 def test_extension_preserved(self):
  self.d['extension']={'unknown_field':Decimal('1.234567890123456789')};new=adopt(self.d,'P1',NOW);self.assertEqual(new['extension'],self.d['extension'])
 def test_cli_no_clobber_and_brief(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);ledger=p/'ledger.json';write(ledger,self.d);original=ledger.read_bytes()
   for cmd in [('citations',str(ledger),str(ledger)),('brief',str(ledger),str(ledger)),('adopt',str(ledger),'P1',str(ledger))]:
    r=subprocess.run([sys.executable,'-B',str(ROOT/'scripts/answerlayer.py'),*cmd],capture_output=True,text=True);self.assertNotEqual(r.returncode,0);self.assertEqual(ledger.read_bytes(),original)
   r=subprocess.run([sys.executable,'-B',str(ROOT/'scripts/answerlayer.py'),'brief',str(ledger),str(p/'brief.md'),'--patch','P1'],capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stdout+r.stderr);self.assertIn('Synthetic', (p/'brief.md').read_text())
 def test_exclusive_write_failure(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'out'
   with patch('io_contract.os.link',side_effect=OSError('injected publication failure')):self.assertRaises(OSError,atomic_bytes,p,b'new')
   self.assertFalse(p.exists());self.assertEqual(list(p.parent.iterdir()),[])
 def test_snapshot_full_tree_and_failure(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)/'case';root.mkdir();(root/'snapshots').mkdir();(root/'snapshots/keep.txt').write_text('keep');(root/'empty').mkdir();out=Path(tmp)/'out.zip'
   with patch('snapshotlib.zipfile.ZipFile.writestr',side_effect=OSError('injected write failure')):self.assertRaises(OSError,snapshot,root,out)
   self.assertFalse(out.exists());snapshot(root,out)
   with zipfile.ZipFile(out) as z:self.assertEqual(z.read('snapshots/keep.txt'),b'keep');self.assertIn('empty/',z.namelist())
   self.assertRaises(LedgerError,snapshot,root,out)
 def test_snapshot_link_root(self):
  with tempfile.TemporaryDirectory() as tmp:
   real=Path(tmp)/'real';real.mkdir();link=Path(tmp)/'link'
   if os.name=='nt':
    r=subprocess.run(['cmd','/c','mklink','/J',str(link),str(real)],capture_output=True);self.assertEqual(r.returncode,0)
   else:link.symlink_to(real,target_is_directory=True)
   try:self.assertRaises(LedgerError,snapshot,link,Path(tmp)/'out.zip')
   finally:link.rmdir() if os.name=='nt' else link.unlink()
 def test_migration_preserves_original_assertions(self):
  oldpath=ROOT/'examples/legacy-v1/reality-ledger.json';original=input_bytes(oldpath);old=strict(original.decode('utf-8-sig'));new=migrate(old,original,oldpath.name);self.assertEqual(new['migration']['source_sha256'],hashlib.sha256(original).hexdigest());self.assertEqual(new['approvals'],[]);self.assertEqual(validate(new,now=NOW),[])
 def test_noop_not_adopted(self):
  self.d['patches'][0]['after']=self.d['patches'][0]['before'];self.assertIn('No textual change',eligible_patch(self.d,self.d['patches'][0],now=NOW)[1])
 def test_source_origin_cycle(self):
  self.d['sources'][0]['origin_id']='S1';self.bad(self.d)
 def test_exactly_one_bom_at_file_boundary(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'one.json';p.write_bytes(b'\xef\xbb\xbf{}');self.assertEqual(load(p),{})
   p.write_bytes(b'\xef\xbb\xbf\xef\xbb\xbf{}');self.assertRaises(LedgerError,load,p)
if __name__=='__main__':unittest.main()
