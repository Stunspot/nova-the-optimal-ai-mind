#!/usr/bin/env python3
"""Prepare a new binding record after real artifact production or reconciliation.

Does not change existing Officefile registers or artifacts. This captures current bytes, not proof that the
output faithfully uses them; the operator supplies and retains that evidence.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from officefile_relationships import current_basis, file_digest, value_digest
from officefile_safety import member_path, walk_officefile_files


def capture(root_value, artifact_id, kind, evidence):
    root, _, errors = walk_officefile_files(root_value)
    if root is None or errors:
        raise ValueError('; '.join(errors))
    def read(name, key, ident):
        data = json.loads((root / name).read_text(encoding='utf-8-sig'))[key]
        if not isinstance(data, list) or any(not isinstance(row, dict) or not isinstance(row.get(ident), str) for row in data):
            raise ValueError('Malformed register: ' + name)
        result = {row[ident]: row for row in data}
        if len(result) != len(data):
            raise ValueError('Duplicate identifiers: ' + name)
        return result
    artifacts = read('state/artifact-register.json', 'artifacts', 'artifact_id')
    sources = read('sources/manifest.json', 'sources', 'source_id')
    ledger = read('state/content-ledger.json', 'items', 'item_id')
    if artifact_id not in artifacts or kind not in ('produced', 'reconciled') or not isinstance(evidence, str) or not evidence.strip():
        raise ValueError('Name an existing artifact, actual production/reconciliation and its evidence')
    path = member_path(root, artifacts[artifact_id].get('path'))
    if path is None or not path.is_file():
        raise ValueError('Artifact file missing or unsafe')
    basis = current_basis(root, artifact_id, artifacts, sources, ledger)
    return {'format': 'officecraft-production-binding/v1', 'artifact_id': artifact_id, 'sha256': file_digest(path), 'input_basis': basis, 'input_basis_sha256': value_digest(basis), 'record_kind': kind, 'production_evidence': evidence, 'captured_at': datetime.now(timezone.utc).isoformat(), 'boundary': 'Current declared inputs and output bytes; no semantic verification or approval. Copy input_basis into the artifact register only after checking actual production evidence. Review the exact result before using the digest binding in a review.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('officefile'); parser.add_argument('artifact_id')
    parser.add_argument('--record-kind', required=True, choices=['produced', 'reconciled'])
    parser.add_argument('--evidence', required=True)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    try:
        result = capture(args.officefile, args.artifact_id, args.record_kind, args.evidence)
        with args.output.open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
        print(str(args.output)); return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print('Binding not recorded: ' + str(exc)); return 2


if __name__ == '__main__':
    raise SystemExit(main())