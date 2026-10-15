#!/bin/sh
TASK_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec python3 "$TASK_DIR/../nova-operations/scripts/nova_estate.py" run project-bridge -- "$@"
