#!/usr/bin/env bash
# Open the stoker: the one conversation the operator talks to.
#
# Everything the operator has to remember is in this file instead of in their
# head — the right folder, and the role marker that loads roles/stoker.md.
# bin/ holds only entry points; there is no logic here on purpose.
set -euo pipefail

cd "$(dirname "$0")/.."
exec env HEATER_ROLE=stoker claude "$@"
