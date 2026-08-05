"""Keep repository tooling side-effect free during verification."""

import sys

sys.dont_write_bytecode = True
