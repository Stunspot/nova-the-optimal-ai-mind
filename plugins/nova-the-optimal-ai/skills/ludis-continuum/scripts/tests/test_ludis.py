from __future__ import annotations
import json,subprocess,sys,tempfile,unittest,zipfile
from pathlib import Path
SKILL=Path(__file__).resolve().parents[2];SCRIPTS=SKILL/"scripts";sys.path.insert(0,str(SCRIPTS))
from ledgerlib import load,validate
class Tests(unittest.TestCase):
 def setUp(self):self.template=SKILL/"assets/campaign.template/campaign-ledger.json";self.example=SKILL/"examples/first-value/campaign/campaign-ledger.json"
 def test_json(self):
  for p in SKILL.rglob("*.json"):
   with self.subTest(p=p):json.loads(p.read_text(encoding="utf-8"))
 def test_template(self):self.assertEqual(validate(load(self.template)),[])
 def test_example(self):self.assertEqual(validate(load(self.example)),[])
 def test_dispute_preserved(self):self.assertEqual(sum(o["status"]=="disputed" for o in load(self.example)["objects"]),2)
 def test_rule_unresolved(self):self.assertEqual(next(o for o in load(self.example)["objects"] if o["id"]=="rule-forced-move")["authority"],"unverified")
 def test_duplicate(self):
  d=load(self.template);base={"id":"x","kind":"npc","status":"proposed","visibility":"gm_only","authority":"model_proposal","provenance":[],"confidence":"low","tenure":"session"};d["objects"]=[base,dict(base)];self.assertTrue(any("duplicate" in e for e in validate(d)))
 def test_broken_link(self):
  d=load(self.template);d["objects"]=[{"id":"x","kind":"npc","status":"proposed","visibility":"gm_only","authority":"model_proposal","provenance":[],"confidence":"low","tenure":"session","links":["nope"]}];self.assertTrue(any("broken" in e for e in validate(d)))
 def test_spoiler_link(self):
  d=load(self.template);base={"kind":"lore","status":"proposed","authority":"model_proposal","provenance":[],"confidence":"low","tenure":"session"};d["objects"]=[dict(base,id="s",visibility="gm_only"),dict(base,id="p",visibility="player_safe",links=["s"])];self.assertTrue(any("spoiler" in e for e in validate(d)))
 def test_active_requires_gm(self):
  d=load(self.template);d["objects"]=[{"id":"x","kind":"npc","status":"active_canon","visibility":"gm_only","authority":"model_proposal","provenance":[],"confidence":"low","tenure":"campaign"}];self.assertTrue(any("gm_approved" in e for e in validate(d)))
 def test_collision(self):
  d=load(self.template);d["sessions"]=[{"id":"a","scheduled_for":"x"},{"id":"b","scheduled_for":"x"}];self.assertTrue(any("collision" in e for e in validate(d)))
 def test_export_safe(self):
  with tempfile.TemporaryDirectory() as t:
   out=Path(t)/"out.json";r=subprocess.run([sys.executable,"-B",str(SCRIPTS/"export_player_safe.py"),str(self.example),str(out)],capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stdout);x=json.loads(out.read_text());self.assertTrue(all(o["visibility"]=="player_safe" for o in x["objects"]));self.assertFalse(any(o["id"].startswith("lore-") for o in x["objects"]))
 def test_promote_requires_gm(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/"l.json";p.write_bytes(self.example.read_bytes());r=subprocess.run([sys.executable,"-B",str(SCRIPTS/"promote_object.py"),str(p),"handout-bell"],capture_output=True,text=True);self.assertNotEqual(r.returncode,0)
 def test_seed_reproducible(self):
  table=SKILL/"examples/first-value/campaign/rumors.json";cmd=[sys.executable,"-B",str(SCRIPTS/"roll_table.py"),str(table),"--seed","bell","--count","3"];self.assertEqual(subprocess.run(cmd,capture_output=True,text=True).stdout,subprocess.run(cmd,capture_output=True,text=True).stdout)
 def test_init_refuses_nonempty(self):
  with tempfile.TemporaryDirectory() as t:
   d=Path(t)/"x";d.mkdir();(d/"keep").write_text("x");r=subprocess.run([sys.executable,"-B",str(SCRIPTS/"init_campaign.py"),str(d)],capture_output=True,text=True);self.assertNotEqual(r.returncode,0)
 def test_eval_count(self):self.assertEqual((SKILL/"evals/core-cases.yaml").read_text().count("  - {id:"),12)
if __name__=="__main__":unittest.main()
