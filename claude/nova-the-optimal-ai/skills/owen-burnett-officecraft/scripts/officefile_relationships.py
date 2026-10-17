"""Exact Officefile artifact relationships and declared production-input revisions.

These records detect drift; they do not prove that an artifact faithfully used its
inputs. Record a basis during real production or a documented reconciliation.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from officefile_safety import member_path

STRONG = {'produced', 'inspected', 'reviewed', 'approved'}

def value_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8')).hexdigest()

def file_digest(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()

def declared_ids(artifact, key):
    values = artifact.get(key, [])
    if not isinstance(values, list) or any(not isinstance(x, str) or not x.strip() for x in values) or len(values) != len(set(values)):
        raise ValueError(f'{key} must contain unique non-empty identifiers')
    return values

def parents(artifact):
    result = list(declared_ids(artifact, 'input_artifact_ids'))
    parent = artifact.get('canonical_source_id')
    if parent is not None:
        if not isinstance(parent, str) or not parent.strip():
            raise ValueError('canonical_source_id must be a non-empty identifier or null')
        if parent not in result:
            result.append(parent)
    return sorted(result)

def has_inputs(artifact):
    return bool(parents(artifact) or declared_ids(artifact, 'source_ids') or declared_ids(artifact, 'ledger_item_ids'))

def current_basis(root, artifact_id, artifacts, sources, ledger):
    """Snapshot only declared dependencies, including transitive artifact inputs."""
    row = artifacts[artifact_id]
    basis = {'format': 'officecraft-input-basis/v1', 'declared_inputs': {'artifact_ids': parents(row), 'source_ids': sorted(declared_ids(row, 'source_ids')), 'ledger_item_ids': sorted(declared_ids(row, 'ledger_item_ids'))}, 'artifacts': {}, 'sources': {}, 'ledger': {}}
    active = []
    visited = set()
    def source(source_id):
        if source_id not in sources:
            raise ValueError(f'unknown source_id {source_id}')
        row = sources[source_id]
        path = member_path(root, row.get('path'))
        if path is None or not path.is_file():
            raise ValueError(f'source {source_id} has no safe current file')
        basis['sources'][source_id] = {'path': row['path'].replace('\\', '/'), 'sha256': file_digest(path), 'custody_status': row.get('custody_status'), 'content_status': row.get('content_status')}
    def visit(current, include_artifact):
        if current in active:
            raise ValueError('artifact dependency cycle: ' + ' -> '.join(active + [current]))
        if current not in artifacts:
            raise ValueError(f'unknown artifact dependency {current}')
        if current in visited:
            return
        active.append(current)
        row = artifacts[current]
        links = parents(row)
        source_ids = declared_ids(row, 'source_ids')
        ledger_ids = declared_ids(row, 'ledger_item_ids')
        if include_artifact:
            path = member_path(root, row.get('path'))
            if path is None or not path.is_file():
                raise ValueError(f'artifact dependency {current} has no safe current file')
            basis['artifacts'][current] = {'path': row['path'].replace('\\', '/'), 'sha256': file_digest(path), 'artifact_ids': links, 'source_ids': sorted(source_ids), 'ledger_item_ids': sorted(ledger_ids)}
        for sid in source_ids:
            source(sid)
        for lid in ledger_ids:
            if lid not in ledger:
                raise ValueError(f'unknown ledger_item_id {lid}')
            item = ledger[lid]
            basis['ledger'][lid] = value_digest(item)
            for sid in item.get('source_ids', []):
                source(sid)
        for parent in links:
            visit(parent, True)
        active.pop()
        visited.add(current)
    visit(artifact_id, False)
    return basis

def validate_relationships(root, artifacts, sources, ledger, errors, warnings):
    paths = {}
    graph = {}
    for aid, row in artifacts.items():
        relative = row.get('path')
        if isinstance(relative, str):
            path = member_path(root, relative)
            normalized = str(path).casefold() if path is not None else None
            if normalized is not None and normalized in paths:
                errors.append(f'artifacts {paths[normalized]} and {aid}: duplicate current artifact path')
            elif normalized is not None:
                paths[normalized] = aid
        try:
            graph[aid] = parents(row)
            declared_ids(row, 'source_ids'); declared_ids(row, 'ledger_item_ids')
            if row.get('role') == 'derivative' and row.get('status') in STRONG and row.get('canonical_source_id') is None:
                errors.append(f'artifact {aid}: produced derivative requires its canonical_source_id; preserve old files and reconcile the source relationship')
            for parent in graph[aid]:
                if parent not in artifacts:
                    (errors if row.get('status') in STRONG else warnings).append(f'artifact {aid}: unresolved artifact dependency {parent}')
        except ValueError as exc:
            errors.append(f'artifact {aid}: {exc}')
    seen = set()
    active = []
    def visit(aid):
        if aid in active:
            errors.append('artifact dependency cycle: ' + ' -> '.join(active + [aid])); return
        if aid in seen:
            return
        active.append(aid)
        for parent in graph.get(aid, []):
            visit(parent)
        active.pop(); seen.add(aid)
    for aid in graph:
        visit(aid)
    for aid, row in artifacts.items():
        try:
            if not has_inputs(row):
                if row.get('input_basis') is not None:
                    expected = current_basis(root, aid, artifacts, sources, ledger)
                    if row['input_basis'] != expected:
                        errors.append(f'artifact {aid}: input basis no longer matches its declared inputs')
                continue
            if row.get('status') not in STRONG:
                continue
            expected = current_basis(root, aid, artifacts, sources, ledger)
            if row.get('input_basis') != expected:
                errors.append(f'artifact {aid}: production input basis missing or stale; preserve output and regenerate or record an evidenced reconciliation, not a blind recapture')
        except (ValueError, OSError, TypeError) as exc:
            errors.append(f'artifact {aid}: cannot establish current input basis: {exc}')
def empty_basis():
    return {'format': 'officecraft-input-basis/v1', 'declared_inputs': {'artifact_ids': [], 'source_ids': [], 'ledger_item_ids': []}, 'artifacts': {}, 'sources': {}, 'ledger': {}}

def basis_digest(artifact):
    return value_digest(artifact.get('input_basis') or empty_basis())
