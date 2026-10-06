"""Tests allowlisted registry reads, query privacy and actual private service."""
import json,subprocess,sys,unittest,urllib.request,urllib.error
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlsplit,parse_qs
sys.path.insert(0,str(Path(__file__).resolve().parent))
import host
class KnowledgeDispatchTest(unittest.TestCase):
 def setUp(self):host.OPS=Path('canonical/nova_estate.py');host.ESTATE=Path('approved/estate')
 def test_mutations_are_not_commands(self):
  with patch('host.subprocess.run') as run:
   for command in ('capture','unpin','forget','rebuild','restore-test','put-person','views'):
    with self.assertRaises(ValueError):host.read_owner(command,{})
   run.assert_not_called()
 def test_query_in_stdin_only_and_native_failure_preserved(self):
  with patch('host.subprocess.run',return_value=subprocess.CompletedProcess([],11,'{"status":"unavailable","reason":"exact binding mismatch"}','')) as run:
   result=host.read_owner('search',{'query':'PRIVATE-QUERY'})
   self.assertNotIn('PRIVATE-QUERY',' '.join(run.call_args.args[0]));self.assertIn('PRIVATE-QUERY',run.call_args.kwargs['input']);self.assertEqual(result['native']['status'],'unavailable');self.assertEqual(result['scope'],['public','personal','private'])
 def test_project_scope_is_explicit(self):
  with patch('host.subprocess.run',return_value=subprocess.CompletedProcess([],0,'{"pins":[]}','')) as run:
   host.read_owner('pins',{});self.assertEqual(json.loads(run.call_args.kwargs['input']),{})
   host.read_owner('pins',{'project':'project-a'});self.assertEqual(json.loads(run.call_args.kwargs['input']),{'project':'project-a'})
   host.read_owner('pins',{'all_projects':True});self.assertEqual(json.loads(run.call_args.kwargs['input']),{'all_projects':True})
 def test_non_json_failure_retains_read_envelope(self):
  with patch('host.subprocess.run',return_value=subprocess.CompletedProcess([],2,'','Unavailable estate')):
   result=host.read_owner('status',{})
   self.assertTrue(result['read_only']);self.assertEqual(result['scope'],['public','personal','private']);self.assertEqual(result['native']['status'],'unavailable');self.assertEqual(result['native']['diagnostic'],'Unavailable estate')
 def test_missing_owner_bundle_rejected_before_launch(self):
  with self.assertRaisesRegex(ValueError,'incomplete or obsolete'):
   host.validate_owner_bundle(Path('missing/skills/nova-operations/scripts/nova_estate.py'))
 def test_operations_json_error_is_preserved(self):
  error='{"format":"nova-emergent-operation-error/v1","code":"estate_error","message":"missing owner"}'
  with patch('host.subprocess.run',return_value=subprocess.CompletedProcess([],2,'',error)):
   result=host.read_owner('pins',{})
   self.assertEqual(result['native']['code'],'estate_error');self.assertEqual(result['native']['message'],'missing owner')
 def test_empty_note_scope_reports_stored_count_without_reading_private_content(self):
  replies=[subprocess.CompletedProcess([],0,'{"ok":true,"records":[]}',''),subprocess.CompletedProcess([],0,'{"record_count":20}','')]
  with patch('host.subprocess.run',side_effect=replies) as run:
   result=host.read_owner('notes',{})
   self.assertEqual(result['coverage']['stored_record_count'],20)
   self.assertEqual(result['native']['records'],[])
   self.assertEqual(result['scope'],['public','personal','private'])
   self.assertEqual(run.call_args.args[0][-2:],['status','--json'])
if __name__=='__main__':unittest.main()
