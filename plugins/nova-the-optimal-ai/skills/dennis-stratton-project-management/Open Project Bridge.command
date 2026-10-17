#!/bin/sh
cd "$(dirname "$0")" || exit 1
python3 workspace/launch.py "$@"
result=$?
if [ "$result" -ne 0 ]; then printf '\nInstall Python 3.10+ or read the reported Project Bridge startup error.\n'; read -r reply; fi
exit "$result"
