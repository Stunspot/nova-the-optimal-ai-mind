import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from test_validate_swarm_plan import MODULE, TEMPLATE_PATH


class ExecutionDecisionTests(unittest.TestCase):
    def setUp(self):
        self.p = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
        a=self.p["workers"][0]
        b=copy.deepcopy(a);b["id"]="worker-b"
        self.p["workers"]=[a,b];self.p["regime"]="assemble"

    def assertBad(self, text):
        errors=MODULE.validate(self.p)
        self.assertTrue(any(text in e for e in errors),errors)

    def assertGood(self):
        self.assertEqual([],MODULE.validate(self.p))

    def test_directory_ancestor_conflict_and_sibling_boundary(self):
        a,b=self.p["workers"]
        for x,y in [("src","src/a.py"),("SRC\\","src/a.py"),(".","lib/a"),("E:/work","e:\\work\\a.py")]:
            a["write_surfaces"]=[x];b["write_surfaces"]=[y]
            self.assertBad("share write surface")
        a["write_surfaces"]=["src/a"];b["write_surfaces"]=["src/ab"]
        self.assertGood()

    def test_planned_dependency_may_reserve_parent_and_child(self):
        a,b=self.p["workers"];self.p["regime"]="chain"
        a["write_surfaces"]=["src"];b["write_surfaces"]=["src/a.py"];b["depends_on"]=[a["id"]]
        self.assertGood()
        b["status"]="working"
        self.assertBad("share write surface")
        a["status"]="reconciled"
        self.assertGood()

    def test_budget_counts_running_workers_not_future_wave(self):
        a,b=self.p["workers"];self.p["budgets"]["concurrency_limit"]=1
        a["status"]="working";b["status"]="dispatched"
        self.assertBad("exceeds budgets")
        b["status"]="planned";self.assertGood()
        b["status"]="returned";self.assertGood()

    def test_reserved_permission_cannot_also_be_allowed(self):
        self.p["authority"]["reserved"]=["  "+self.p["authority"]["allowed"][0].upper()+"  "]
        self.assertBad("conflicts with authority.reserved")

    def test_cancelled_unstarted_dependency_and_unknown_interruption(self):
        a,b=self.p["workers"];self.p["regime"]="chain";b["depends_on"]=[a["id"]]
        for status in ["cancelled","interrupted"]:
            a["status"]=b["status"]=status
            a["started"]=b["started"]=False
            self.p["status"]="cancelled";self.p["next_move"]="Cancelled"
            self.assertGood()
        b["started"]=True
        self.assertBad("requires accepted dependency")

    def test_disposal_does_not_erase_explicit_accepted_output(self):
        a,b=self.p["workers"];self.p["regime"]="chain";b["depends_on"]=[a["id"]]
        a["status"]="closed";b["status"]="working"
        self.assertBad("requires accepted dependency")
        a["output"]={"state":"accepted","evidence":["root-review.txt"]}
        self.assertGood()
        a["output"]["state"]="rejected"
        self.assertBad("requires accepted dependency")

    def test_closed_writer_needs_readback_even_with_accepted_output(self):
        a,b=self.p["workers"];self.p["regime"]="chain";b["depends_on"]=[a["id"]]
        a["status"]="closed";b["status"]="working"
        a["write_surfaces"]=["src"];b["write_surfaces"]=["src/a"]
        a["output"]={"state":"accepted","evidence":["review.txt"]}
        self.assertBad("requires accepted dependency");self.assertBad("share write surface")
        a["write_readback"]={"state":"reconciled","evidence":["diff-and-check.txt"]}
        self.assertGood()

    def test_unknown_interrupted_writes_remain_reserved(self):
        a,b=self.p["workers"]
        a["status"]="interrupted";a["write_surfaces"]=["src"];b["write_surfaces"]=["src/a"]
        b["status"]="working";self.assertBad("share write surface")
        a["started"]=False;self.assertGood()
        a.pop("started");a["write_readback"]={"state":"reconciled","evidence":["actual-state.txt"]}
        self.assertGood()

    def test_contradictory_declared_worker_facts_reject(self):
        a=self.p["workers"][0]
        for status in ["dispatched","working","returned","reconciled"]:
            a["status"]=status;a["started"]=False
            self.assertBad("started contradicts")
        a["status"]="reconciled";a["started"]=True;a["output"]={"state":"rejected","evidence":["bad.txt"]}
        self.assertBad("output contradicts")

    def close(self):
        for w in self.p["workers"]:w["status"]="failed"
        self.p["status"]="closed";self.p["next_move"]="None"
        return self.p["outcome"]

    def test_closed_legacy_is_unverified_not_rejected_or_accepted(self):
        self.close();self.p.pop("outcome")
        self.assertGood();self.assertEqual("unverified",MODULE.declared_outcome(self.p))

    def test_explicit_partial_failure_is_valid(self):
        outcome=self.close();outcome.update(state="partial",unresolved=["Criterion still fails."])
        outcome["checks"]=[{"criterion":self.p["acceptance"][0],"result":"failed","evidence":["failure.txt"]}]
        self.assertGood()

    def accepted(self):
        outcome=self.close();outcome["state"]="accepted"
        outcome["checks"]=[{"criterion":c,"result":"passed","evidence":["root-result.txt"]} for c in self.p["acceptance"]]
        return outcome

    def test_accepted_requires_exact_pass_coverage_and_no_unresolved(self):
        out=self.accepted();self.assertGood()
        pristine=copy.deepcopy(out)
        for mutate,needle in [
            (lambda o:o["checks"].pop(),"every acceptance"),
            (lambda o:o["checks"][0].update(result="failed"),"every acceptance"),
            (lambda o:o["checks"][0].update(result="not-run"),"every acceptance"),
            (lambda o:o["checks"][0].update(criterion="Other task"),"match a plan"),
            (lambda o:o["checks"].append(copy.deepcopy(o["checks"][0])),"duplicates"),
            (lambda o:o["checks"][0].update(evidence=["none"]),"concrete evidence"),
            (lambda o:o["unresolved"].append("blocker"),"unresolved issues")]:
            self.p["outcome"]=copy.deepcopy(pristine);mutate(self.p["outcome"]);self.assertBad(needle)

    def test_accepted_cannot_hide_unknown_interrupted_write(self):
        self.accepted()
        w=self.p["workers"][0];w["status"]="interrupted";w["write_surfaces"]=["src"]
        self.assertBad("unknown or unresolved writes")
        w["write_readback"]={"state":"reconciled","evidence":["readback.txt"]}
        self.assertGood()

    def test_malformed_extensions_fail_without_traceback(self):
        a=self.p["workers"][0]
        for field in ["output","write_readback"]:
            for value in [7,[],{"state":[],"evidence":[3]},{"state":"accepted","evidence":[]},{"state":"accepted","evidence":["N/A"]}]:
                a[field]=value
                self.assertTrue(MODULE.validate(self.p),(field,value))
            a.pop(field)
        for value in [[],3,{"state":[],"checks":[{}],"unresolved":[]}]:
            self.p["outcome"]=value
            self.assertTrue(MODULE.validate(self.p))

    def test_help_and_invalid_utf8_are_controlled(self):
        cmd=[sys.executable,"-B","-X","utf8",str(MODULE.__file__)]
        help_result=subprocess.run(cmd+["--help"],capture_output=True,text=True,encoding="utf-8")
        self.assertEqual(0,help_result.returncode);self.assertIn("usage:",help_result.stdout)
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"bad.json";path.write_bytes(b"\xff")
            result=subprocess.run(cmd+[str(path)],capture_output=True,text=True,encoding="utf-8")
            self.assertEqual(1,result.returncode);self.assertNotIn("Traceback",result.stdout+result.stderr)


if __name__=="__main__":unittest.main()
