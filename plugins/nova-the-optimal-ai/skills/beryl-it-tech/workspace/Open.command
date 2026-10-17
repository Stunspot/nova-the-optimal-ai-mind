#!/bin/sh
cd "$(dirname "$0")" || exit 1
command -v python3 >/dev/null 2>&1 || { echo "Install Python 3.10 or newer, then reopen Beryl Repair Companion."; exit 1; }
exec python3 launch.py "$@"
