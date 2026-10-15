#!/bin/sh
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
if [ -f "$ROOT/scripts/project_bridge.py" ]; then
    exec sh "$ROOT/Open Project Bridge.command" "$@"
fi
exec sh "$ROOT/plugins/dennis-stratton-project-management/skills/dennis-stratton-project-management/Open Project Bridge.command" "$@"
