#!/usr/bin/env python3
"""Structural integrity and projection mechanics for Observatory cases.

The guardrail validates syntax, references, capture fields, time order,
coordinate ranges, readiness subject bindings, and projection invariants. It does
not determine credibility, identity, truth, causation, privacy, legal safety,
editorial approval, or whether a case should be published.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import copy
import math
from safe_io import load, finite, relative_name, contained, reject_links, bytes_json, write_new, write_bundle
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


BOUNDARY = "STRUCTURAL_INTEGRITY_ONLY"
FORMAT = "cd-observatory-case/v1"
PHASES = {"orient", "scoped", "collecting", "preserved", "normalized", "related", "challenged", "watching", "presenting", "review", "handoff"}
POSTURES = {"provisional", "blocked", "reviewable", "watch-ready", "publication-ready"}
COLLECTIONS = ("sources", "captures", "observations", "claims", "events", "entities", "relations", "inferences", "hypotheses", "contradictions", "assessments", "recommendations", "decisions", "outcomes", "artifacts", "checks", "blockers", "history")
INVARIANT_FIELDS = ("id", "kind", "status", "confidence", "uncertainty", "provenance_ids")
SHA_RE = re.compile(r"^[0-9A-Fa-f]{64}$")
UNRESOLVED = {"candidate", "disputed", "open", "provisional", "unresolved", "unverified"}


def load_json(path: Path) -> dict[str, Any]:
    value = load(path)
    if not isinstance(value, dict): raise ValueError("JSON root must be an object")
    return value


def write_json(path: Path, value: Any) -> None:
    write_new(path, bytes_json(value))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


TIME_FIELDS = ("published_at", "updated_at", "retrieved_at", "observed_at", "event_start", "event_end", "first_seen_at", "last_seen_at", "reviewed_at")
TIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$")


def parse_time(value: Any, field: str, errors: list[str], item_id: str) -> datetime | None:
    if value is None or value == "": return None
    if not isinstance(value, str) or not TIME_RE.fullmatch(value):
        errors.append(f"{item_id}: {field} requires YYYY-MM-DDTHH:MM:SS with known Z or numeric offset")
        return None
    if value.endswith("-00:00") or (value[-1] != "Z" and (int(value[-5:-3]) > 23 or int(value[-2:]) > 59)):
        errors.append(f"{item_id}: {field} has unknown or invalid timezone offset")
        return None
    # Host ISO parsers may normalize 24:00 into tomorrow; this contract does not.
    if int(value[11:13]) > 23 or int(value[14:16]) > 59 or int(value[17:19]) > 59:
        errors.append(f"{item_id}: {field} requires hours 00-23 and minutes/seconds 00-59")
        return None
    try: return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"{item_id}: {field} is not a valid timestamp")
        return None


def canonical_url(url: str) -> str:
    if not isinstance(url, str) or not url.strip() or any(ord(c)<32 for c in url): raise ValueError("Capture URL must be a nonempty URL string without controls")
    parts = urlsplit(url.strip())
    if parts.scheme.lower() == "file":
        if parts.netloc.lower() not in {"", "localhost"} or not parts.path.startswith("/") or parts.query:
            raise ValueError("Local file capture requires an absolute file URI without query or remote host")
        return urlunsplit(("file", "", parts.path, "", ""))
    if parts.scheme.lower() not in {"http", "https"} or not parts.hostname: raise ValueError("Capture URL must use http, https, or an absolute local file URI")
    if parts.username is not None or parts.password is not None: raise ValueError("URLs with embedded credentials are not allowed")
    host = parts.hostname.lower(); host = '['+host+']' if ':' in host else host
    port = parts.port
    default_port = (parts.scheme.lower()=="http" and port==80) or (parts.scheme.lower()=="https" and port==443)
    netloc = host if port is None or default_port else f"{host}:{port}"
    tracking = {"fbclid", "gclid", "mc_cid", "mc_eid"}
    # Preserve parameter ordering and exact encoding; normalization never establishes source identity.
    query = '&'.join(part for part in parts.query.split('&') if part and not any(k.lower() in tracking or k.lower().startswith('utm_') for k,_ in parse_qsl(part,keep_blank_values=True)))
    return urlunsplit((parts.scheme.lower(), netloc, parts.path or "/", query, ""))


def text(value): return isinstance(value,str) and bool(value.strip())


def subject_sha256(case):
    # Checks are review evidence, not the subject; phase/posture/history are administrative.
    # Every other root field and all substantive records, artifact paths/hashes and watch inputs are bound.
    value={k:v for k,v in case.items() if k not in {'checks','phase','posture','history'}}
    return hashlib.sha256(__import__('json').dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf8')).hexdigest()


def _all_items(case: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    output: list[tuple[str, dict[str, Any]]] = []
    for collection in COLLECTIONS:
        values = case.get(collection, [])
        if isinstance(values, list):
            output.extend((collection, item) for item in values if isinstance(item, dict))
    return output


def validate_case(case: dict[str, Any], root: Path | None = None) -> list[str]:
    errors=[]
    if not isinstance(case,dict): return ["Case must be an object"]
    try: finite(case)
    except ValueError as exc: return [str(exc)]
    if case.get('format')!=FORMAT: errors.append('format must be '+FORMAT)
    for field in ('case_id','title','question','audience_or_decision','time_horizon','scope','collection_authority','harm_model','evidence_burden','stop_condition'):
        if not text(case.get(field)):errors.append(field+' is required as nonempty text')
    for field,allowed in [('phase',PHASES),('posture',POSTURES)]:
        if not isinstance(case.get(field),str) or case[field] not in allowed:errors.append(field+' is missing or invalid')
    identifiers={};items=[]
    for collection in COLLECTIONS:
        values=case.get(collection)
        if not isinstance(values,list):errors.append(collection+' must be an array');continue
        for index,item in enumerate(values):
            if not isinstance(item,dict) or not text(item.get('id')):
                errors.append(f'{collection}[{index}] requires an object with stable text id');continue
            if item['id'] in identifiers:errors.append('duplicate id: '+item['id'])
            identifiers[item['id']]=collection;items.append((collection,item))
    targets={name[:-1]+'_ids':name for name in COLLECTIONS}
    targets.update(entity_ids='entities',hypothesis_ids='hypotheses')
    cutoff=parse_time(case.get('evidence_as_of'),'evidence_as_of',errors,'case')
    for collection,item in items:
        iid=item['id']
        for field in ('status','confidence','uncertainty','kind','title','summary','statement','name','reason'):
            if field in item and not text(item[field]):errors.append(f'{iid}: {field} must be nonempty text when supplied')
        for field,value in item.items():
            if not field.endswith('_ids'):continue
            if not isinstance(value,list):errors.append(f'{iid}: {field} must be an array');continue
            seen=set()
            for ref in value:
                if not text(ref):errors.append(f'{iid}: {field} references must be text IDs');continue
                if ref in seen:errors.append(f'{iid}: duplicate {field} reference {ref}')
                seen.add(ref)
                if ref not in identifiers:errors.append(f'{iid}: dangling {field} reference {ref}')
                elif field in targets and identifiers[ref]!=targets[field]:errors.append(f'{iid}: {field} reference {ref} has wrong record type')
        for field in ('high_risk','material_to_publication'):
            if field in item and type(item[field]) is not bool:errors.append(f'{iid}: {field} must be boolean')
        if collection=='relations':
            for field in ('from_id','to_id'):
                if not text(item.get(field)) or item[field] not in identifiers:errors.append(f'{iid}: {field} requires an existing typed endpoint')
            if not text(item.get('relation_type')):errors.append(f'{iid}: relation_type is required')
        times={field:parse_time(item.get(field),field,errors,iid) for field in TIME_FIELDS if field in item}
        for first,last in [('first_seen_at','last_seen_at'),('event_start','event_end')]:
            if times.get(first) and times.get(last) and times[first]>times[last]:errors.append(f'{iid}: {first} is after {last}')
        if cutoff:
            for field in ('retrieved_at','observed_at','first_seen_at','last_seen_at'):
                if times.get(field) and times[field]>cutoff:errors.append(f'{iid}: {field} is after evidence_as_of')
        if collection=='captures':
            for field in ('source_ids','original_url','canonical_url','preservation_status'):
                if field not in item or item[field] is None or item[field]=='' or item[field]==[]:errors.append(f'{iid}: capture requires {field}')
            try:
                if item.get('canonical_url')!=canonical_url(item.get('original_url')):errors.append(f'{iid}: canonical_url does not match deterministic normalization')
            except (ValueError,TypeError) as exc:errors.append(f'{iid}: {exc}')
            if times.get('published_at') and times.get('retrieved_at') and times['published_at']>times['retrieved_at']:errors.append(f'{iid}: publication follows retrieval; retain uncertain source metadata as text instead of inventing a chronology')
            if item.get('preservation_status')=='preserved':
                if not times.get('retrieved_at'):errors.append(f'{iid}: preserved capture requires a known retrieval time')
                try:relative_name(item.get('artifact_path'))
                except ValueError:errors.append(f'{iid}: preserved capture requires a portable artifact_path')
                if not isinstance(item.get('sha256'),str) or not SHA_RE.fullmatch(item['sha256']):errors.append(f'{iid}: preserved capture requires SHA-256')
            elif item.get('preservation_status') not in ('unavailable','partial'):errors.append(f'{iid}: preservation_status must be preserved, unavailable or partial')
            elif not text(item.get('failure')):errors.append(f'{iid}: incomplete capture requires failure explanation')
        loc=item.get('location')
        if loc is not None:
            if not isinstance(loc,dict):errors.append(f'{iid}: location must be an object')
            else:
                lat,lon=loc.get('latitude'),loc.get('longitude')
                for field,value,bound in [('latitude',lat,90),('longitude',lon,180)]:
                    if value is not None and (type(value) not in (int,float) or not math.isfinite(value) or not -bound<=value<=bound):errors.append(f'{iid}: {field} is outside -{bound}..{bound}')
                if (lat is None)!=(lon is None):errors.append(f'{iid}: latitude and longitude must appear together')
                if lat is None and not text(loc.get('region')):errors.append(f'{iid}: uncertain location requires a region label')
        if collection=='checks':
            if 'evidence_files' in item:
                if not isinstance(item['evidence_files'],list) or any(not isinstance(v,dict) for v in item['evidence_files']):errors.append(f'{iid}: evidence_files must be an array of objects')
            if 'check_type' in item and not text(item['check_type']):errors.append(f'{iid}: check_type must be text')
        if 'support' in item:
            if not isinstance(item['support'],list):errors.append(f'{iid}: support must be an array')
            else:
                for support in item['support']:
                    if not isinstance(support,dict):errors.append(f'{iid}: support entry must be an object');continue
                    cap=support.get('capture_id')
                    if not text(cap) or identifiers.get(cap)!='captures':errors.append(f'{iid}: support requires an existing capture_id')
                    if support.get('relation') not in ('supports','refutes','context','reports'):errors.append(f'{iid}: support relation must be supports, refutes, context or reports')
                    for field in ('locator','excerpt','rationale'):
                        if not text(support.get(field)):errors.append(f'{iid}: support requires {field}')
    action=case.get('next_action')
    if not isinstance(action,dict):errors.append('next_action must be an object')
    else:
        for field in ('action','owner','advance_when'):
            if not text(action.get(field)):errors.append('next_action requires text '+field)
    if case.get('posture') in ('watch-ready','publication-ready') and not errors:
        errors.extend(readiness_errors(case))
    if root is not None and not errors:errors.extend(audit_files(case,root))
    return sorted(set(errors))


def readiness_errors(case):
    errors=[];posture=case['posture'];subject=subject_sha256(case)
    required=('watch-specification','baseline-integrity') if posture=='watch-ready' else ('provenance','citation-integrity','redaction','editorial-challenge')
    if posture=='watch-ready':
        watch=case.get('watch')
        if not isinstance(watch,dict):errors.append('watch-ready requires a watch specification')
        else:
            for key in ('baseline_case_id','cadence','owner','change_threshold','resume_action'):
                if not text(watch.get(key)):errors.append('watch specification requires '+key)
            if not isinstance(watch.get('triggers'),list) or not watch['triggers'] or any(not text(v) for v in watch['triggers']):errors.append('watch requires substantive triggers')
    else:
        target=case.get('publication_artifact_id')
        artifact=next((a for a in case['artifacts'] if a['id']==target),None)
        if not artifact or artifact.get('artifact_type')!='publication-package':errors.append('publication-ready requires a named publication-package artifact')
        elif not text(artifact.get('path')) or not isinstance(artifact.get('sha256'),str) or not SHA_RE.fullmatch(artifact['sha256']):errors.append('publication package needs path and SHA-256')
        if publication_blockers(case):errors.append('publication-ready is blocked by material unresolved conditions')
    for kind in required:
        relevant=[c for c in case['checks'] if c.get('check_type')==kind]
        if not relevant or not any(c.get('status')=='passed' for c in relevant):errors.append(posture+' requires passed '+kind+' check')
        for check in relevant:
            iid=check['id']
            if check.get('status')!='passed':errors.append(f'{iid}: unresolved or nonpassing {kind} check prevents readiness');continue
            if check.get('subject_sha256')!=subject:errors.append(f'{iid}: review subject is absent or stale')
            for field in ('reviewer','method','rationale','reviewed_at'):
                if not text(check.get(field)):errors.append(f'{iid}: completed review requires {field}')
            reviewed=parse_time(check.get('reviewed_at'),'reviewed_at',errors,iid)
            known=[parse_time(c.get('retrieved_at'),'retrieved_at',[],c['id']) for c in case['captures']]
            if reviewed and any(t and t>reviewed for t in known):errors.append(f'{iid}: review predates evidence retrieval')
            if posture=='publication-ready' and check.get('artifact_id')!=case.get('publication_artifact_id'):errors.append(f'{iid}: review must name the selected publication artifact')
            proofs=check.get('evidence_files')
            if not isinstance(proofs,list) or not proofs:errors.append(f'{iid}: review requires retained evidence_files')
            else:
                for proof in proofs:
                    if not isinstance(proof,dict):errors.append(f'{iid}: evidence file must be an object');continue
                    try:relative_name(proof.get('path'))
                    except ValueError:errors.append(f'{iid}: evidence file path is invalid')
                    if not isinstance(proof.get('sha256'),str) or not SHA_RE.fullmatch(proof['sha256']):errors.append(f'{iid}: evidence file hash is invalid')
    return errors


def publication_blockers(case):
    blockers=[]
    for collection in ('blockers','entities','claims'):
        values=case.get(collection,[])
        if not isinstance(values,list):continue
        for item in values:
            if not isinstance(item,dict):continue
            blocked=(collection=='blockers' and item.get('status','open') not in ('closed','resolved') and item.get('severity') in ('high','material')) or (collection=='entities' and item.get('resolution_status') in ('collision','unresolved') and item.get('material_to_publication') is True) or (collection=='claims' and item.get('high_risk') is True and item.get('human_review')!='approved')
            if blocked:blockers.append(str(item.get('id','unnamed blocker')))
    return sorted(set(blockers))


def audit_files(case,root):
    errors=[]
    def verify(iid,path,digest):
        try:
            p=contained(root,path)
            if not p.is_file():raise ValueError('missing regular file')
            if not isinstance(digest,str) or sha256(p).lower()!=digest.lower():raise ValueError('bytes do not match SHA-256')
        except (OSError,ValueError) as exc:errors.append(f'{iid}: {path}: {exc}')
    for cap in case['captures']:
        if cap.get('preservation_status')=='preserved':verify(cap['id'],cap.get('artifact_path'),cap.get('sha256'))
    for artifact in case['artifacts']:
        if artifact.get('sha256') or artifact.get('artifact_type')=='publication-package':verify(artifact['id'],artifact.get('path'),artifact.get('sha256'))
    for check in case['checks']:
        if check.get('status')=='passed':
            for proof in check.get('evidence_files',[]):
                if isinstance(proof,dict):verify(check['id'],proof.get('path'),proof.get('sha256'))
    for _,item in _all_items(case):
        for support in item.get('support',[]):
            cap=next((c for c in case['captures'] if c['id']==support['capture_id']),None)
            if cap and cap.get('preservation_status')=='preserved':
                try:
                    content=contained(root,cap['artifact_path']).read_text(encoding='utf-8-sig')
                    if support['excerpt'] not in content:errors.append(item['id']+': excerpt absent from captured UTF-8 source')
                except (OSError,ValueError,UnicodeError) as exc:errors.append(item['id']+': excerpt cannot be checked: '+str(exc))
    return errors


def common(item: dict[str, Any], kind: str) -> dict[str, Any]:
    return {
        "id": item["id"],
        "kind": item.get("kind", {"entities":"entity","hypotheses":"hypothesis"}.get(kind,kind[:-1])),
        "status": item.get("status", "unresolved"),
        "confidence": item.get("confidence", "unrated"),
        "uncertainty": item.get("uncertainty", "not stated"),
        "provenance_ids": item.get("provenance_ids", item.get("source_ids", item.get("capture_ids", []))),
    }


def project_case(case: dict[str, Any]) -> dict[str, Any]:
    ledger: list[dict[str, Any]] = []
    registry: dict[str, dict[str, Any]] = {}
    for collection, item in _all_items(case):
        projected = common(item, collection)
        projected["summary"] = item.get("summary", item.get("statement", item.get("name", item.get("title", ""))))
        ledger.append(projected)
        registry[item["id"]] = projected

    node_collections = set(COLLECTIONS) - {"relations"}
    nodes = [dict(common(item, collection), label=item.get("name", item.get("title", item.get("statement", item["id"])))) for collection, item in _all_items(case) if collection in node_collections]
    edges = []
    for relation in case.get("relations", []):
        if not isinstance(relation, dict):
            continue
        edge = common(relation, "relations")
        edge.update({"from_id": relation.get("from_id"), "to_id": relation.get("to_id"), "relation_type": relation.get("relation_type", "unspecified")})
        edges.append(edge)

    timeline = []
    for collection,item in _all_items(case):
        for clock in TIME_FIELDS:
            if clock=='reviewed_at' or not item.get(clock):continue
            entry=common(item,collection)
            entry.update(time=item[clock],time_kind=clock,label=item.get('summary',item.get('statement',item.get('title',item['id']))))
            timeline.append(entry)
    timeline.sort(key=lambda item:(parse_time(item['time'],'time',[],item['id']),item['id'],item['time_kind']))

    features = []
    for collection in ("events", "entities", "observations"):
        for item in case.get(collection, []):
            if not isinstance(item, dict) or not isinstance(item.get("location"), dict):
                continue
            location = item["location"]
            geometry = None
            if location.get("latitude") is not None and location.get("longitude") is not None:
                geometry = {"type": "Point", "coordinates": [location["longitude"], location["latitude"]]}
            properties = common(item, collection)
            properties.update({"label": item.get("summary", item.get("name", item["id"])), "region": location.get("region"), "precision": location.get("precision", "unknown")})
            features.append({"type": "Feature", "id": item["id"], "geometry": geometry, "properties": properties})
    return {
        "ledger": {"format": "cd-observatory-ledger/v1", "case_id": case["case_id"], "items": sorted(ledger, key=lambda item: item["id"])},
        "graph": {"format": "cd-observatory-graph/v1", "case_id": case["case_id"], "nodes": sorted(nodes, key=lambda item: item["id"]), "edges": sorted(edges, key=lambda item: item["id"])},
        "timeline": {"format": "cd-observatory-timeline/v1", "case_id": case["case_id"], "items": timeline},
        "map": {"type": "FeatureCollection", "observatory_format": "cd-observatory-map/v1", "case_id": case["case_id"], "features": sorted(features, key=lambda item: item["id"])},
        "registry": registry,
    }


def verify_projection_invariants(case,projections):
    expected=project_case(case);errors=[]
    if not isinstance(projections,dict):return ['Projection must be an object']
    for view in expected:
        if projections.get(view)!=expected[view]:errors.append(view+': projection changed invariant, inventory, clock, geometry, relationship or source-derived field')
    return errors


def semantic_fingerprint(item):
    return hashlib.sha256(json.dumps(item,sort_keys=True,ensure_ascii=False,allow_nan=False).encode('utf8')).hexdigest()


def delta_report(baseline,current):
    for name,case in [('baseline',baseline),('current',current)]:
        errors=validate_case(case)
        if errors:raise ValueError(name+': '+'; '.join(errors))
    if baseline.get('inquiry_id',baseline['case_id'])!=current.get('inquiry_id',current['case_id']):raise ValueError('Compare revisions of the same inquiry; record a shared inquiry_id explicitly')
    base={(kind,item['id']):item for kind,item in _all_items(baseline)};now={(kind,item['id']):item for kind,item in _all_items(current)}
    classes={k:[] for k in ('newly_represented','changed','currentness_changed','no_longer_represented','corrected_or_superseded','newly_contradicted','newly_unsupported','unchanged','still_unresolved')}
    for key in sorted(set(base)|set(now)):
        before,after=base.get(key),now.get(key);iid=key[1]
        if before is None:classes['newly_represented'].append(iid)
        elif after is None:classes['no_longer_represented'].append(iid)
        elif before==after:classes['unchanged'].append(iid)
        else:
            clocks={'retrieved_at','last_seen_at','first_seen_at','observed_at'}
            changed={k for k in set(before)|set(after) if before.get(k)!=after.get(k)}
            classes['currentness_changed' if changed<=clocks else 'changed'].append(iid)
        if after:
            status=after.get('status')
            if (before is None or before.get('status')!=status) and status in ('corrected','superseded'):classes['corrected_or_superseded'].append(iid)
            if (before is None or before.get('supersedes_ids')!=after.get('supersedes_ids')) and after.get('supersedes_ids'):classes['corrected_or_superseded'].append(iid)
            if (before is None or before.get('status')!=status) and status=='contradicted':classes['newly_contradicted'].append(iid)
            if (before is None or before.get('status')!=status) and status in ('unsupported','withdrawn'):classes['newly_unsupported'].append(iid)
            if status in UNRESOLVED:classes['still_unresolved'].append(iid)
    return {'format':'cd-observatory-delta/v2','baseline_case_id':baseline['case_id'],'current_case_id':current['case_id'],'inquiry_id':current.get('inquiry_id',current['case_id']),'classes':{k:sorted(set(v)) for k,v in classes.items()},'case_fields_changed':[k for k in sorted(set(baseline)|set(current)) if k not in COLLECTIONS and baseline.get(k)!=current.get(k)],'semantic_truth_assessed':False,'materiality_assessed':False}


def receipt(file_path: Path, source_id: str, capture_id: str, url: str, published_at: str | None, retrieved_at: str | None) -> dict[str, Any]:
    reject_links(file_path)
    errors=[]
    for key,value in [("published_at",published_at),("retrieved_at",retrieved_at)]: parse_time(value,key,errors,capture_id)
    if not text(source_id) or not text(capture_id): errors.append("Source and capture IDs must be nonempty text")
    if errors: raise ValueError("; ".join(errors))
    return {
        "id": capture_id,
        "source_ids": [source_id],
        "original_url": url,
        "canonical_url": canonical_url(url),
        "published_at": published_at,
        "retrieved_at": retrieved_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "artifact_path": file_path.name,
        "sha256": sha256(file_path),
        "preservation_status": "preserved",
        "failure": None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate-case")
    validate.add_argument("case", type=Path)
    validate.add_argument("--files",action="store_true",help="Check capture, package and review evidence bytes relative to the case")
    project = commands.add_parser("project")
    project.add_argument("case", type=Path)
    project.add_argument("output", type=Path)
    delta = commands.add_parser("delta")
    delta.add_argument("baseline", type=Path)
    delta.add_argument("current", type=Path)
    delta.add_argument("output", type=Path, nargs="?")
    capture = commands.add_parser("capture-receipt")
    capture.add_argument("file", type=Path)
    capture.add_argument("--source-id", required=True)
    capture.add_argument("--capture-id", required=True)
    capture.add_argument("--url", required=True)
    capture.add_argument("--published-at")
    capture.add_argument("--retrieved-at")
    capture.add_argument("--output", type=Path)
    capture.add_argument("--case-root",type=Path,help="Root for the recorded relative capture path; defaults to the capture parent")
    publication = commands.add_parser("audit-publication")
    publication.add_argument("case", type=Path)
    subject=commands.add_parser("review-subject",help="Print the current review subject digest; this performs no review")
    subject.add_argument("case",type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "capture-receipt":
            result = receipt(args.file, args.source_id, args.capture_id, args.url, args.published_at, args.retrieved_at)
            root=reject_links(args.case_root or args.file.parent)
            file=reject_links(args.file)
            if not file.is_relative_to(root): raise ValueError("Capture must remain under case-root")
            result["artifact_path"]=file.relative_to(root).as_posix()
            if args.output:
                write_json(args.output, result)
            else:
                print(json.dumps(result, indent=2))
            return 0
        if args.command == "delta":
            result = delta_report(load_json(args.baseline), load_json(args.current))
            if args.output:
                write_json(args.output, result)
            else:
                print(json.dumps(result, indent=2))
            return 0
        case = load_json(args.case)
        if args.command=="review-subject":
            errors=validate_case(dict(case,posture="provisional"))
            if errors:raise ValueError("; ".join(errors))
            print(json.dumps({"subject_sha256":subject_sha256(case),"review_performed":False}));return 0
        errors = validate_case(case,args.case.parent if args.command=="audit-publication" or getattr(args,"files",False) else None)
        if args.command == "validate-case":
            result = {"label": BOUNDARY, "valid": not errors, "errors": errors, "semantic_truth_assessed": False,"file_custody_assessed":args.files}
            print(json.dumps(result, indent=2))
            return 0 if not errors else 1
        if args.command == "audit-publication":
            blockers = publication_blockers(case)
            result = {"label": BOUNDARY, "structurally_publishable": case.get("posture")=="publication-ready" and not errors and not blockers, "case_errors": errors, "blockers": blockers, "truth_legality_safety_assessed": False}
            print(json.dumps(result, indent=2))
            return 0 if result["structurally_publishable"] else 1
        if errors:
            print(json.dumps({"label": BOUNDARY, "valid": False, "errors": errors}, indent=2))
            return 1
        projections = project_case(case)
        invariant_errors = verify_projection_invariants(case, projections)
        if invariant_errors:raise ValueError('; '.join(invariant_errors))
        items={name+'.json':bytes_json(projections[name]) for name in ('ledger','graph','timeline','map')}
        manifest={'format':'cd-observatory-projection-manifest/v1','case_id':case['case_id'],'subject_sha256':subject_sha256(case),'invariant_errors':[],'files':[{'path':name,'sha256':hashlib.sha256(data).hexdigest()} for name,data in items.items()],'semantic_truth_assessed':False}
        items['projection-manifest.json']=bytes_json(manifest)
        write_bundle(args.output,items)
        print(json.dumps(manifest, indent=2))
        return 0 if not invariant_errors else 1
    except (OSError, ValueError, UnicodeError, RecursionError) as exc:
        print(json.dumps({"label": BOUNDARY, "valid": False, "errors": [str(exc)]}, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
