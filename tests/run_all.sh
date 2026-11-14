#!/usr/bin/env bash
# Runs every BrainOS core test (B1-B5 and the no-network guard). Exit 0 = all pass.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$here"
export PYTHONDONTWRITEBYTECODE=1
# python3 on a Mac or Linux; on Windows (Git Bash) it is often python or py.
py=python3
for candidate in python3 python py; do
  if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; sys.exit(sys.version_info < (3, 8))' 2>/dev/null; then
    py=$candidate
    break
  fi
done
"$py" -m unittest discover -s "$here" -p 'test_*.py' -v
echo "All BrainOS core tests passed."
