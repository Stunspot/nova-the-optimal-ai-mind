import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from upgrade_osint_security import guarded_entrypoint
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
if __name__=='__main__':unittest.main()
