#!/bin/sh
TASK_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec python3 "$TASK_DIR/scripts/giles.py" "$@" serve
