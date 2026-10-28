"""Execute the shipped Dennis/Commonplace join, including correction and guard behavior.

NOVA_STATE_TEST_HOME may select a retained fixture-output directory. These tests
never read customer stores, alter global selectors, or approve computed adapter hashes.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import uuid
from datetime import datetime, timezone

ROOT = Path(os.environ.get("NOVA_STATE_TEST_ROOT") or Path(__file__).resolve().parents[1]).resolve()
SKILLS = [p for p in [
    ROOT / 'codex/plugins/nova-emergent/skills',
    ROOT / 'claude/nova-emergent/skills',
    ROOT / 'claude/folders',
    ROOT / 'plugins/nova-the-optimal-ai/skills',
    ROOT / 'claude/nova-the-optimal-ai/skills',
] if (p / 'nova-operations/scripts/nova_estate.py').is_file()]
if os.environ.get("NOVA_STATE_TEST_SKILL_ROOTS"):
    SKILLS = [Path(p).resolve() for p in json.loads(os.environ["NOVA_STATE_TEST_SKILL_ROOTS"])]

class ShippedStateCompositionTests(unittest.TestCase):
    def test_created_and_corrected_project_reaches_consumer_with_guard_intact(self):
        self.assertTrue(SKILLS, 'No native edition skill tree found')
        output = Path(os.environ.get('NOVA_STATE_TEST_HOME') or tempfile.mkdtemp(prefix='nova-state-composition-')).resolve()
        output.mkdir(parents=True, exist_ok=True)
        for skills in SKILLS:
            with self.subTest(skills=str(skills)):
                case = output / ('composition-' + uuid.uuid4().hex[:12])
                case.mkdir()
                estate = case / 'estate'
                ops = skills / 'nova-operations/scripts/nova_estate.py'
                env = os.environ.copy()
                for key in list(env):
                    if key.startswith('NOVA_') or key in {'DUNBAR_STORE', 'CORKBOARD_HOME', 'DENNIS_PROJECT_HOME', 'MIND_CORE_DATABASE', 'MIND_HOOK_RECEIPT_DIRECTORY', 'PYTHONPATH'}:
                        env.pop(key, None)
                # Keep current-estate discovery private on all supported platforms.
                env.update(LOCALAPPDATA=str(case / 'platform'), XDG_CONFIG_HOME=str(case / 'platform'), XDG_DATA_HOME=str(case / 'platform'), HOME=str(case / 'private-user'), USERPROFILE=str(case / 'private-user'), PYTHONDONTWRITEBYTECODE='1')
                log = []
                def run(name, args, payload=None):
                    result = subprocess.run([sys.executable, '-B', '-X', 'utf8', *map(str, args)], input=json.dumps(payload) if payload is not None else None, capture_output=True, text=True, encoding='utf-8', env=env, timeout=90)
                    try:
                        value = json.loads(result.stdout)
                    except json.JSONDecodeError:
                        value = result.stdout
                    log.append({'name':name,'args':list(map(str,args)),'input':payload,'exit_code':result.returncode,'stdout':value,'stderr':result.stderr})
                    (case/'responses.json').write_text(json.dumps(log,indent=2)+'\n',encoding='utf-8')
                    self.assertEqual(result.returncode, 0, f'{name}: {value}\n{result.stderr}')
                    return value
                def service(name, args, payload=None):
                    return run(name, [ops,'run','--root',estate,*args], payload)
                request = {'query':'Harbor Lantern','owners':['Dennis'],'allowed_sensitivities':['public','personal'],'timeout_ms':15000}
                def recall(name):
                    value = service(name, ['commonplace','--','federated-search','--stdin-json','--json'], request)
                    row = next(x for x in value['owners'] if x['owner']=='Dennis')
                    self.assertEqual(row['status'],'current',row)
                    self.assertEqual(len(row['payload']),1,row)
                    return row['payload'][0]
                run('init',[ops,'init','--root',estate,'--user','fixture-user'])
                created = service('ensure',['project-management','--','ensure','--project-id','harbor-lantern','--project-name','Harbor Lantern','--owner','Fictional owner','--outcome','Prepare a small lighthouse exhibition','--source-locator','fixture:authorized-project'])
                native_path = Path(created['record']['path'])
                self.assertTrue(native_path.resolve().is_relative_to(estate))
                before = recall('recall-created')
                self.assertEqual(before['project_id'],'harbor-lantern')
                self.assertEqual(before['status'],'proposed')
                self.assertEqual(before['source_locators'],['fixture:authorized-project'])
                native = json.loads(native_path.read_text(encoding='utf-8'))
                self.assertEqual(before['current']['next_action'],native['current']['next_action'])
                # A caller authors a correction in the owned project record, then
                # uses the native validator. Recall must reread that authority.
                corrected = 'Ask the fictional curator to measure the lantern doorway.'
                native['current']['next_action'] = corrected
                stamp = datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z')
                native['current']['as_of'] = stamp
                native['project']['updated_at'] = stamp
                staging = native_path.with_suffix('.fixture-next')
                staging.write_text(json.dumps(native,indent=2)+'\n',encoding='utf-8')
                service('validate-correction',['project-management','--','validate',str(staging),'--json'])
                staging.replace(native_path)
                after = recall('recall-corrected')
                self.assertEqual(after['current']['next_action'],corrected)
                self.assertNotEqual(before['fingerprint'],after['fingerprint'])
                self.assertEqual(after['status'],'proposed')
                self.assertEqual(after['source_locators'],before['source_locators'])
                # Alter a copied owner after composition. Retain the shipped pin:
                # approval must not follow arbitrary local source bytes.
                altered = case / 'altered-skills'
                shutil.copytree(skills/'commonplace/scripts',altered/'commonplace/scripts',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
                for relative in ('dunbar/scripts/dunbar.py', 'corkboard/scripts/corkboard.py', 'cognitive-continuity/scripts/worldline.py'):
                    target = altered/relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(skills/relative,target)
                copied_owner = altered/'dennis-stratton-project-management/scripts/project_control.py'
                copied_owner.parent.mkdir(parents=True)
                shutil.copy2(skills/'dennis-stratton-project-management/scripts/project_control.py',copied_owner)
                marker = case/'unapproved-owner-executed.txt'
                with copied_owner.open('a',encoding='utf-8') as stream:
                    stream.write('\nfrom pathlib import Path as _FixturePath\n_FixturePath('+repr(str(marker))+').write_text("unapproved adapter executed", encoding="utf-8")\n')
                code = 'import json,sys;sys.path.insert(0,sys.argv[1]);from nova_commonplace.federation import federated_search;print(json.dumps(federated_search("Harbor Lantern",estate_root=sys.argv[2],skills_root=sys.argv[3],owners=["Dennis"],timeout_ms=15000)))'
                rejected = run('reject-unapproved-owner',['-c',code,altered/'commonplace/scripts',estate,altered])
                row = next(x for x in rejected['owners'] if x['owner']=='Dennis')
                self.assertEqual(row['status'],'integrity_error',row)
                self.assertEqual(row['code'],'adapter_integrity_error',row)
                self.assertNotIn('payload',row)
                self.assertFalse(marker.exists(),'Unapproved owner code executed')
                print('Verified created/corrected recall and rejected unapproved owner:',skills,flush=True)

if __name__=='__main__':
    unittest.main()

