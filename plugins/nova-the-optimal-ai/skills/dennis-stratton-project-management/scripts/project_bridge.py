"""Project Bridge: visual access to the native Dennis project-record estate."""
from pathlib import Path
from datetime import datetime, timezone
import copy, json, secrets
import project_control as control
from workspace_host import atomic_json, run_workspace

ROOT = Path(__file__).resolve().parent.parent

def state(home):
    rows, diagnostics = control.scan_store(home)
    result = []
    for row in rows:
        errors, warnings = control.validate_record(row['record'])
        result.append({**control.public_store_row(row), 'record': row['record'], 'errors': errors, 'warnings': warnings})
    return {'home': str(home), 'projects': result, 'diagnostics': diagnostics, 'boundary': control.BOUNDARY}

def mutate(home, value):
    action = value.get('action')
    if action == 'create':
        fields = {k: str(value.get(k, '')).strip() for k in ('name', 'owner', 'outcome', 'source')}
        if any(not v for v in fields.values()): raise ValueError('Name, owner, observable outcome and authority source are required.')
        result = control.ensure_project(home, fields['name'], fields['owner'], fields['outcome'], source_locator=fields['source'])
        return {'created': result['created'], 'id': result['record']['project_id']}
    if action == 'import':
        record = value['record']
        errors, _ = control.validate_record(record)
        if errors: raise ValueError('Import rejected: ' + json.dumps(errors[:8]))
        imports = home / 'imports'; imports.mkdir(exist_ok=True)
        source = imports / ('import-' + secrets.token_hex(6) + '.json')
        atomic_json(source, record)
        result = control.adopt_project(home, source)
        return {'created': result['created'], 'id': result['record']['project_id'], 'original': str(source)}
    if action != 'save': raise ValueError('Unknown action')
    rows, _ = control.scan_store(home)
    matches = [row for row in rows if row['project_id'] == value['id']]
    if len(matches) != 1: raise ValueError('Project missing or ambiguous. Refresh the portfolio.')
    row = matches[0]
    if row['fingerprint'] != value['expected']: raise ValueError('This project changed elsewhere. Export your unsaved draft, then refresh and reconcile before saving.')
    record = copy.deepcopy(value['record'])
    if record['project']['id'] != row['project_id']: raise ValueError('Project identity cannot change in the editor.')
    record['project']['updated_at'] = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')
    errors, _ = control.validate_record(record)
    if errors: raise ValueError('Record not saved: ' + json.dumps(errors[:8]))
    backup = row['path'].parent / 'records' / 'bridge-history' / (secrets.token_hex(8) + '.json')
    atomic_json(backup, row['record'])
    atomic_json(row['path'], record)
    return {'saved': True, 'id': row['project_id'], 'fingerprint': control.fingerprint(record), 'previous': str(backup)}

if __name__ == '__main__':
    run_workspace('Dennis Project Bridge', '0.5.0', ROOT, lambda explicit: control.resolve_store(Path(explicit) if explicit else None)[0], state, mutate, 8881)
