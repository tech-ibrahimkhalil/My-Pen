#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  echo "Install the environment and requirements using README.md first."
  exit 1
fi
exec .venv/bin/python scripts/test_platform.py --gui-smoke "$@"
