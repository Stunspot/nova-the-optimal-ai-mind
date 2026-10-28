import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from upgrade_osint_security import guarded_entrypoint, accepted_adapter, PRIOR_ADAPTERS
import hashlib, tempfile
import upgrade_osint_security as upgrade
from unittest.mock import patch
class UpgradeTests(unittest.TestCase):
    def test_only_maigret_routes_change_and_repeat_is_stable(self):
        text="""def main():
    if args.command=='help':
        if args.tool=='theharvester': command=['keep']
        else: command=[exe(args.tool),'--help']
    command=[exe('maigret'),args.target,'--db','keep']
"""
        updated=guarded_entrypoint(text)
        self.assertIn("if args.tool=='theharvester': command=['keep']",updated)
        self.assertIn("str(ROOT/'drivers/maigret_safe.py')",updated)
        self.assertEqual(guarded_entrypoint(updated),updated)
    def test_unrecognized_adapter_is_preserved_by_refusal(self):
        with self.assertRaises(ValueError):guarded_entrypoint('custom_entrypoint()')
    def test_only_exact_prior_or_current_adapter_bytes_can_upgrade(self):
        old=b'accepted fixture';new=b'new guard'
        with patch.dict(PRIOR_ADAPTERS,{'safe_http.py':{hashlib.sha256(old).hexdigest()}},clear=True):
            self.assertTrue(accepted_adapter('safe_http.py',old,new))
            self.assertTrue(accepted_adapter('safe_http.py',new,new))
            self.assertTrue(accepted_adapter('safe_http.py',None,new))
            self.assertFalse(accepted_adapter('safe_http.py',b'locally customized',new))
            self.assertFalse(accepted_adapter('other.py',old,new))
    def test_complete_old_guard_migration_preserves_backups_and_other_data(self):
        with tempfile.TemporaryDirectory() as temp:
            home=Path(temp)/'workbench';home.mkdir()
            entry="def run():\n    command=[exe('maigret'),args.target,'--db','keep']\n    if args.command=='help':\n        else: command=[exe(args.tool),'--help']\n"
            # Use the real adapter's complete, compilable control flow.
            entry=(upgrade.HERE/'osint-runtime/osint.py').read_text(encoding='utf-8')
            (home/'osint.py').write_text(entry,encoding='utf-8')
            py=home/'envs/maigret'/('Scripts/python.exe' if upgrade.os.name=='nt' else 'bin/python');py.parent.mkdir(parents=True);py.write_bytes(b'fixture-runtime')
            before=b'accepted prior transport fixture'
            (home/'safe_http.py').write_bytes(before)
            (home/'runs').mkdir();(home/'runs/user-report.txt').write_bytes(b'keep me')
            with patch.dict(PRIOR_ADAPTERS,{'safe_http.py':{hashlib.sha256(before).hexdigest()}},clear=True),patch.object(upgrade.subprocess,'run') as run:
                result=upgrade.upgrade(home,'fixture-uv')
            self.assertTrue(result['tls_verification'])
            self.assertEqual((home/'safe_http.py').read_bytes(),(upgrade.HERE/'osint-runtime/safe_http.py').read_bytes())
            backup=Path(result['entrypoint_preimage']).parent
            self.assertEqual((backup/'safe_http.py').read_bytes(),before)
            self.assertEqual((home/'runs/user-report.txt').read_bytes(),b'keep me')
            install=run.call_args_list[0].args[0]
            self.assertIn('--require-hashes',install)
            self.assertIn('--no-deps',install)
            self.assertFalse(result['provider_queries'])

    def test_unknown_old_guard_stops_before_environment_or_files_change(self):
        with tempfile.TemporaryDirectory() as temp:
            home=Path(temp);(home/'osint.py').write_bytes((upgrade.HERE/'osint-runtime/osint.py').read_bytes())
            py=home/'envs/maigret'/('Scripts/python.exe' if upgrade.os.name=='nt' else 'bin/python');py.parent.mkdir(parents=True);py.write_bytes(b'fixture-runtime')
            (home/'safe_http.py').write_bytes(b'custom code')
            with patch.object(upgrade.subprocess,'run') as run,self.assertRaisesRegex(ValueError,'accepted releases'):
                upgrade.upgrade(home,'fixture-uv')
            run.assert_not_called()
            self.assertEqual((home/'safe_http.py').read_bytes(),b'custom code')
            self.assertFalse((home/'security-backups').exists())
if __name__=='__main__':unittest.main()
