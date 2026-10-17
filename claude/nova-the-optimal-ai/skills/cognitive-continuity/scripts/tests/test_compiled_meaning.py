from __future__ import annotations
import json
from scripts.tests.test_continuity_v2 import WorkspaceCase, STORE, compiler, runtime, rewrite_active_member

class MeaningPreservationTests(WorkspaceCase):
    def test_selected_source_neighborhood_survives_recent_window_and_keeps_time(self):
        source=self.episode("The dry-run restriction applies to production only.",key="important")
        record=self.cli(STORE,"record",self.root,"--kind","decision","--content","Production changes require a dry run; local experiments remain allowed.",
            "--source-ids",source["episode_id"],"--authority","user-stunspot","--valid-from","2026-01-01T00:00:00Z",
            "--idempotency-key","decision","--expected-generation",self.generation)
        for i in range(3):
            self.episode("Unrelated recent observation "+str(i),key="noise-"+str(i))
        markdown, metadata=compiler.compile_packet(self.root,"production release",12000,"limited",1,[],[])
        self.assertIn("The dry-run restriction applies to production only.",markdown)
        self.assertIn("effective from: 2026-01-01T00:00:00Z",markdown)
        self.assertIn("recorded:",markdown)
        self.assertIn(source["episode_id"],metadata["supporting_episode_ids"])
        self.assertIn("Scope: agent=nova; project=project; user=user",markdown)
        self.assertNotIn("\\n",markdown)
    def test_eligible_conflict_exposes_its_meaning_without_becoming_current(self):
        source=self.episode("Two unresolved reports describe different next steps.",key="source")
        self.cli(STORE,"record",self.root,"--kind","decision","--content","Wait for the owner to resolve the delivery choice.",
            "--source-ids",source["episode_id"],"--authority","user-stunspot","--idempotency-key","state","--expected-generation",self.generation)
        rows=runtime.read_jsonl(self.root/"state"/"records.jsonl")
        current=rows[-1]
        dispute=json.loads(json.dumps(current))
        dispute.update(id="ST-dispute",status="conflicted",content="One source proposes delivery tomorrow.",conflicts_with=[current["id"]])
        current["conflicts_with"]=["ST-dispute"]
        rows.append(dispute)
        rewrite_active_member(self.root,"state.jsonl",rows)
        markdown, metadata=compiler.compile_packet(self.root,"delivery",12000,"limited",0,[],[])
        self.assertIn("One source proposes delivery tomorrow.",markdown)
        self.assertIn("Neither statement is selected as operative authority.",markdown)
        self.assertEqual(metadata["conflict_detail_ids"],["ST-dispute"])
        self.assertNotIn("ST-dispute",metadata["selected_ids"])
