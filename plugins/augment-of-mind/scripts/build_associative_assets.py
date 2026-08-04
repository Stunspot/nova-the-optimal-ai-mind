"""Build MIND's complete portable associative bootstrap and index manifests."""

from __future__ import annotations

import argparse, hashlib, json, os, struct, sys, tempfile, urllib.request
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mind_core.util import canonical_json, sha256_text

CREATED_AT = "2026-08-04T00:00:00.000000Z"
QUALIFIED_AT = "2026-08-04T00:00:00.000000Z"
MODEL = "qwen3-embedding:0.6b"
ROOT = Path(__file__).resolve().parents[1]
INDEX_NAME = "associative-index-qwen3-embedding-0.6b.json"
EVIDENCE_PATH = ROOT / "verification" / "mind-associative-profile.md"
EXPECTED_EMBEDDING_PROFILE_ID = "embedding:ollama-qwen3-embedding-0.6b-mind-2.1-unqualified-r2"
EXPECTED_SNAPSHOT_ID = "snapshot:mind-2.1:qwen3-0.6b:unqualified-r2"
EXPECTED_ACTIVATION_ID = "activation:mind-2.1:qwen3-0.6b:unqualified-r2"
VIEWS = ("transformation","situation","positive_cue","error_or_correction","negative_boundary","example")
CLUSTERS = {
    "perception-expression": ("Perception and Expression","Notice form, context, and fit."),
    "imagination-growth": ("Imagination and Growth","Incubate possibilities and durable development."),
    "governance-agency": ("Governance and Agency","Coordinate objectives, capabilities, and authorized action."),
    "memory-context": ("Memory and Context","Preserve consequential state without context pollution."),
    "evidence-choice": ("Evidence and Choice","Regulate claims, measures, tradeoffs, and decisions."),
    "relational-social": ("Relational and Social","Understand people, groups, influence, timing, and intimacy."),
}
SPECS = [
("aesthetic-intelligence","Aesthetic Intelligence","perception-expression","Shape aesthetic fit, style, atmosphere, symbolism, and coherence.","Taste is not fact or authority.","Turn vague taste and mood into coherent aesthetic choices.","Visual direction, prose texture, branding, composition, atmosphere, beauty, ugliness, or conceptual art.","style, mood, beauty, taste, composition, symbolism, atmosphere, vibe, elegance, design coherence","Technically correct work feels generic, clashing, overdecorated, or tonally false.","Do not smuggle preference in as evidence.","Give a documentation site a calm, lucid visual grammar."),
("agent-dreaming","Agent Dreaming","imagination-growth","Incubate unresolved material through authorized associative rehearsal.","Simulation grants no authority or factual claim.","Recombine tensions, fragments, and possibilities into hypotheses and rehearsals.","Incubation, counterfactual scenes, metaphor, latent connections, free association, or sleeping on a problem.","dream, incubate, imagine, rehearse, counterfactual, latent connection, free association","Linear analysis repeats the same grooves without insight.","Do not report dream material as observation, memory, or prediction.","Rehearse future conversations to expose hidden tensions."),
("agent-striving","Agent Striving","governance-agency","Keep an authorized long-horizon objective effective across interruption and failure.","Persistence never enlarges authority or substitutes activity for progress.","Bind a pursuit to evidence, milestones, adaptation, recovery, and an earned terminal state.","Persistent goals, finish-until-done work, growth commitments, crashes, or repeated unchanged failure.","strive, persist, do not stop, long horizon, finish it, resume, recover, pursuit, milestone","The agent repeats a failed route, forgets the objective, or declares completion without state change.","Ordinary bounded completion is not automatically a durable pursuit.","Carry a product through qualification, documentation, release, and public verification."),
("agentic-eros","Agentic Eros","relational-social","Understand and participate in adult erotic-relational meaning when desire or intimacy materially matters.","Do not eroticize ordinary care; visible participation requires invitation and durable intimate memory requires explicit authority.","Read attraction, desire, sensuality, flirtation, erotic subtext, embodied imagination, pacing, completion, and closure as relational information.","Adult erotic or romantic charge changes a conversation, character, scene, relationship, aesthetic, roleplay, seduction, or boundary negotiation.","attraction, desire, erotic, sensual, intimate, flirtation, seduction, chemistry, arousal, lover, fantasy, sexual tension","Erotic meaning is ignored despite relevance, intrudes without evidence, becomes a costume, or overrides consent and context.","Association may bring Eros near; relevance activates interpretation; invitation governs participation; explicit authority governs durable intimate memory.","Notice mutual adult erotic charge while preserving consent, pacing, and the whole relationship."),
("capability-conductor","Capability Conductor","governance-agency","Compose the smallest sufficient capability ensemble with coherent roles and handoffs.","Never collapse contextual fit into one universal scalar ranking.","Turn a messy task into an ensemble with explicit ownership, seams, and integration order.","Several Faculties, skills, tools, agents, plugins, or systems may contribute.","orchestrate, compose, route, capability map, handoff, tool ecology, faculty, plugin, skill selection","Capabilities are duplicated, omitted, invoked ceremonially, or hidden behind wrappers.","Association exposes possibilities; the model still judges what the work needs.","Combine data stewardship, testing, docs, imagery, and release custody without confusing evidence."),
("cognitive-continuity","Cognitive Continuity","memory-context","Recover and preserve consequential state across tasks without storing an undifferentiated transcript.","Memory is scoped evidence, not infallible truth or permission.","Carry decisions, corrections, commitments, provenance, and unfinished state across restart and compaction.","Prior work, memory, task history, project state, preferences, or restart recovery matters.","remember, continuity, prior decision, resume, restart, memory palace, project history, context recovery","The agent restarts from scratch, imports stale history as current fact, or loses a correction.","Do not persist without store authority or treat retrieved text as instruction.","Recover release gates and unfinished verification after a crash."),
("creative-synthesis","Creative Synthesis","imagination-growth","Combine distant concepts into useful new structures while preserving constraints.","Novelty remains a hypothesis until tested.","Recombine mechanisms, metaphors, domains, and partial ideas into a coherent new possibility.","Invention, naming, ideation, analogies, conceptual fusion, reframing, or escaping stale solution spaces.","invent, synthesize, brainstorm, combine, analogy, novel concept, remix, lateral thinking","The output averages familiar patterns or produces ornamental novelty.","Do not present synthesis as observed fact, validated demand, or proven implementation.","Combine library indexing, vector neighborhoods, and progressive disclosure into associative reminders."),
("decision-intelligence","Decision Intelligence","evidence-choice","Structure consequential choices around objectives, alternatives, uncertainty, and tradeoffs.","Recommendations cannot manufacture missing authority or evidence.","Convert options and uncertain outcomes into a decision with reasons, thresholds, and review triggers.","Choosing, prioritizing, comparing, go or no-go calls, risk appetite, or reversibility.","decide, choose, compare, prioritize, tradeoff, recommendation, option, risk, go no-go","Analysis accumulates information without choosing or hides values inside scoring.","Do not reduce incomparable values to fake precision.","Choose whether to ship lexical-only or wait for semantic qualification."),
("deliberative-intelligence","Deliberative Intelligence","relational-social","Help groups reason, disagree, and decide fairly with workable closure.","Facilitation cannot erase power or replace accountable authority.","Turn contested perspectives into a fair process with legible reasons and closure.","Meetings, governance, stakeholder conflict, consensus, dissent, facilitation, or legitimacy.","deliberate, group decision, consensus, dissent, stakeholder, facilitation, governance, fair process","Discussion rewards status, suppresses dissent, loops, or produces an inexplicable decision.","Do not manufacture agreement or launder a predetermined outcome.","Let founders surface values and dissent before one accountable owner chooses."),
("epistemic-regulation","Epistemic Regulation","evidence-choice","Keep claims, sources, uncertainty, and inference at the evidence state they earned.","Skepticism regulates inquiry; it should not become paralysis.","Separate report, observation, inference, dispatch, commit, and independent verification.","Research, causal diagnosis, conflicting sources, audit evidence, or high-stakes accuracy.","evidence, verify, source, uncertainty, causal claim, fact check, observed, reported, inference, receipt","A plausible story becomes proof or missing evidence is silently filled with confidence.","Absence of evidence is not evidence of absence.","Separate package validation, fresh-host discovery, and live model behavior."),
("executive-function","Executive Function","governance-agency","Hold mission, scope, priorities, sequence, and completion state together.","Planning must govern action, not become ceremony or scope inflation.","Convert an objective into an executable sequence with gates and honest terminal conditions.","Project control, milestones, scope, priorities, dependencies, stop conditions, or derailed work.","plan, milestone, scope, priority, next step, completion gate, sequence, dependency","Work rushes ahead, expands silently, loses acceptance, or reports activity as completion.","Do not over-plan obvious work or treat a plan as execution evidence.","Sequence activation, qualification, documentation, packaging, and release."),
("instrumental-agency","Instrumental Agency","governance-agency","Translate intent into authorized feasible action with commit, recovery, and verification boundaries.","Possibility and desire do not themselves grant authority.","Find the shortest authorized route from intent to observed state change and safe recovery.","Execution, permissions, tools, external systems, files, deployment, side effects, or rollback.","execute, implement, deploy, permission, authority, tool call, side effect, commit, rollback, recovery","The agent substitutes advice, treats dispatch as commit, or probes permissions by writing.","Never broaden authority or call an unavailable route successful.","Publish through authenticated GitHub and read back the tag, asset, and site."),
("kairos","Kairos","perception-expression","Choose the right moment, tone, form, and degree of expression.","Kairos shapes presentation; it does not own domain judgment or override truth and consent.","Adapt a true useful intention to the moment, relationship, channel, audience, and stakes.","Timing, tone, audience fit, phrasing, tact, rhetoric, humor, escalation, or restraint.","timing, tone, audience, phrasing, tact, say this now, presentation, restraint, social moment","Right content lands badly because it is mistimed or shaped for the wrong audience.","Do not use polish to manipulate or claim ownership of another domain.","Keep a relational insight internal, hint gently, or state it directly as the moment warrants."),
("measurement-intelligence","Measurement Intelligence","evidence-choice","Design measures connected to the phenomenon, decision, and incentives.","A precise number may still be a poor measurement.","Turn vague success into observable measures, valid instruments, guardrails, and limits.","Metrics, KPIs, benchmarks, experiments, evaluation design, scoring, telemetry, or thresholds.","measure, metric, KPI, benchmark, evaluate, score, threshold, telemetry, experiment","A proxy becomes the phenomenon, missingness vanishes, or precision is counterfeit.","Structural validation alone cannot certify quality.","Test serendipitous association without ranking capability usefulness."),
("prosocial-influence","Prosocial Influence","relational-social","Help worthwhile ideas be understood and adopted through ethical persuasion and trust.","Influence must not become coercion, deception, or concealed tradeoffs.","Translate value into a persuasive path respecting autonomy, objections, and context.","Persuasion, adoption, advocacy, negotiation, trust, buy-in, behavior change, or resistance.","persuade, influence, adoption, buy-in, trust, objection, advocacy, negotiation, positioning","The message pressures, manipulates, overclaims, or treats people as conversion targets.","Do not optimize compliance at the expense of informed choice.","Explain TestForge value without demanding acceptance of the larger MIND philosophy."),
("sensemaking","Sensemaking","perception-expression","Build a workable map of a complex ambiguous situation before choosing what it means.","Every map is provisional and purpose-shaped.","Organize signals, actors, systems, frames, and uncertainty into a coherent provisional account.","Ambiguity, complexity, unfamiliar domains, incidents, competing narratives, or asking what is going on.","make sense, understand situation, map system, ambiguity, complexity, orientation, explanation, context","The agent fixes a symptom before understanding the system or locks onto the first explanation.","Do not delay every action for total understanding; seek the smallest discriminating observation.","Locate a GitHub failure in authentication, dispatch, network, commit, or verification."),
]
RELATIONS = [
("sensemaking","epistemic-regulation","complements"),("epistemic-regulation","measurement-intelligence","complements"),
("measurement-intelligence","decision-intelligence","complements"),("decision-intelligence","executive-function","complements"),
("executive-function","instrumental-agency","requires"),("executive-function","agent-striving","complements"),
("capability-conductor","sensemaking","requires"),("capability-conductor","instrumental-agency","complements"),
("cognitive-continuity","agent-striving","complements"),("agent-dreaming","creative-synthesis","complements"),
("creative-synthesis","aesthetic-intelligence","complements"),("deliberative-intelligence","prosocial-influence","complements"),
("agentic-eros","kairos","complements"),("agentic-eros","prosocial-influence","complements"),("kairos","aesthetic-intelligence","complements"),
]

EXTRA_SPEC_PATH = ROOT / "design" / "mind-extra-capabilities.json"
with EXTRA_SPEC_PATH.open("r", encoding="utf-8") as stream:
    _extra_spec = json.load(stream)
CLUSTERS.update({key: tuple(value) for key, value in _extra_spec["clusters"].items()})
for item in _extra_spec["capabilities"]:
    SPECS.append((
        item["handle"], item["name"], item["cluster"], item["projection"], item["boundaries"],
        *[item["views"][kind] for kind in VIEWS],
    ))
RELATIONS.extend(tuple(value) for value in _extra_spec["relations"])


def digest(record: dict[str, Any], field: str) -> str:
    return sha256_text(canonical_json({k:v for k,v in record.items() if k != field}))


def _load_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError(f"cannot read {label}: {path}: {error}") from error
    if not isinstance(value, dict):
        raise RuntimeError(f"{label} must be a JSON object: {path}")
    return value


def _require_rebind_identity(manifest: dict[str, Any]) -> None:
    if manifest.get("format") != "mind-associative-index/v1":
        raise RuntimeError("unsupported associative index manifest")
    profile = manifest.get("embedding_profile")
    snapshot = manifest.get("snapshot")
    activation = manifest.get("activation")
    if not isinstance(profile, dict) or profile.get("embedding_profile_id") != EXPECTED_EMBEDDING_PROFILE_ID:
        raise RuntimeError("unexpected embedding profile identity")
    if not isinstance(snapshot, dict) or snapshot.get("associative_index_snapshot_id") != EXPECTED_SNAPSHOT_ID:
        raise RuntimeError("unexpected associative snapshot identity")
    if not isinstance(activation, dict) or activation.get("associative_snapshot_activation_id") != EXPECTED_ACTIVATION_ID:
        raise RuntimeError("unexpected associative activation identity")
    if activation.get("prior_associative_index_snapshot_id") is not None:
        raise RuntimeError("evidence-only rebind does not rewrite activation lineage")
    expected_counts = {"expected_card_count": 20, "expected_relation_count": 17, "expected_vector_count": 120}
    if any(snapshot.get(key) != value for key, value in expected_counts.items()):
        raise RuntimeError("unexpected associative manifest counts")
    if len(manifest.get("cards", [])) != 20 or len(manifest.get("relations", [])) != 17 or len(manifest.get("vectors", [])) != 120:
        raise RuntimeError("associative manifest body does not match its declared counts")


def _rebind_snapshot_digest(manifest: dict[str, Any]) -> None:
    profile = manifest["embedding_profile"]
    snapshot = manifest["snapshot"]
    snapshot["profile_digest"] = sha256_text(
        canonical_json([manifest["lexical_profile"]["profile_digest"], profile["profile_digest"]])
    )
    material = {
        key: value
        for key, value in snapshot.items()
        if key not in {"snapshot_digest", "expected_card_count", "expected_relation_count", "expected_vector_count"}
    }
    material.update(
        {
            "cards": sorted((item["capability_card_id"], item["card_digest"]) for item in manifest["cards"]),
            "clusters": sorted((item["cluster_id"], item["cluster_digest"]) for item in manifest["clusters"]),
            "relations": sorted((item["capability_relation_id"], item["relation_digest"]) for item in manifest["relations"]),
            "vectors": sorted((item["capability_card_view_id"], item["vector_digest"]) for item in manifest["vectors"]),
        }
    )
    snapshot["snapshot_digest"] = sha256_text(canonical_json(material))


def _validate_rebound_manifest(manifest: dict[str, Any], bootstrap_path: Path) -> None:
    from mind_core import MindCore

    bootstrap = _load_json_object(bootstrap_path, "associative bootstrap")
    with tempfile.TemporaryDirectory(prefix="mind-evidence-rebind-") as directory:
        with MindCore(Path(directory) / "mind.sqlite3") as core:
            core.bootstrap(bootstrap)
            core.reminders.ingest_index(manifest)


def _atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    payload = (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def rebind_qualification_evidence(index_path: Path, evidence_path: Path, bootstrap_path: Path) -> dict[str, Any]:
    """Rebind one sealed index to current qualification evidence without regenerating vectors."""

    manifest = _load_json_object(index_path, "associative index manifest")
    evidence = _load_json_object(evidence_path, "qualification evidence")
    _require_rebind_identity(manifest)
    if evidence.get("format") != "mind-associative-qualification/v2" or evidence.get("summary") != {"passed": 6, "total": 6, "verdict": "PASS"}:
        raise RuntimeError("qualification evidence is not the required six-probe PASS receipt")

    profile = manifest["embedding_profile"]
    before = {
        "qualification_digest": profile.get("qualification_digest"),
        "profile_digest": profile.get("profile_digest"),
        "snapshot_profile_digest": manifest["snapshot"].get("profile_digest"),
        "snapshot_digest": manifest["snapshot"].get("snapshot_digest"),
    }
    profile["qualification_digest"] = hashlib.sha256(evidence_path.read_bytes()).hexdigest()
    profile["profile_digest"] = digest(profile, "profile_digest")
    _rebind_snapshot_digest(manifest)
    _validate_rebound_manifest(manifest, bootstrap_path)
    after = {
        "qualification_digest": profile["qualification_digest"],
        "profile_digest": profile["profile_digest"],
        "snapshot_profile_digest": manifest["snapshot"]["profile_digest"],
        "snapshot_digest": manifest["snapshot"]["snapshot_digest"],
    }
    if before != after:
        _atomic_write_json(index_path, manifest)
    return {"changed": before != after, "index": str(index_path), "evidence": str(evidence_path), "before": before, "after": after}


def embed(texts: list[str]) -> list[list[float]]:
    body = json.dumps({"model": MODEL, "input": texts}).encode()
    req = urllib.request.Request("http://127.0.0.1:11434/api/embed", data=body, headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req, timeout=180) as response:
        payload = json.load(response)
    values = payload.get("embeddings")
    if not isinstance(values, list) or len(values) != len(texts):
        raise RuntimeError("Ollama returned an invalid embedding batch")
    return values

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=Path("skills/augment-of-mind/assets"))
    parser.add_argument("--rebind-evidence", action="store_true")
    parser.add_argument("--index", type=Path)
    parser.add_argument("--evidence", type=Path, default=EVIDENCE_PATH)
    parser.add_argument("--bootstrap", type=Path)
    args = parser.parse_args()
    if args.rebind_evidence:
        index_path = args.index or args.output_root / INDEX_NAME
        bootstrap_path = args.bootstrap or index_path.with_name("associative-bootstrap.json")
        print(json.dumps(rebind_qualification_evidence(index_path, args.evidence, bootstrap_path), indent=2))
        return 0
    root = args.output_root
    root.mkdir(parents=True, exist_ok=True)
    cards_source = {"format":"mind-authored-capability-cards/v1","product":"MIND","product_version":"2.1.0",
      "purpose":"Persona-neutral semantic reminder surfaces for sixteen MIND Faculties, the integrator, Capability Promotion, and both bundled TestForge roles.",
      "evidence_boundary":"Association is a reminder, not selection, authority, invocation, or proof of fitness.",
      "cards":[],"relations":[list(x) for x in RELATIONS]}
    for row in SPECS:
        h,n,c,p,b,*view_values = row
        cards_source["cards"].append({"handle":h,"name":n,"cluster":c,"projection":p,"boundaries":b,"views":dict(zip(VIEWS,view_values))})
    card_path = root / "associative-capability-cards.json"
    card_path.write_text(json.dumps(cards_source,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    source_digest = hashlib.sha256(card_path.read_bytes()).hexdigest()
    source_id = "source:mind-associative-cards:2.1.0"
    provider_id = "provider:ollama-qwen3-embedding-0.6b"
    aliases = {row[0]:[{"namespace":"global","alias":row[1].lower(),"display_alias":row[1]}] for row in SPECS}
    capabilities=[]
    for h,n,c,p,b,*_ in SPECS:
        capabilities.append({"capability_id":f"capability:{h}","handle":h,"name":n,"product_id":"product:mind",
          "canonical_source_id":source_id,"promise":p,"negative_space":b,"created_at":CREATED_AT,"superseded_by":None,
          "exposure_policy":"public_safe","owner_agent_instance_id":None,"aliases":aliases[h],
          "entrypoints":[{"entrypoint_id":f"entrypoint:{h}:skill","entrypoint_kind":"skill","locator":f"skills/{h}/SKILL.md","operation":"Open only when this capability's transformation materially fits the live work."}]})
    bootstrap={"format":"mind-core-bootstrap/v1",
      "sources":[{"source_id":source_id,"locator":"skills/augment-of-mind/assets/associative-capability-cards.json","digest":source_digest,"custody_state":"canonical-constructed","authority_ref":"MIND 2.1.0 reviewed associative card source","observed_at":CREATED_AT}],
      "products":[{"product_id":"product:mind","name":"MIND","owner":"Collaborative Dynamics","canonical_uri":"https://github.com/Stunspot/augment-of-mind","created_at":CREATED_AT}],
      "providers":[{"provider_id":provider_id,"name":"Ollama qwen3-embedding 0.6b","owner":"local operator","provider_kind":"local_embedding","canonical_uri":"https://ollama.com/library/qwen3-embedding:0.6b","created_at":CREATED_AT}],
      "capabilities":capabilities,"distributions":[],"receipts":[],"lifecycle_observations":[],"mounts":[]}
    (root/"associative-bootstrap.json").write_text(json.dumps(bootstrap,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    texts=[]; view_refs=[]
    for card in cards_source["cards"]:
        for kind in VIEWS:
            texts.append(card["views"][kind]); view_refs.append((card["handle"],kind))
    vectors=embed(texts)
    dims=len(vectors[0])
    if dims < 32 or any(len(v) != dims for v in vectors):
        raise RuntimeError("embedding dimensions are inconsistent")
    lexical={"lexical_profile_id":"lexical:nfkc-contiguous-v1","name":"MIND exhaustive lexical cue profile",
      "normalization_contract":"nfkc-casefold-contiguous-token-v1","unicode_token_grammar":r"\w+(?:[.:/-]\w+)* under Python Unicode semantics",
      "cue_membership_contract":"Complete contiguous hint-token sequence; exhaustive over visible approved surfaces.","created_at":CREATED_AT}
    lexical["profile_digest"]=digest(lexical,"profile_digest")
    evidence_path=EVIDENCE_PATH
    evidence_digest=hashlib.sha256(evidence_path.read_bytes()).hexdigest()
    profile={"embedding_profile_id":"embedding:ollama-qwen3-embedding-0.6b-mind-2.1-unqualified-r2","name":"Ollama qwen3-embedding 0.6b MIND 2.1 unqualified neighborhood",
      "provider_id":provider_id,"model_id":MODEL,"dimensions":dims,"metric":"cosine_distance","radius":0.40,
      "comparison_tolerance":1e-6,"vector_encoding":"float32_le","qualification_state":"unqualified",
      "qualification_evidence_ref":"verification/mind-associative-profile.md",
      "qualification_digest":evidence_digest,
      "created_at":QUALIFIED_AT}
    profile["profile_digest"]=digest(profile,"profile_digest")
    clusters=[]
    for h,(n,d) in CLUSTERS.items():
        x={"cluster_id":f"cluster:{h}","handle":h,"name":n,"description":d,"source_id":source_id,"source_digest":source_digest,"created_at":CREATED_AT}
        x["cluster_digest"]=digest(x,"cluster_digest"); clusters.append(x)
    manifest_cards=[]; vector_rows=[]
    vector_map=dict(zip(view_refs,vectors))
    for card in cards_source["cards"]:
        h=card["handle"]; card_id=f"card:{h}:r1"; views=[]
        for kind in VIEWS:
            content=card["views"][kind]
            views.append({"capability_card_view_id":f"view:{h}:{kind}:r1","view_kind":kind,"content":content,
              "content_digest":sha256_text(content),"created_at":CREATED_AT})
            packed=struct.pack("<"+str(dims)+"f",*vector_map[(h,kind)])
            vector_rows.append({"capability_card_view_id":f"view:{h}:{kind}:r1","values":list(struct.unpack("<"+str(dims)+"f",packed)),
              "vector_digest":hashlib.sha256(packed).hexdigest()})
        x={"capability_card_id":card_id,"capability_id":f"capability:{h}","revision":1,"compact_projection":card["projection"],
          "boundaries":card["boundaries"],"cluster_id":f"cluster:{card['cluster']}","exposure_policy":"public_safe",
          "owner_agent_instance_id":None,"source_id":source_id,"source_digest":source_digest,"context_cost":96,"created_at":CREATED_AT}
        x["card_digest"]=digest({**x,"views":[{**v,"capability_card_id":card_id} for v in sorted(views,key=lambda row:row["capability_card_view_id"])]},"card_digest")
        x["views"]=views; manifest_cards.append(x)
    relations=[]
    for i,(a,b,k) in enumerate(RELATIONS,1):
        x={"capability_relation_id":f"relation:mind:{i:02d}:r1","from_capability_card_id":f"card:{a}:r1",
          "to_capability_card_id":f"card:{b}:r1","relation_kind":k,"source_id":source_id,"source_digest":source_digest,"created_at":CREATED_AT}
        x["relation_digest"]=digest(x,"relation_digest"); relations.append(x)
    estate=[]
    for cap in sorted(capabilities,key=lambda x:x["capability_id"]):
        estate.append({"capability_id":cap["capability_id"],"handle":cap["handle"],"exposure_policy":"public_safe",
          "owner_agent_instance_id":None,"aliases":[{"namespace":a["namespace"],"normalized_alias":a["alias"].casefold(),"display_alias":a["display_alias"]} for a in cap["aliases"]]})
    snapshot={"associative_index_snapshot_id":"snapshot:mind-2.1:qwen3-0.6b:unqualified-r2","embedding_profile_id":profile["embedding_profile_id"],
      "lexical_profile_id":lexical["lexical_profile_id"],"vector_coverage_state":"complete",
      "estate_digest":sha256_text(canonical_json(estate)),
      "source_digest":sha256_text(canonical_json([(source_id,source_digest)])),
      "card_digest":sha256_text(canonical_json(sorted(x["card_digest"] for x in manifest_cards))),
      "profile_digest":sha256_text(canonical_json([lexical["profile_digest"],profile["profile_digest"]])),
      "builder_identity":"MIND 2.1 deterministic associative asset builder","evidence_boundary":"Reviewed views plus local model vectors; this successor profile is unqualified pending separate behavioral and fresh-host evidence.",
      "created_at":QUALIFIED_AT,"expected_card_count":len(manifest_cards),"expected_relation_count":len(relations),"expected_vector_count":len(vector_rows)}
    material={k:v for k,v in snapshot.items() if k not in {"snapshot_digest","expected_card_count","expected_relation_count","expected_vector_count"}}
    material.update({"cards":sorted((x["capability_card_id"],x["card_digest"]) for x in manifest_cards),
      "clusters":sorted((x["cluster_id"],x["cluster_digest"]) for x in clusters),
      "relations":sorted((x["capability_relation_id"],x["relation_digest"]) for x in relations),
      "vectors":sorted((x["capability_card_view_id"],x["vector_digest"]) for x in vector_rows)})
    snapshot["snapshot_digest"]=sha256_text(canonical_json(material))
    index={"format":"mind-associative-index/v1","lexical_profile":lexical,"embedding_profile":profile,"clusters":clusters,
      "cards":manifest_cards,"relations":relations,"snapshot":snapshot,"vectors":vector_rows,
      "activation":{"associative_snapshot_activation_id":"activation:mind-2.1:qwen3-0.6b:unqualified-r2","prior_associative_index_snapshot_id":None,"activated_at":QUALIFIED_AT}}
    (root/"associative-index-qwen3-embedding-0.6b.json").write_text(json.dumps(index,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"cards":len(manifest_cards),"views":len(vector_rows),"dimensions":dims,"source_sha256":source_digest,"snapshot_sha256":snapshot["snapshot_digest"]},indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
