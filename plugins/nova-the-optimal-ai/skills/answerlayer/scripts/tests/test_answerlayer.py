from __future__ import annotations
import json,subprocess,sys,tempfile,unittest,zipfile
from datetime import date
from pathlib import Path
HERE=Path(__file__).resolve();ROOT=HERE.parents[2];SCRIPTS=ROOT/"scripts";sys.path.insert(0,str(SCRIPTS))
from ledgerlib import load,next_recheck,qualify,validate

class AnswerLayerTests(unittest.TestCase):
 def setUp(self):self.example=ROOT/"examples/first-value/reality-ledger.json"
 def run_script(self,name,*args):return subprocess.run([sys.executable,str(SCRIPTS/name),*map(str,args)],capture_output=True,text=True)
 def test_example_validates(self):self.assertEqual(validate(load(self.example)),[])
 def test_duplicate_id_rejected(self):
  d=load(self.example);d["probes"].append(dict(d["probes"][0]));self.assertTrue(any("duplicate id" in x for x in validate(d)))
 def test_unknown_source_rejected(self):
  d=load(self.example);d["patches"][0]["source_ids"]=["NOPE"];self.assertTrue(any("unknown source_id" in x for x in validate(d)))
 def test_patched_baseline_requires_human_approval(self):
  d=load(self.example);d["baseline"]["status"]="patched";self.assertTrue(any("human_approved" in x for x in validate(d)))
 def test_candidate_qualification_fails_without_answer_change(self):
  c=load(self.example)["candidates"][1];self.assertTrue(any("answer_change" in x for x in qualify(c)))
 def test_recheck(self):self.assertEqual(next_recheck(date(2026,7,20),30).isoformat(),"2026-08-19")
 def test_init_refuses_overwrite(self):
  with tempfile.TemporaryDirectory() as t:
   first=self.run_script("init_reality_ledger.py",t);second=self.run_script("init_reality_ledger.py",t);self.assertEqual(first.returncode,0);self.assertEqual(second.returncode,2)
 def test_export_refuses_unapproved(self):
  with tempfile.TemporaryDirectory() as t:
   r=self.run_script("export_approved_brief.py",self.example,Path(t)/"brief.md");self.assertEqual(r.returncode,2);self.assertIn("REFUSED",r.stdout)
 def test_watch_threshold(self):
  r=self.run_script("evaluate_watch_threshold.py","11","gte","10");self.assertEqual(r.returncode,0);self.assertIn("TRIGGERED",r.stdout)
 def test_conflict_detector_surfaces_fuzz(self):
  r=self.run_script("detect_conflicts.py",self.example);self.assertEqual(r.returncode,0);self.assertIn("FUZZ_UNRESOLVED: CAN-005",r.stdout)
 def test_snapshot_excludes_nested_snapshots(self):
  with tempfile.TemporaryDirectory() as t:
   src=Path(t)/"workspace";src.mkdir();(src/"x.txt").write_text("x");(src/"snapshots").mkdir();(src/"snapshots/old.zip").write_text("old");out=Path(t)/"snapshot.zip";r=self.run_script("snapshot_ledger.py",src,out);self.assertEqual(r.returncode,0)
   with zipfile.ZipFile(out) as z:self.assertEqual(z.namelist(),["x.txt"])
if __name__=="__main__":unittest.main()
