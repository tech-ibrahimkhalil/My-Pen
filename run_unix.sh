#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  echo "First create the environment and install requirements. See README.md."
  exit 1
fi
exec .venv/bin/python main.py "$@"
