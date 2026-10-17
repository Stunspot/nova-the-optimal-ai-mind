#!/usr/bin/env python3
"""Copy an older Officefile into a new workspace; preserve old outputs and review history."""
import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from package_officefile import snapshot_officefile, snapshot_signature
from officefile_safety import is_reparse_or_symlink


def migrate(source, destination):
    root, before = snapshot_officefile(source)
    destination = Path(destination).absolute()
    if os.path.lexists(destination) or not destination.parent.is_dir():
        raise ValueError('Use a new destination with an existing parent')
    for ancestor in (destination.parent, *destination.parent.parents):
        if is_reparse_or_symlink(ancestor):
            raise ValueError('Destination parent chain contains a link or reparse point')
    if destination.resolve().is_relative_to(root):
        raise ValueError('Migration destination must be outside the original Officefile')
    def read(relative):
        return json.loads(before[relative]['path'].read_text(encoding='utf-8-sig'))
    register = read('state/artifact-register.json'); review = read('review/officecraft-review.json'); brief = read('state/brief.json')
    if register.get('format') != 'officecraft-artifact-register/v1' or review.get('format') != 'officecraft-review/v1':
        raise ValueError('This migration accepts the original v1 register and review only')
    if not isinstance(register.get('artifacts'), list) or any(not isinstance(x, dict) for x in register['artifacts']):
        raise ValueError('Malformed original artifact register; preserve and reconcile manually')
    if any(n.startswith('history/pre-v2/') or n in ('history/pre-v2', 'MIGRATION.json', 'MIGRATION-INCOMPLETE.txt') for n in before):
        raise ValueError('Historical migration path already exists; choose an explicit manual reconciliation')
    destination.mkdir()  # Exclusive creation; a failure below retains an unmistakable incomplete copy.
    marker = destination / 'MIGRATION-INCOMPLETE.txt'
    marker.write_text('Incomplete migration. Original Officefile remains the authority.\n', encoding='utf-8')
    for name, item in before.items():
        target = destination / name; target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as out:
            out.write(item['path'].read_bytes())
    _, copied = snapshot_officefile(destination)
    assert {n:(v['size'],v['sha256'])for n,v in copied.items()if n!='MIGRATION-INCOMPLETE.txt'} == snapshot_signature(before), 'Copied bytes differ'
    history = destination / 'history/pre-v2'; history.mkdir(parents=True)
    for name in ['state/artifact-register.json','review/officecraft-review.json','state/brief.json']:
        target = history / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes((destination/name).read_bytes())
    def save(name, data):
        (destination/name).write_text(json.dumps(data, indent=2, ensure_ascii=False)+'\n',encoding='utf-8',newline='\n')
    register['format'] = 'officecraft-artifact-register/v2'
    for artifact in register['artifacts']:
        artifact['legacy_status'] = artifact.get('status')
        artifact['status'] = 'planned' if artifact.get('status') == 'planned' else 'working'
        artifact.pop('input_basis', None)
        artifact['migration_note'] = 'Original output preserved. Production basis and current review unverified; regenerate or reconcile against actual evidence before stronger claims.'
    save('state/artifact-register.json',register)
    save('review/officecraft-review.json',{'format':'officecraft-review/v2','operator_review':{'status':'not_run'},'independent_review':{'status':'not_run'},'approval_records':[]})
    brief['state']='production'; brief['updated_at']=datetime.now(timezone.utc).isoformat();save('state/brief.json',brief)
    _, after = snapshot_officefile(root)
    assert snapshot_signature(before)==snapshot_signature(after), 'Original changed during migration; new copy is not accepted'
    receipt={'format':'officecraft-migration/v1','original':str(root),'destination':str(destination),'original_files_preserved':len(before),'history':'history/pre-v2','current_claim':'working; old review and approval retained as history, not adopted','next':'Reconcile relationships, produce or substantiate current outputs, capture their actual inputs, inspect and review.'}
    save('MIGRATION.json',receipt);marker.unlink();return receipt


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source');p.add_argument('destination');a=p.parse_args()
    try:print(json.dumps(migrate(a.source,a.destination),indent=2));return 0
    except (OSError,ValueError,KeyError,TypeError,AssertionError)as exc:print('Migration not completed: '+str(exc));return 2

if __name__=='__main__':raise SystemExit(main())