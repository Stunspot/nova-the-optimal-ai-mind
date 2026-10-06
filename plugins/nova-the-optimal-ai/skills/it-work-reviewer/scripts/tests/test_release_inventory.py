import hashlib, importlib.util, pathlib, tempfile, unittest
SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "validate_release.py"
spec = importlib.util.spec_from_file_location("release_inventory", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class ReleaseInventoryTests(unittest.TestCase):
    def test_interpreter_cache_is_not_product_cargo(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            (root / "useful.txt").write_bytes(b"canonical")
            cache = root / "__pycache__"
            cache.mkdir()
            (cache / "module.cpython-314.pyc").write_bytes(b"cache")
            (root / "loose.pyc").write_bytes(b"cache")
            (root / "loose.pyo").write_bytes(b"cache")
            (root / "release-manifest.json").write_text("{}")
            self.assertEqual(module.inventory(root), {"useful.txt": {"sha256": hashlib.sha256(b"canonical").hexdigest(), "bytes": 9}})

if __name__ == "__main__":
    unittest.main()
