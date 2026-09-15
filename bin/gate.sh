#!/usr/bin/env bash
# The project's own gate. Exit 0 is one of the three things a change needs to
# land; the other two are a fresh independent review pass and a green suite.
set -euo pipefail

cd "$(dirname "$0")/.."

fail=0
step() {
    printf '\n== %s\n' "$1"
    shift
    if "$@"; then
        return 0
    fi
    fail=1
    return 0
}

step "rule style" python3 tools/style_lint.py
step "unit tests" python3 -m unittest discover -s tests -q
# Deploy drift is a property of a machine, not of a change, so it is not gated
# here. The SessionStart hook reports it, and `bin/deploy.py --check` runs it.

printf '\n'
if [ "$fail" -ne 0 ]; then
    echo "gate: FAILED"
    exit 1
fi
echo "gate: passed"
