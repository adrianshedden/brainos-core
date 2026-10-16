#!/usr/bin/env bash
# Runs every BrainOS core test (B1-B5 and the no-network guard). Exit 0 = all pass.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$here"
export PYTHONDONTWRITEBYTECODE=1
python3 -m unittest discover -s "$here" -p 'test_*.py' -v
echo "All BrainOS core tests passed."
