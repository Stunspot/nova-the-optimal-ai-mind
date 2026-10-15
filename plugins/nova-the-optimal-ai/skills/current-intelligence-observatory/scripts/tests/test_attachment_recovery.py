"""Attachments must preserve original custody and honest tool state on failure."""
import json,unittest,sys,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from osint_bridge import attach
import test_osint_bridge as bridge_tests

class AttachmentRecovery(unittest.TestCase):
    setUp=bridge_tests.OsintBridgeTests.setUp
    def test_malformed_events_leave_no_partial_destination_then_retry(self):
        original=self.original.read_bytes();(self.run/'spiderfoot-events.json').write_text('{"not":"array"}')
        with self.assertRaises(ValueError):attach(self.home,self.original,self.run,self.output)
        self.assertFalse(self.output.exists());self.assertFalse(self.output.with_suffix('.captures').exists());self.assertEqual(original,self.original.read_bytes())
        (self.run/'spiderfoot-events.json').write_text(json.dumps(self.report));attach(self.home,self.original,self.run,self.output);self.assertTrue(self.output.exists())
    def test_legacy_receipt_is_explicitly_unverified(self):
        result=attach(self.home,self.original,self.run,self.output);self.assertFalse(result['receipt_inventory_verified']);self.assertIn('Legacy receipt',json.loads(self.output.read_text())['sources'][-1]['uncertainty'])
    def test_modern_changed_report_rejected(self):
        run=json.loads((self.run/'run.json').read_text());run.update(format='cd-osint-run/v1',artifacts={'spiderfoot-events.json':hashlib.sha256((self.run/'spiderfoot-events.json').read_bytes()).hexdigest()});(self.run/'run.json').write_text(json.dumps(run));(self.run/'spiderfoot-events.json').write_text('[]')
        with self.assertRaises(ValueError):attach(self.home,self.original,self.run,self.output)
        self.assertFalse(self.output.exists());self.assertFalse(self.output.with_suffix('.captures').exists())
    def test_modern_exact_receipt_accepted_without_truth_upgrade(self):
        run=json.loads((self.run/'run.json').read_text());run.update(format='cd-osint-run/v1',artifacts={'spiderfoot-events.json':hashlib.sha256((self.run/'spiderfoot-events.json').read_bytes()).hexdigest()});(self.run/'run.json').write_text(json.dumps(run));result=attach(self.home,self.original,self.run,self.output);self.assertTrue(result['receipt_inventory_verified']);self.assertEqual(0,result['entities_resolved'])
    def test_boolean_exit_and_invalid_clock_rejected(self):
        original=json.loads((self.run/'run.json').read_text())
        for field,value in [('exit_code',True),('completed_at','2026-10-05T23:00:00-00:00')]:
            run=dict(original);run[field]=value;(self.run/'run.json').write_text(json.dumps(run))
            with self.assertRaises(ValueError):attach(self.home,self.original,self.run,self.output)
            self.assertFalse(self.output.exists())
    def test_duplicate_raw_run_key_rejected(self):
        raw=(self.run/'run.json').read_text().replace('"exit_code":','"exit_code":7,"exit_code":');(self.run/'run.json').write_text(raw)
        with self.assertRaises(ValueError):attach(self.home,self.original,self.run,self.output)
        self.assertFalse(self.output.exists())
if __name__=='__main__':unittest.main()
