#!/usr/bin/env bash
# Open the stoker: the one conversation the operator talks to.
#
# Everything the operator has to remember is in this file instead of in their
# head — the right folder and one command.
#
# This does not exit when a session does. It supervises: when a session has
# written, pushed and verified its handover, this ends it and opens a fresh one
# on its own, so the handoff asks the operator for nothing. Stop the stoker by
# ending the session with /exit or Ctrl-C.
#
# Remote Control is what resolves the cloud-or-terminal question. The session
# runs here, on this machine, with this machine's filesystem and this machine's
# fleet install; the Claude app is a window onto it. So the operator talks to
# the stoker from the app without the stoker losing the machine it governs.
#
# bin/ holds only entry points; the supervisor is tools/stoker.py on purpose.
set -euo pipefail

cd "$(dirname "$0")/.."
exec python3 tools/stoker.py "$@"
