from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import adapters  # noqa: E402
from adapters import (  # noqa: E402
    AdapterError,
    FOUNDRY_IMPORTER_TEMPLATE,
    render_alchemy_character_json,
    render_foundry_v14_bundle,
    validate_alchemy_character_files,
    validate_foundry_v14_bundle,
)


def load_json(files, path):
    return json.loads(files[path].decode("utf-8"))


class AlchemyAdapterTests(unittest.TestCase):
    def projection(self):
        return {
            "campaign": {"id": "campaign-lantern", "title": "Lantern Wake", "system": "Some Rules"},
            "objects": [
                {
                    "id": "mara",
                    "kind": "npc",
                    "title": "Mara Venn",
                    "content": "A sharp-eyed courier who owes the duke nothing.",
                    "asset_ids": ["mara-token"],
                    "data": {
                        "systemKey": "5e",
                        "ability_scores": {"str": 10, "dex": 14, "con": 12, "int": 11, "wis": 13, "cha": 9},
                        "hp": {"current": 12, "max": 12},
                        "armor_class": 13,
                        "movement_modes": [{"mode": "Walking", "distance": 30}],
                        "traits": [{"name": "Quick Hands", "description": "Can palm a key unnoticed."}],
                    },
                }
            ],
            "assets": [{"id": "mara-token", "path": "media/mara.webp"}],
        }

    def test_renders_individual_and_exact_bulk_file(self):
        files = render_alchemy_character_json(self.projection(), {"mara-token": b"ignored"})
        self.assertEqual(validate_alchemy_character_files(files), [])
        self.assertIn("mara-venn.json", files)
        character = load_json(files, "mara-venn.json")
        bulk = load_json(files, "_all.json")
        self.assertEqual(bulk, {"characters": [character]})
        self.assertEqual(character["systemKey"], "5e")
        self.assertTrue(character["isNPC"])
        self.assertEqual(character["abilityScores"][1], {"name": "dex", "value": 14})
        self.assertEqual(character["textBlocks"][0]["textBlocks"][0]["title"], "Quick Hands")
        self.assertFalse(any(path.startswith("assets/") for path in files))
        report = load_json(files, "reports/loss-report.json")
        self.assertFalse(report["compatibility"]["live_import_verified"])
        self.assertIn("local_assets_not_embedded", {item["code"] for item in report["items"]})

    def test_missing_explicit_system_key_blocks_without_inference(self):
        projection = self.projection()
        projection["objects"][0]["data"].pop("systemKey")
        files = render_alchemy_character_json(projection)
        self.assertEqual(set(files), {"reports/loss-report.json"})
        report = load_json(files, "reports/loss-report.json")
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["summary"]["blocked"], 1)
        self.assertIn("missing_system_key", {item["code"] for item in report["items"]})
        self.assertEqual(validate_alchemy_character_files(files), [])

    def test_name_and_system_key_are_not_enough_to_invent_mechanics(self):
        projection = {
            "campaign": {"systemKey": "5e"},
            "objects": [{"id": "empty", "kind": "npc", "title": "Empty Coat", "data": {}}],
            "assets": [],
        }
        files = render_alchemy_character_json(projection)
        self.assertNotIn("_all.json", files)
        report = load_json(files, "reports/loss-report.json")
        self.assertIn("insufficient_character_data", {item["code"] for item in report["items"]})

    def test_renderer_is_deterministic_and_does_not_mutate_projection(self):
        projection = self.projection()
        before = copy.deepcopy(projection)
        first = render_alchemy_character_json(projection)
        second = render_alchemy_character_json(projection)
        self.assertEqual(first, second)
        self.assertEqual(projection, before)

    def test_invalid_bulk_mismatch_is_detected(self):
        files = render_alchemy_character_json(self.projection())
        damaged = dict(files)
        bulk = load_json(files, "_all.json")
        bulk["characters"][0]["name"] = "Someone Else"
        damaged["_all.json"] = (json.dumps(bulk) + "\n").encode("utf-8")
        self.assertIn("_all.json characters do not exactly match", " ".join(validate_alchemy_character_files(damaged)))

    def test_malformed_nested_native_fields_cannot_be_statically_ready(self):
        files = render_alchemy_character_json(self.projection())
        damaged = dict(files)
        character_path = "mara-venn.json"
        character = load_json(files, character_path)
        character["textBlocks"] = [42]
        character["actions"] = [{"name": "Broken", "steps": [42]}]
        character["spells"] = [42]
        damaged[character_path] = (json.dumps(character) + "\n").encode("utf-8")
        damaged["_all.json"] = (json.dumps({"characters": [character]}) + "\n").encode("utf-8")
        errors = " ".join(validate_alchemy_character_files(damaged))
        self.assertIn("textBlocks[0] must be an object", errors)
        self.assertIn("actions[0].steps[0] must be an object", errors)
        self.assertIn("spells[0] must be an object", errors)

    def test_renderer_blocks_malformed_native_text_blocks(self):
        projection = self.projection()
        projection["objects"][0]["data"]["alchemy"] = {"textBlocks": [42]}
        with self.assertRaisesRegex(AdapterError, "textBlocks\\[0\\] must be an object"):
            render_alchemy_character_json(projection)


    def test_exact_allowlist_rejects_code_binary_unlisted_json_and_alias_paths(self):
        files = render_alchemy_character_json(self.projection())
        variants = {
            "module code": ("scripts/evil.mjs", b"export default true;\n"),
            "binary": ("payload.bin", b"opaque"),
            "unlisted json": ("other.json", b"{}\n"),
            "path alias": ("./mara-venn.json", files["mara-venn.json"]),
        }
        for label, (path, payload) in variants.items():
            with self.subTest(label=label):
                damaged = dict(files)
                damaged[path] = payload
                errors = " ".join(validate_alchemy_character_files(damaged))
                self.assertIn("exact allowlist", errors)

    def test_loss_report_binds_exact_deterministic_character_paths_and_counts(self):
        projection = self.projection()
        second = copy.deepcopy(projection["objects"][0])
        second["id"] = "mara-two"
        projection["objects"].append(second)
        files = render_alchemy_character_json(projection)
        report = load_json(files, "reports/loss-report.json")
        self.assertEqual(
            report["summary"]["emitted"],
            {"characters": 2, "character_files": ["mara-venn.json", "mara-venn-2.json"]},
        )
        self.assertEqual(
            set(files),
            {"reports/loss-report.json", "_all.json", "mara-venn.json", "mara-venn-2.json"},
        )

        damaged = dict(files)
        altered_report = copy.deepcopy(report)
        altered_report["summary"]["emitted"] = {"characters": 99, "character_files": ["alias.json"]}
        damaged["reports/loss-report.json"] = (json.dumps(altered_report) + "\n").encode("utf-8")
        errors = " ".join(validate_alchemy_character_files(damaged))
        self.assertIn("does not match exact character count", errors)
        self.assertIn("does not match deterministic paths", errors)

    def test_loss_status_and_compatibility_state_are_exactly_consistent(self):
        with_losses = render_alchemy_character_json(self.projection())
        with_losses_report = load_json(with_losses, "reports/loss-report.json")
        self.assertEqual(with_losses_report["status"], "statically_ready_with_losses")
        self.assertEqual(with_losses_report["compatibility"]["state"], with_losses_report["status"])

        ready_projection = self.projection()
        ready_projection["objects"][0]["asset_ids"] = []
        ready_projection["assets"] = []
        ready = render_alchemy_character_json(ready_projection)
        ready_report = load_json(ready, "reports/loss-report.json")
        self.assertEqual(ready_report["status"], "statically_ready")
        self.assertEqual(ready_report["compatibility"]["state"], ready_report["status"])

        blocked_projection = self.projection()
        blocked_projection["objects"][0]["data"].pop("systemKey")
        blocked = render_alchemy_character_json(blocked_projection)
        blocked_report = load_json(blocked, "reports/loss-report.json")
        self.assertEqual(blocked_report["status"], "blocked")
        self.assertEqual(blocked_report["compatibility"]["state"], blocked_report["status"])

        damaged = dict(ready)
        ready_report["compatibility"]["state"] = "blocked"
        damaged["reports/loss-report.json"] = (json.dumps(ready_report) + "\n").encode("utf-8")
        self.assertIn(
            "compatibility.state must exactly match status",
            " ".join(validate_alchemy_character_files(damaged)),
        )

class FoundryAdapterTests(unittest.TestCase):
    def projection(self):
        return {
            "campaign": {"id": "campaign-lantern", "title": "Lantern Wake"},
            "objects": [
                {
                    "id": "mara",
                    "kind": "npc",
                    "title": "Mara Venn",
                    "content": "A sharp-eyed courier.",
                    "asset_ids": [],
                    "data": {"systemKey": "5e", "armorClass": 13},
                },
                {
                    "id": "rumors",
                    "kind": "rumor_table",
                    "title": "Market Rumors",
                    "content": "Things overheard before dawn.",
                    "asset_ids": [],
                    "data": {
                        "entries": [
                            {"text": "The duke vanished.", "weight": 2},
                            {"text": "A comet burns green.", "weight": 1},
                        ]
                    },
                },
                {
                    "id": "old-mill",
                    "kind": "scene",
                    "title": "Old Mill",
                    "content": "A flooded mill under green moonlight.",
                    "asset_ids": ["mill-map"],
                    "data": {
                        "width": 2400,
                        "height": 1800,
                        "padding": 0,
                        "grid": {"type": "square", "size": 100, "distance": 5, "units": "ft"},
                        "levels": [
                            {
                                "id": "old-mill-ground",
                                "name": "Ground",
                                "background_asset_id": "mill-map",
                                "elevation": {"bottom": 0, "top": 10},
                            }
                        ],
                    },
                },
            ],
            "assets": [{"id": "mill-map", "path": "media/old-mill.webp", "kind": "map", "alt_text": "Map of a flooded old mill beneath green moonlight."}],
        }

    def test_renders_core_documents_v14_levels_and_module_assets(self):
        files = render_foundry_v14_bundle(
            self.projection(),
            {"mill-map": b"generated map bytes"},
            module_id="ludis-lantern",
        )
        self.assertEqual(validate_foundry_v14_bundle(files), [])
        manifest = load_json(files, "module.json")
        payload = load_json(files, "data/ludis-foundry-v14.json")
        self.assertEqual(manifest["compatibility"], {"minimum": "14", "maximum": "14"})
        self.assertNotIn("verified", manifest["compatibility"])
        self.assertEqual(set(payload["documents"]), {"JournalEntry", "RollTable", "Scene"})
        self.assertNotIn("Actor", payload["documents"])
        self.assertNotIn("Item", payload["documents"])
        self.assertEqual(payload["target"], {"generation": 14, "build": 365})
        self.assertEqual(payload["audience"], "gm")
        self.assertEqual(payload["assets"][0]["altText"], "Map of a flooded old mill beneath green moonlight.")
        self.assertTrue(all(document["ownership"]["default"] == 0 for document in payload["documents"]["JournalEntry"] + payload["documents"]["RollTable"]))
        self.assertTrue(all(record["scene"]["ownership"]["default"] == 0 for record in payload["documents"]["Scene"]))
        self.assertFalse(payload["compatibility"]["liveImportVerified"])
        table = payload["documents"]["RollTable"][0]
        self.assertEqual(table["formula"], "1d3")
        self.assertEqual([result["range"] for result in table["results"]], [[1, 2], [3, 3]])
        scene_import = payload["documents"]["Scene"][0]
        self.assertNotIn("background", scene_import["scene"])
        background = scene_import["levels"][0]["background"]["src"]
        self.assertTrue(background.startswith("modules/ludis-lantern/assets/"))
        self.assertIn(background.removeprefix("modules/ludis-lantern/"), files)
        importer = files["scripts/importer.mjs"].decode("utf-8")
        self.assertIn('createEmbeddedDocuments("Level"', importer)
        self.assertIn("report.skipped", importer)
        self.assertIn("getFlag?.(FLAG_SCOPE, FLAG_KEY)", importer)
        self.assertIn("classifyLudisImport(found?.metadata, incoming", importer)
        self.assertIn("const existing = indexWorld(report)", importer)
        self.assertIn('if (disposition === "conflict")', importer)
        self.assertIn("Conflicts were left unchanged", importer)
        self.assertIn("scene.initialLevel?.id !== initialLevel.id", importer)

    def test_player_projection_emits_observer_visible_core_documents(self):
        projection = self.projection()
        projection["audience"] = "player"
        files = render_foundry_v14_bundle(projection, {"mill-map": b"map"})
        self.assertEqual(validate_foundry_v14_bundle(files), [])
        payload = load_json(files, "data/ludis-foundry-v14.json")
        self.assertEqual(payload["audience"], "player")
        self.assertTrue(all(document["ownership"]["default"] == 2 for document in payload["documents"]["JournalEntry"] + payload["documents"]["RollTable"]))
        self.assertTrue(all(record["scene"]["ownership"]["default"] == 2 for record in payload["documents"]["Scene"]))

    def test_exact_example_map_alt_text_reaches_foundry_payload(self):
        projection = self.projection()
        example_alt = "Top-down map of a roofless stone-and-timber tollhouse beside a river, with a muddy fenced yard and broken cart."
        projection["assets"][0]["alt_text"] = example_alt
        payload = load_json(
            render_foundry_v14_bundle(projection, {"mill-map": b"map"}),
            "data/ludis-foundry-v14.json",
        )
        self.assertEqual(payload["assets"][0]["altText"], example_alt)
    def test_asset_alt_text_is_required_and_player_images_require_authored_text(self):
        files = render_foundry_v14_bundle(self.projection(), {"mill-map": b"map"})
        damaged = dict(files)
        payload = load_json(files, "data/ludis-foundry-v14.json")
        payload["assets"][0]["altText"] = ""
        damaged["data/ludis-foundry-v14.json"] = (json.dumps(payload) + "\n").encode("utf-8")
        self.assertIn("altText must be a non-empty canonical string", " ".join(validate_foundry_v14_bundle(damaged)))

        projection = self.projection()
        projection["audience"] = "player"
        projection["assets"][0].pop("alt_text")
        with self.assertRaisesRegex(AdapterError, "requires authored alt_text"):
            render_foundry_v14_bundle(projection, {"mill-map": b"map"})

    def test_foundry_loss_status_matches_report_and_payload_compatibility(self):
        ready = render_foundry_v14_bundle(self.projection(), {"mill-map": b"map"})
        ready_report = load_json(ready, "reports/loss-report.json")
        ready_payload = load_json(ready, "data/ludis-foundry-v14.json")
        self.assertEqual(ready_report["compatibility"]["state"], ready_report["status"])
        self.assertEqual(ready_payload["compatibility"]["state"], ready_report["status"])

        lossy_projection = {
            "campaign": {"id": "campaign-lossy", "title": "Lossy"},
            "objects": [{"id": "bad-scene", "kind": "scene", "title": "Fog", "data": {"width": 1200}}],
            "assets": [],
        }
        lossy = render_foundry_v14_bundle(lossy_projection)
        lossy_report = load_json(lossy, "reports/loss-report.json")
        lossy_payload = load_json(lossy, "data/ludis-foundry-v14.json")
        self.assertEqual(lossy_report["status"], "statically_ready_with_losses")
        self.assertEqual(lossy_report["compatibility"]["state"], lossy_report["status"])
        self.assertEqual(lossy_payload["compatibility"]["state"], lossy_report["status"])

        blocked_projection = {
            "campaign": {"id": "campaign-empty", "title": "Empty"},
            "objects": [],
            "assets": [],
        }
        blocked = render_foundry_v14_bundle(blocked_projection)
        blocked_report = load_json(blocked, "reports/loss-report.json")
        blocked_payload = load_json(blocked, "data/ludis-foundry-v14.json")
        self.assertEqual(blocked_report["status"], "blocked")
        self.assertEqual(blocked_report["compatibility"]["state"], blocked_report["status"])
        self.assertEqual(blocked_payload["compatibility"]["state"], blocked_report["status"])

        damaged = dict(ready)
        ready_report["compatibility"]["state"] = "blocked"
        damaged["reports/loss-report.json"] = (json.dumps(ready_report) + "\n").encode("utf-8")
        self.assertIn(
            "compatibility.state must exactly match status",
            " ".join(validate_foundry_v14_bundle(damaged)),
        )
    def test_validator_rejects_ownership_that_does_not_match_audience(self):
        projection = self.projection()
        projection["audience"] = "player"
        files = render_foundry_v14_bundle(projection, {"mill-map": b"map"})
        damaged = dict(files)
        payload = load_json(files, "data/ludis-foundry-v14.json")
        payload["documents"]["JournalEntry"][0]["ownership"]["default"] = 0
        damaged["data/ludis-foundry-v14.json"] = (json.dumps(payload) + "\n").encode("utf-8")
        self.assertIn("ownership must contain only the audience-matching default", " ".join(validate_foundry_v14_bundle(damaged)))
    def test_validator_rejects_explicit_user_ownership_overrides_after_revision_restamp(self):
        files = render_foundry_v14_bundle(self.projection(), {"mill-map": b"map"})
        for label in ("JournalEntry", "Scene"):
            with self.subTest(label=label):
                damaged = dict(files)
                payload = load_json(files, "data/ludis-foundry-v14.json")
                if label == "JournalEntry":
                    document = payload["documents"]["JournalEntry"][0]
                    document["ownership"]["player-user-id"] = 3
                    adapters._stamp_foundry_revision(document)
                else:
                    record = payload["documents"]["Scene"][0]
                    scene = record["scene"]
                    scene["ownership"]["player-user-id"] = 3
                    adapters._stamp_foundry_revision(record, scene)
                damaged["data/ludis-foundry-v14.json"] = (json.dumps(payload) + "\n").encode("utf-8")
                self.assertIn(
                    "ownership must contain only the audience-matching default",
                    " ".join(validate_foundry_v14_bundle(damaged)),
                )

    def test_campaign_scoped_identity_preserves_source_id_and_changes_exact_revision(self):
        first_projection = self.projection()
        first_files = render_foundry_v14_bundle(first_projection, {"mill-map": b"map"})
        first_payload = load_json(first_files, "data/ludis-foundry-v14.json")
        first_record = first_payload["documents"]["JournalEntry"][0]
        first_flags = first_record["flags"]["ludis"]

        repeated_payload = load_json(
            render_foundry_v14_bundle(copy.deepcopy(first_projection), {"mill-map": b"map"}),
            "data/ludis-foundry-v14.json",
        )
        repeated_flags = repeated_payload["documents"]["JournalEntry"][0]["flags"]["ludis"]
        self.assertEqual(first_flags, repeated_flags)
        self.assertEqual(first_flags["campaignId"], "campaign-lantern")
        self.assertEqual(first_flags["audience"], "gm")
        self.assertRegex(first_flags["importRevisionSha256"], r"^[0-9a-f]{64}$")

        second_projection = copy.deepcopy(first_projection)
        second_projection["campaign"]["id"] = "campaign-other"
        second_payload = load_json(
            render_foundry_v14_bundle(second_projection, {"mill-map": b"map"}),
            "data/ludis-foundry-v14.json",
        )
        second_flags = second_payload["documents"]["JournalEntry"][0]["flags"]["ludis"]
        self.assertEqual(second_flags["sourceId"], first_flags["sourceId"])
        self.assertNotEqual(second_flags["campaignId"], first_flags["campaignId"])
        self.assertNotEqual(second_flags["importRevisionSha256"], first_flags["importRevisionSha256"])

        player_projection = copy.deepcopy(first_projection)
        player_projection["audience"] = "player"
        player_payload = load_json(
            render_foundry_v14_bundle(player_projection, {"mill-map": b"map"}),
            "data/ludis-foundry-v14.json",
        )
        player_flags = player_payload["documents"]["JournalEntry"][0]["flags"]["ludis"]
        self.assertEqual(player_flags["campaignId"], first_flags["campaignId"])
        self.assertEqual(player_flags["sourceId"], first_flags["sourceId"])
        self.assertEqual(player_flags["audience"], "player")
        self.assertNotEqual(player_flags["importRevisionSha256"], first_flags["importRevisionSha256"])

        changed_projection = copy.deepcopy(first_projection)
        changed_projection["objects"][0]["title"] = "Changed exact import content"
        changed_payload = load_json(
            render_foundry_v14_bundle(changed_projection, {"mill-map": b"map"}),
            "data/ludis-foundry-v14.json",
        )
        changed_flags = changed_payload["documents"]["JournalEntry"][0]["flags"]["ludis"]
        self.assertNotEqual(changed_flags["importRevisionSha256"], first_flags["importRevisionSha256"])

    def test_js_identity_helper_skips_exact_reruns_and_conflicts_on_changed_import(self):
        node = shutil.which("node")
        if node is None:
            self.skipTest("Node.js is unavailable")
        digest_a = "a" * 64
        digest_b = "b" * 64
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            importer_path = root / "importer.mjs"
            importer_path.write_text(
                FOUNDRY_IMPORTER_TEMPLATE.replace("__LUDIS_MODULE_ID__", "ludis-helper-test"),
                encoding="utf-8",
            )
            runner_path = root / "runner.mjs"
            runner_path.write_text(
                """
globalThis.Hooks = {once() {}};
const imported = await import(process.argv[2]);
const base = {campaignId: "campaign-a", sourceId: "same-id", audience: "gm", importRevisionSha256: "DIGEST_A"};
const exact = {...base};
const otherCampaign = {...base, campaignId: "campaign-b"};
const changedAudience = {...base, audience: "player"};
const changedDigest = {...base, importRevisionSha256: "DIGEST_B"};
console.log(JSON.stringify({
  first: imported.classifyLudisImport(null, base),
  exact: imported.classifyLudisImport(base, exact),
  otherCampaign: imported.classifyLudisImport(base, otherCampaign),
  changedAudience: imported.classifyLudisImport(base, changedAudience),
  changedDigest: imported.classifyLudisImport(base, changedDigest),
  changedType: imported.classifyLudisImport(base, exact, "JournalEntry", "RollTable"),
  identityA: imported.ludisIdentity(base),
  identityB: imported.ludisIdentity(otherCampaign)
}));
""".replace("DIGEST_A", digest_a).replace("DIGEST_B", digest_b),
                encoding="utf-8",
            )
            result = subprocess.run(
                [node, str(runner_path), importer_path.as_uri()],
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        dispositions = json.loads(result.stdout)
        self.assertEqual(dispositions["first"], "create")
        self.assertEqual(dispositions["exact"], "skip")
        self.assertEqual(dispositions["otherCampaign"], "create")
        self.assertEqual(dispositions["changedAudience"], "conflict")
        self.assertEqual(dispositions["changedDigest"], "conflict")
        self.assertEqual(dispositions["changedType"], "conflict")
        self.assertNotEqual(dispositions["identityA"], dispositions["identityB"])

    def test_importer_blocks_exact_level_under_foreign_scene_before_creation(self):
        node = shutil.which("node")
        if node is None:
            self.skipTest("Node.js is unavailable")
        payload = load_json(
            render_foundry_v14_bundle(self.projection(), {"mill-map": b"map"}),
            "data/ludis-foundry-v14.json",
        )
        payload["documents"]["JournalEntry"] = []
        payload["documents"]["RollTable"] = []
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            importer_path = root / "importer.mjs"
            importer_path.write_text(
                FOUNDRY_IMPORTER_TEMPLATE.replace("__LUDIS_MODULE_ID__", "ludis-parent-test"),
                encoding="utf-8",
            )
            runner_path = root / "runner.mjs"
            runner = r'''
globalThis.Hooks = {once() {}};
const payload = __PAYLOAD__;
const incomingScene = payload.documents.Scene[0];
const incomingSceneMetadata = incomingScene.scene.flags.ludis;
const incomingLevelMetadata = incomingScene.levels[0].flags.ludis;
function makeDocument(metadata, additions = {}) {
  return {
    ...additions,
    getFlag(scope, key) {
      if (scope !== "ludis") return null;
      return metadata[key] ?? null;
    }
  };
}
let createdScenes = 0;
let foreignSceneUpdates = 0;
const existingLevel = makeDocument(incomingLevelMetadata, {id: "foreign-level-id"});
const foreignSceneMetadata = {
  ...incomingSceneMetadata,
  sourceId: "foreign-parent-scene",
  importRevisionSha256: "f".repeat(64)
};
const foreignScene = makeDocument(foreignSceneMetadata, {
  id: "foreign-scene-id",
  levels: [existingLevel],
  initialLevel: null,
  async update() { foreignSceneUpdates += 1; }
});
globalThis.game = {
  user: {isGM: true},
  release: {generation: 14},
  journal: [],
  tables: [],
  scenes: [foreignScene]
};
globalThis.CONFIG = {
  Scene: {documentClass: {async createDocuments() { createdScenes += 1; return []; }}}
};
globalThis.fetch = async () => ({ok: true, async json() { return payload; }});
globalThis.ui = {notifications: {error() {}, info() {}}};
const imported = await import(process.argv[2]);
const report = await imported.importBundle();
console.log(JSON.stringify({report, createdScenes, foreignSceneUpdates}));
'''.replace("__PAYLOAD__", json.dumps(payload, separators=(",", ":")))
            runner_path.write_text(runner, encoding="utf-8")
            result = subprocess.run(
                [node, str(runner_path), importer_path.as_uri()],
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        observed = json.loads(result.stdout)
        self.assertEqual(observed["createdScenes"], 0)
        self.assertEqual(observed["foreignSceneUpdates"], 0)
        self.assertEqual(observed["report"]["created"]["Scene"], 0)
        self.assertEqual(observed["report"]["errors"], [])
        self.assertEqual(len(observed["report"]["conflicts"]), 1)
        self.assertEqual(observed["report"]["conflicts"][0]["reason"], "parent_scene_mismatch")

    def test_importer_blocks_exact_page_under_foreign_journal_before_creation(self):
        node = shutil.which("node")
        if node is None:
            self.skipTest("Node.js is unavailable")
        payload = load_json(
            render_foundry_v14_bundle(self.projection(), {"mill-map": b"map"}),
            "data/ludis-foundry-v14.json",
        )
        payload["documents"]["JournalEntry"] = payload["documents"]["JournalEntry"][:1]
        payload["documents"]["RollTable"] = []
        payload["documents"]["Scene"] = []
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            importer_path = root / "importer.mjs"
            importer_path.write_text(
                FOUNDRY_IMPORTER_TEMPLATE.replace("__LUDIS_MODULE_ID__", "ludis-page-parent-test"),
                encoding="utf-8",
            )
            runner_path = root / "runner.mjs"
            runner = r'''
globalThis.Hooks = {once() {}};
const payload = __PAYLOAD__;
const incomingJournal = payload.documents.JournalEntry[0];
const incomingJournalMetadata = incomingJournal.flags.ludis;
const incomingPageMetadata = incomingJournal.pages[0].flags.ludis;
function makeDocument(metadata, additions = {}) {
  return {
    ...additions,
    getFlag(scope, key) {
      if (scope !== "ludis") return null;
      return metadata[key] ?? null;
    }
  };
}
let createdJournals = 0;
const existingPage = makeDocument(incomingPageMetadata, {id: "foreign-page-id"});
const foreignJournalMetadata = {
  ...incomingJournalMetadata,
  sourceId: "foreign-parent-journal",
  importRevisionSha256: "f".repeat(64)
};
const foreignJournal = makeDocument(foreignJournalMetadata, {
  id: "foreign-journal-id",
  pages: [existingPage]
});
globalThis.game = {
  user: {isGM: true},
  release: {generation: 14},
  journal: [foreignJournal],
  tables: [],
  scenes: []
};
globalThis.CONFIG = {
  JournalEntry: {documentClass: {async createDocuments() { createdJournals += 1; return []; }}}
};
globalThis.fetch = async () => ({ok: true, async json() { return payload; }});
globalThis.ui = {notifications: {error() {}, info() {}}};
const imported = await import(process.argv[2]);
const report = await imported.importBundle();
console.log(JSON.stringify({report, createdJournals}));
'''.replace("__PAYLOAD__", json.dumps(payload, separators=(",", ":")))
            runner_path.write_text(runner, encoding="utf-8")
            result = subprocess.run(
                [node, str(runner_path), importer_path.as_uri()],
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        observed = json.loads(result.stdout)
        self.assertEqual(observed["createdJournals"], 0)
        self.assertEqual(observed["report"]["created"]["JournalEntry"], 0)
        self.assertEqual(observed["report"]["errors"], [])
        self.assertEqual(len(observed["report"]["conflicts"]), 1)
        self.assertEqual(observed["report"]["conflicts"][0]["type"], "JournalEntryPage")
        self.assertEqual(observed["report"]["conflicts"][0]["reason"], "parent_document_mismatch")

    def test_validator_rejects_stale_revision_after_content_tampering(self):
        files = render_foundry_v14_bundle(self.projection(), {"mill-map": b"map"})
        damaged = dict(files)
        payload = load_json(files, "data/ludis-foundry-v14.json")
        payload["documents"]["JournalEntry"][0]["name"] = "Silently stale"
        damaged["data/ludis-foundry-v14.json"] = (json.dumps(payload) + "\n").encode("utf-8")
        self.assertIn(
            "does not match exact import record",
            " ".join(validate_foundry_v14_bundle(damaged)),
        )

    def test_validator_rejects_importer_manifest_and_member_injection(self):
        files = render_foundry_v14_bundle(self.projection(), {"mill-map": b"map"})

        appended = dict(files)
        appended["scripts/importer.mjs"] += b"\nconsole.log('appended');\n"
        self.assertIn(
            "does not exactly match the trusted generated importer",
            " ".join(validate_foundry_v14_bundle(appended)),
        )

        scripted_manifest = dict(files)
        manifest = load_json(files, "module.json")
        manifest["scripts"] = ["scripts/evil.js"]
        scripted_manifest["module.json"] = (json.dumps(manifest) + "\n").encode("utf-8")
        self.assertIn("strict allowlist", " ".join(validate_foundry_v14_bundle(scripted_manifest)))

        altered_esmodules = dict(files)
        manifest = load_json(files, "module.json")
        manifest["esmodules"] = ["scripts/importer.mjs", "scripts/evil.mjs"]
        altered_esmodules["module.json"] = (json.dumps(manifest) + "\n").encode("utf-8")
        self.assertIn(
            "esmodules must contain only scripts/importer.mjs",
            " ".join(validate_foundry_v14_bundle(altered_esmodules)),
        )

        extra_code = dict(files)
        extra_code["scripts/evil.mjs"] = b"export default true;\n"
        code_errors = " ".join(validate_foundry_v14_bundle(extra_code))
        self.assertIn("unexpected executable Foundry bundle member", code_errors)
        self.assertIn("unlisted members", code_errors)

        extra_document = dict(files)
        extra_document["README.txt"] = b"not declared"
        self.assertIn("unlisted members", " ".join(validate_foundry_v14_bundle(extra_document)))

    def test_manifest_template_matches_emitted_manifest_exactly(self):
        files = render_foundry_v14_bundle(
            self.projection(),
            {"mill-map": b"map"},
            module_id="ludis-lantern",
        )
        template = (ROOT / "assets" / "foundry-v14-module" / "module.template.json").read_text(encoding="utf-8")
        expected = json.loads(
            template.replace("__LUDIS_MODULE_ID__", "ludis-lantern").replace(
                "__LUDIS_MODULE_TITLE__",
                "Ludis: Lantern Wake",
            )
        )
        self.assertEqual(load_json(files, "module.json"), expected)
    def test_renderer_is_deterministic_pure_and_accepts_asset_paths(self):
        projection = self.projection()
        before = copy.deepcopy(projection)
        with tempfile.TemporaryDirectory() as temporary:
            map_path = Path(temporary) / "mill.webp"
            map_path.write_bytes(b"path-backed map")
            first = render_foundry_v14_bundle(projection, {"mill-map": map_path})
            second = render_foundry_v14_bundle(projection, {"mill-map": map_path})
        self.assertEqual(first, second)
        self.assertEqual(projection, before)
        payload = load_json(first, "data/ludis-foundry-v14.json")
        output_path = payload["assets"][0]["path"]
        self.assertEqual(first[output_path], b"path-backed map")

    def test_unresolved_scene_and_table_are_demoted_to_journals_with_losses(self):
        projection = {
            "campaign": {"id": "campaign-loss"},
            "objects": [
                {"id": "bad-scene", "kind": "scene", "title": "Fog", "data": {"width": 1200}},
                {"id": "bad-table", "kind": "table", "title": "Blank", "data": {"entries": []}},
            ],
            "assets": [],
        }
        files = render_foundry_v14_bundle(projection)
        payload = load_json(files, "data/ludis-foundry-v14.json")
        self.assertEqual(len(payload["documents"]["JournalEntry"]), 2)
        self.assertEqual(payload["documents"]["RollTable"], [])
        self.assertEqual(payload["documents"]["Scene"], [])
        codes = {item["code"] for item in load_json(files, "reports/loss-report.json")["items"]}
        self.assertIn("scene_demoted", codes)
        self.assertIn("roll_table_demoted", codes)

    def test_validator_rejects_obsolete_scene_background(self):
        files = render_foundry_v14_bundle(self.projection(), {"mill-map": b"map"})
        damaged = dict(files)
        payload = load_json(files, "data/ludis-foundry-v14.json")
        payload["documents"]["Scene"][0]["scene"]["background"] = {"src": "wrong.webp"}
        damaged["data/ludis-foundry-v14.json"] = (json.dumps(payload) + "\n").encode("utf-8")
        self.assertIn("obsolete top-level background", " ".join(validate_foundry_v14_bundle(damaged)))

    def test_validator_rejects_missing_asset_bytes_and_bad_digest(self):
        files = render_foundry_v14_bundle(self.projection(), {"mill-map": b"map"})
        damaged = dict(files)
        payload = load_json(files, "data/ludis-foundry-v14.json")
        asset_path = payload["assets"][0]["path"]
        damaged[asset_path] = b"changed"
        errors = " ".join(validate_foundry_v14_bundle(damaged))
        self.assertIn("size or digest", errors)

    def test_duplicate_source_ids_are_blocked(self):
        projection = self.projection()
        projection["objects"].append(copy.deepcopy(projection["objects"][0]))
        with self.assertRaisesRegex(AdapterError, "duplicate object source id"):
            render_foundry_v14_bundle(projection, {"mill-map": b"map"})

    def test_static_importer_template_matches_emitted_logic(self):
        template = (ROOT / "assets" / "foundry-v14-module" / "scripts" / "importer.mjs").read_text(encoding="utf-8")
        self.assertEqual(template.rstrip(), FOUNDRY_IMPORTER_TEMPLATE.rstrip())

    def test_importer_has_valid_javascript_syntax_when_node_is_available(self):
        node = shutil.which("node")
        if node is None:
            self.skipTest("Node.js is unavailable")
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "importer.mjs"
            path.write_text(FOUNDRY_IMPORTER_TEMPLATE, encoding="utf-8")
            result = subprocess.run([node, "--check", str(path)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class SchemaTests(unittest.TestCase):
    def test_schemas_are_valid_json_and_record_static_evidence_boundary(self):
        alchemy = json.loads((ROOT / "schemas" / "alchemy-character.schema.json").read_text(encoding="utf-8"))
        foundry = json.loads((ROOT / "schemas" / "foundry-v14-bundle.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(alchemy["required"], ["name", "systemKey"])
        self.assertIn("does not prove live import compatibility", alchemy["description"])
        self.assertEqual(foundry["properties"]["target"]["properties"]["build"]["const"], 365)
        self.assertEqual(foundry["properties"]["compatibility"]["properties"]["liveImportVerified"]["const"], False)
        self.assertEqual(set(foundry["properties"]["documents"]["properties"]), {"JournalEntry", "RollTable", "Scene"})
        self.assertFalse(foundry["$defs"]["ownership"]["additionalProperties"])
        ludis_flags = foundry["$defs"]["flags"]["properties"]["ludis"]
        self.assertEqual(
            set(ludis_flags["required"]),
            {"sourceId", "campaignId", "audience", "importRevisionSha256"},
        )
        self.assertFalse(ludis_flags["additionalProperties"])


if __name__ == "__main__":
    unittest.main()