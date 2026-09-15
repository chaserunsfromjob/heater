#!/usr/bin/env bash
# Open the stoker: the one conversation the operator talks to.
#
# Everything the operator has to remember is in this file instead of in their
# head — the right folder, the role marker, and Remote Control.
#
# Remote Control is what resolves the cloud-or-terminal question. The session
# runs here, on this machine, with this machine's filesystem and this machine's
# fleet install; the Claude app is a window onto it. So the operator talks to
# the stoker from the app without the stoker losing the machine it governs.
#
# It degrades rather than fails: without Remote Control enabled on the account,
# this is still an ordinary local stoker session.
#
# bin/ holds only entry points; there is no logic here on purpose.
set -euo pipefail

cd "$(dirname "$0")/.."
exec env HEATER_ROLE=stoker claude --remote-control "${HEATER_SESSION_NAME:-heater stoker}" "$@"
