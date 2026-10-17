"""Synthetic declared-record controls, not real device or model trials."""
import copy
import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from validate_case_file import validate_data, consistency_issues, load_json
ROOT = Path(__file__).resolve().parents[2]
SAMPLE = json.loads((ROOT / "assets/it-case.template.json").read_text())

def draft():
    data = copy.deepcopy(SAMPLE)
    data["next_move"]["action"] = "Ask which application is affected"
    return data

def resolved():
    data = draft()
    data["status"] = "verification-passed"
    data["verification"] = {"original_envelope_retested": True,
        "results": [{"outcome": "passed", "observation": "Three sleep/wake cycles retained dock Ethernet", "source": "Synthetic technician observation", "conditions": "Same dock, cable and 20-minute sleep as reported"}],
        "adjacent_checks": [{"outcome": "passed", "observation": "Dock keyboard and Wi-Fi still work", "source": "Synthetic technician observation", "conditions": "After the same wake cycles"}],
        "disposition": "verified-resolved", "reopen_condition": "Reopen if Ethernet is lost at the original sleep/wake trigger"}
    return data

class EvidenceTests(unittest.TestCase):
    def test_incomplete_draft_and_unknown_extension_remain_usable(self):
        data=draft();data['owner_extension']={'keep':[False,0,'café']};before=copy.deepcopy(data)
        validate_data(data);self.assertEqual(consistency_issues(data),[]);self.assertEqual(data,before)
    def test_exact_recorded_resolution_is_consistent_not_physical_proof(self):
        data=resolved();validate_data(data);self.assertEqual(consistency_issues(data),[])
    def test_resolution_requires_original_envelope_and_results(self):
        for field,value in [('original_envelope_retested',False),('results',[])]:
            data=resolved();data['verification'][field]=value
            self.assertTrue(consistency_issues(data))
    def test_failed_unknown_or_narrative_checks_do_not_prove_pass(self):
        for result in [{'outcome':'failed'}, {'outcome':'unknown'}, 'looks fine']:
            data=resolved();data['verification']['results']=[result];self.assertTrue(consistency_issues(data))
    def test_adjacent_not_applicable_requires_specific_reason(self):
        data=resolved();data['verification']['adjacent_checks']=[];self.assertTrue(consistency_issues(data))
        data['verification']['adjacent_not_applicable']='The observed display preference changed no device, network or account subsystem.'
        self.assertEqual(consistency_issues(data),[])
    def test_stale_resolution_and_conflicting_status_are_reported(self):
        data=resolved();data['verification']['stale']=True;self.assertTrue(consistency_issues(data))
        data=resolved();data['status']='verification-failed';self.assertTrue(consistency_issues(data))
    def test_actions_and_reference_shapes_are_not_fluent_objects(self):
        for bad in [' ',{},[],True]:
            data=draft();data['next_move']['action']=bad
            with self.assertRaises(ValueError):validate_data(data)
        data=draft();data['tests']=[{'id':'T1','hypothesis_ids':[{}]}]
        with self.assertRaises(ValueError):validate_data(data)
    def test_duplicate_ids_rejected_without_choosing_one(self):
        data=draft();data['hypotheses']=[{'id':'H1'},{'id':'H1'}]
        with self.assertRaisesRegex(ValueError,'duplicates'):validate_data(data)
    def test_dangling_reference_visible_without_invention(self):
        data=draft();data['tests']=[{'id':'T1','hypothesis_ids':['missing'],'performed':False}]
        validate_data(data);self.assertIn('missing hypotheses ID missing',' '.join(consistency_issues(data)))
    def test_performed_requires_provenance_but_legacy_is_preserved(self):
        data=draft();data['tests']=[{'id':'T1','state':'test-run','test':'Check the dock','result':'Link returns'}]
        before=copy.deepcopy(data);validate_data(data);self.assertTrue(consistency_issues(data));self.assertEqual(data,before)
        data['tests'][0].update(performed=True,result_source='Synthetic observer',result_basis='reported')
        self.assertEqual(consistency_issues(data),[])
    def test_string_performed_rejected(self):
        data=draft();data['tests']=[{'id':'T1','performed':'false'}]
        with self.assertRaises(ValueError):validate_data(data)
    def test_conflicting_aliases_are_not_silently_resolved(self):
        data=draft();data['evidence']=[{'id':'E1','kind':'measured','state':'assumed','claim':'A','value':'B'}]
        validate_data(data);self.assertEqual(len(consistency_issues(data)),2)
    def test_nonfinite_and_duplicate_json_rejected(self):
        for raw in ['{"a":1,"a":2}','{"a":NaN}','{"a":Infinity}','{"a":[1e400]}','{"a":-1e400}']:
            with self.assertRaises(ValueError):load_json(raw)

    def test_nonfinite_in_memory_extension_rejected_without_mutation(self):
        data=draft();data['extension']={'observations':[float('inf')]}
        with self.assertRaisesRegex(ValueError,'Non-finite'):validate_data(data)
        self.assertEqual(data['extension']['observations'],[float('inf')])
    def test_finite_extension_numbers_are_retained(self):
        data=draft();data['extension']={'observations':[0,1.25,-2,1e-40]}
        self.assertEqual(validate_data(load_json(json.dumps(data))),data)

if __name__ == '__main__':unittest.main()
