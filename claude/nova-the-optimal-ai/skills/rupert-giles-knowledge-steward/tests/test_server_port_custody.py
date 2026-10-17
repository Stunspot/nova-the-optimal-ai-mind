import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import giles

class PortCustodyTests(unittest.TestCase):
    def test_another_listener_cannot_share_a_giles_port(self):
        with tempfile.TemporaryDirectory() as directory:
            first = giles.make_server(Path(directory) / "catalog.json", 0)
            try:
                with self.assertRaises(OSError):
                    second = giles.make_server(Path(directory) / "catalog.json", first.server_port)
                    second.server_close()
            finally:
                first.server_close()

if __name__ == "__main__":
    unittest.main()
