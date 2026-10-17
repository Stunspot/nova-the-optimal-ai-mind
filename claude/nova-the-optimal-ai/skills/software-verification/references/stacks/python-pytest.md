# Python with pytest or unittest

Detect `pyproject.toml`, `pytest.ini`, `tox.ini`, `setup.cfg`, dependency manager, import root, test paths, fixtures, markers, plugins, async mode, and repository commands.

Common commands, subject to the repository:

```text
python -m pytest path/to/test_file.py -q
python -m pytest -k expression -q
python -m unittest discover
python -m compileall <changed paths>
```

Use the project interpreter or environment. Do not install pytest or plugins without approval. Keep fixtures narrow, restore environment and global state, avoid timezone and locale dependence, and parameterize meaningful equivalence classes rather than implementation branches.
