from __future__ import annotations
import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock
import test_state_and_operations as fixtures

REPO=Path(__file__).resolve().parents[1]
SOURCE=REPO/'plugins/nova-the-optimal-ai/skills/nova-operations/scripts'

def load_ops():
    spec=importlib.util.spec_from_file_location('nova_operations_audit_runtime',SOURCE/'nova_estate.py')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class OperationsEstateAuditTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.NovaOperationsFreeTests(); self.fixture.setUp(); self.addCleanup(self.fixture.tearDown)
        self.base=self.fixture.base; self.root=self.base/'estate'; self.values=self.fixture.configure(self.root); self.ops=load_ops()

    def test_commonplace_override_forms_rejected_before_real_owner(self):
        for flag in ('--estate-root','--estate-r','--e'):
            for form in ([flag,str(self.base/'other')],[flag+'='+str(self.base/'other')]):
                with self.subTest(form=form):
                    result=self.fixture.run_cli('run','--root',str(self.root),'commonplace','--',*form,'status','--json')
                    self.assertEqual(result.returncode,2,result.stdout)
                    self.assertIn('must not be overridden',result.stderr)
                    self.assertFalse((self.base/'other').exists())

    def test_real_commonplace_status_preserves_selected_root(self):
        result=self.fixture.run_cli('run','--root',str(self.root),'commonplace','--','status','--json')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(Path(json.loads(result.stdout)['root']),Path(self.values['NOVA_COMMONPLACE_HOME']))

    def test_knowledge_desk_abbreviated_owner_override_does_not_dispatch(self):
        for arg in ('--nova-operations=x','--nova-o=x','--n=x','--estate-r=x'):
            with self.subTest(arg=arg),mock.patch.object(self.ops,'load_configured_root',return_value=(self.root,self.values,{})),mock.patch.object(self.ops,'run_service_process') as run:
                with self.assertRaises(self.ops.NovaEstateError):
                    self.ops.command_run(argparse.Namespace(root=str(self.root),service='knowledge-desk',service_args=[arg]))
                run.assert_not_called()

    def test_malformed_additive_values_are_corruption_and_preserved(self):
        p=self.root/'estate/path-selectors.json'; baseline=json.loads(p.read_text(encoding='utf-8'))
        for value in (False,42,[],{},''):
            with self.subTest(value=value):
                changed=json.loads(json.dumps(baseline)); changed['active_values']['NOVA_COMMONPLACE_HOME']=value
                p.write_text(json.dumps(changed),encoding='utf-8'); before=p.read_bytes()
                result=self.fixture.run_cli('upgrade','--root',str(self.root))
                self.assertEqual(result.returncode,2,result.stdout)
                self.assertNotIn('Traceback',result.stderr); self.assertEqual(p.read_bytes(),before)

    def test_relative_selector_is_invalid_independent_of_cwd(self):
        old=Path.cwd()
        try:
            os.chdir(self.base)
            with self.assertRaises(self.ops.NovaEstateError): self.ops._normalized_selector('NOVA_DATA_ROOT','estate',self.root)
        finally: os.chdir(old)

    def test_absent_and_null_known_additions_remain_legacy_migrations(self):
        registry={'format':self.ops.REGISTRY_FORMAT,'active_values':dict(self.values)}
        registry['active_values'].pop('NOVA_COMMONPLACE_HOME'); registry['active_values']['NOVA_CONCORDANCE_HOME']=None
        self.assertEqual(self.ops.registry_upgrade_analysis(registry,self.root)[2],['NOVA_COMMONPLACE_HOME','NOVA_CONCORDANCE_HOME'])

    def test_probe_missing_or_directory_runtime_is_structured(self):
        for runtime in (self.base/'missing.py',self.base):
            result=subprocess.run([sys.executable,'-B','-X','utf8',str(SOURCE/'probe_continuity_mutation.py'),'--runtime',str(runtime),'--workspace',str(self.root)],capture_output=True,text=True,encoding='utf-8',env=self.fixture.environment())
            self.assertEqual(result.returncode,2); self.assertNotIn('Traceback',result.stderr)
            value=json.loads(result.stdout); self.assertFalse(value['supported']); self.assertFalse(value['source_mutated'])

    def test_shell_helper_round_trips_literal_path_without_expansion(self):
        candidates=[Path(r'C:\Program Files\Git\bin\bash.exe'),Path(r'C:\Program Files\Git\usr\bin\bash.exe')]
        bash=next((p for p in candidates if p.is_file()),None)
        if bash is None: self.skipTest('No native Git Bash available for POSIX helper execution')
        value='literal path $HOME $(printf EXPANDED) `printf CHANGED` \\ " quote café\nline'
        script=self.base/'literal.sh'
        script.write_text(self.ops._env_text({'NOVA_DATA_ROOT':value})+'printf "%s" "$NOVA_DATA_ROOT"\n',encoding='utf-8')
        result=subprocess.run([str(bash),'--noprofile','--norc',str(script)],capture_output=True,text=True,encoding='utf-8',env=self.fixture.environment())
        self.assertEqual(result.returncode,0,result.stderr); self.assertEqual(result.stdout,value)

    def test_native_package_junction_is_not_a_bundled_service(self):
        package=self.base/'junction-skills'; package.mkdir(); external=self.base/'external'; (external/'scripts').mkdir(parents=True); (external/'scripts/corkboard.py').write_text('raise RuntimeError("must not execute")',encoding='utf-8'); link=package/'corkboard'
        if os.name=='nt':
            script=self.base/'junction.ps1';script.write_text('param([string]$LinkPath,[string]$TargetPath)\nNew-Item -ItemType Junction -Path $LinkPath -Target $TargetPath -ErrorAction Stop | Out-Null\n',encoding='utf-8')
            made=subprocess.run(['powershell','-NoProfile','-File',str(script),str(link),str(external)],capture_output=True,text=True)
            self.assertEqual(made.returncode,0,made.stderr)
            self.addCleanup(lambda:link.rmdir() if os.path.lexists(link) else None)
        else:
            link.symlink_to(external,target_is_directory=True);self.addCleanup(link.unlink)
        with mock.patch.object(self.ops,'skill_root',return_value=package):
            with self.assertRaises(self.ops.NovaEstateError): self.ops.service_script('corkboard')
            state=self.ops.launcher_payload(); self.assertFalse(state['services']['corkboard']['present']); self.assertFalse(state['ready'])
        self.assertTrue((external/'scripts/corkboard.py').is_file())

    def test_missing_continuity_package_is_not_registry_corruption(self):
        (self.fixture.skills/'cognitive-continuity/scripts/continuity_store_v2.py').unlink()
        result=self.fixture.run_cli('status','--root',str(self.root)); self.assertEqual(result.returncode,0,result.stderr)
        state=json.loads(result.stdout);self.assertTrue(state['configured']); self.assertNotEqual(state['state'],'registry_invalid')
        self.assertEqual(state['continuity_read_support']['code'],'package_unavailable');self.assertEqual(state['continuity_operating_mode'],'unavailable')

    def test_missing_mutation_probe_preserves_actual_read_support(self):
        (self.fixture.skills/'nova-operations/scripts/probe_continuity_mutation.py').unlink()
        result=self.fixture.run_cli('status','--root',str(self.root));self.assertEqual(result.returncode,0,result.stderr)
        state=json.loads(result.stdout);self.assertTrue(state['continuity_read_support']['supported']);self.assertFalse(state['continuity_mutation_support']['supported']);self.assertEqual(state['continuity_operating_mode'],'read_only')

    def test_nonzero_probe_cannot_qualify_mutation(self):
        with mock.patch.object(self.ops,'run_json',return_value=(7,{'format':'nova-continuity-mutation-support/v1','probe_completed':True,'source_mutated':False,'supported':True,'qualified':True,'status':'qualified'},'failed')):
            probe=self.ops.probe_mutation_support({'mutation_probe':self.base/'p.py','runtime':self.base/'r.py'},self.values)
        self.assertFalse(probe['supported']); self.assertEqual(probe['reported_result']['status'],'qualified')
        self.assertEqual(self.ops.continuity_operating_mode({'read':{'supported':True},'mutation':probe}),'read_only')

    def test_malformed_success_probe_cannot_qualify_mutation(self):
        reports=(
            {'supported':True,'qualified':True,'status':'qualified'},
            {'format':'nova-continuity-mutation-support/v1','probe_completed':True,'source_mutated':False,'supported':'yes','qualified':True,'status':'qualified'},
            {'format':'nova-continuity-mutation-support/v1','probe_completed':True,'source_mutated':False,'supported':True,'qualified':True,'status':'unsupported'},
        )
        for report in reports:
            with self.subTest(report=report),mock.patch.object(self.ops,'run_json',return_value=(0,report,'')):
                probe=self.ops.probe_mutation_support({'mutation_probe':self.base/'p.py','runtime':self.base/'r.py'},self.values)
            self.assertFalse(probe['supported']);self.assertEqual(probe['code'],'probe_output_invalid')
            self.assertEqual(self.ops.continuity_operating_mode({'read':{'supported':True},'mutation':probe}),'read_only')

    def test_explicit_environment_retry_applies_without_reinitializing(self):
        args=argparse.Namespace(root=str(self.root),apply_user_environment=True,user='tester')
        with mock.patch.object(self.ops,'require_windows_environment_flag_supported'),mock.patch.object(self.ops,'assert_locator_conflict_free',return_value=None),mock.patch.object(self.ops,'status_payload',return_value={'configured':True,'selectors':self.values}),mock.patch.object(self.ops,'apply_windows_user_environment') as apply,mock.patch.object(self.ops,'run_json') as child,mock.patch.object(self.ops,'emit') as emit:
            self.assertEqual(self.ops.command_init(args),0);apply.assert_called_once_with(self.values);child.assert_not_called()
            self.assertTrue(emit.call_args.args[0]['environment_applied']);self.assertFalse(emit.call_args.args[0]['source_mutated'])

    def test_environment_failure_after_publication_preserves_new_estate_and_retry(self):
        root=self.base/'new-estate'
        args=argparse.Namespace(root=str(root),apply_user_environment=True,user='tester')
        with mock.patch.dict(os.environ,self.fixture.environment(),clear=True),mock.patch.object(self.ops,'require_windows_environment_flag_supported'),mock.patch.object(self.ops,'skill_root',return_value=self.fixture.skills),mock.patch.object(self.ops,'user_environment_values',return_value={key:None for key in self.ops.SELECTOR_KEYS}),mock.patch.object(self.ops,'apply_windows_user_environment',side_effect=OSError('injected optional-copy failure')),mock.patch.object(self.ops,'emit') as emit:
            self.assertEqual(self.ops.command_init(args),2)
            receipt=emit.call_args.args[0];self.assertEqual(receipt['state'],'initialized');self.assertTrue(receipt['source_mutated']);self.assertEqual(receipt['environment_state'],'failed_may_be_partial')
        self.assertTrue((root/'memory/commonplace/CURRENT.json').is_file())
        before={str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}
        with mock.patch.dict(os.environ,self.fixture.environment(),clear=True),mock.patch.object(self.ops,'require_windows_environment_flag_supported'),mock.patch.object(self.ops,'skill_root',return_value=self.fixture.skills),mock.patch.object(self.ops,'apply_windows_user_environment') as apply,mock.patch.object(self.ops,'emit') as emit:
            self.assertEqual(self.ops.command_init(args),0);apply.assert_called_once();self.assertEqual(emit.call_args.args[0]['state'],'already_configured')
        self.assertEqual(before,{str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()})
    def test_optional_environment_failure_preserves_existing_estate(self):
        before={str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        args=argparse.Namespace(root=str(self.root),apply_user_environment=True,user='tester')
        with mock.patch.object(self.ops,'require_windows_environment_flag_supported'),mock.patch.object(self.ops,'assert_locator_conflict_free',return_value=None),mock.patch.object(self.ops,'status_payload',return_value={'configured':True,'selectors':self.values}),mock.patch.object(self.ops,'apply_windows_user_environment',side_effect=OSError('injected registry-copy failure')),mock.patch.object(self.ops,'emit') as emit:
            self.assertEqual(self.ops.command_init(args),2);self.assertEqual(emit.call_args.args[0]['environment_state'],'failed_may_be_partial');self.assertFalse(emit.call_args.args[0]['environment_applied'])
        after={str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()};self.assertEqual(before,after)

if __name__=='__main__': unittest.main()

