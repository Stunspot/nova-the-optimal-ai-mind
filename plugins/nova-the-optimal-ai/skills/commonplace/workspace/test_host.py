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
   result=host.read_owner('people',{'query':'PRIVATE-QUERY','include_private':False})
   self.assertNotIn('PRIVATE-QUERY',' '.join(run.call_args.args[0]));self.assertIn('PRIVATE-QUERY',run.call_args.kwargs['input']);self.assertEqual(result['native']['status'],'unavailable');self.assertEqual(result['scope'],['public','personal'])
 def test_project_scope_is_explicit(self):
  with patch('host.subprocess.run',return_value=subprocess.CompletedProcess([],0,'{"pins":[]}','')) as run:
   host.read_owner('pins',{});self.assertEqual(json.loads(run.call_args.kwargs['input']),{})
   host.read_owner('pins',{'project':'project-a'});self.assertEqual(json.loads(run.call_args.kwargs['input']),{'project':'project-a'})
   host.read_owner('pins',{'all_projects':True});self.assertEqual(json.loads(run.call_args.kwargs['input']),{'all_projects':True})
 def test_non_json_failure_retains_read_envelope(self):
  with patch('host.subprocess.run',return_value=subprocess.CompletedProcess([],2,'','Unavailable estate')):
   result=host.read_owner('status',{})
   self.assertTrue(result['read_only']);self.assertEqual(result['scope'],['public','personal']);self.assertEqual(result['native']['status'],'unavailable');self.assertEqual(result['native']['diagnostic'],'Unavailable estate')
if __name__=='__main__':unittest.main()
