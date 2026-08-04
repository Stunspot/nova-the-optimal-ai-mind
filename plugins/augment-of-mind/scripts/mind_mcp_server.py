"""Launch the plugin-local MIND MCP server."""

from __future__ import annotations

import sys
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

from mind_core.mcp_server import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
