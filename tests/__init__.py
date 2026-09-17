"""Test package init, which exists for one reason: the suite must never push.

Taking bearings sweeps every checkout this machine knows about and pushes any
branch that lives here only. That is wanted in a session and never wanted in a
test run, which would otherwise push the real branches of whatever machine the
suite happened to run on. Setting the switch here covers every test file,
including ones written later that never think about it.
"""

import os

os.environ["HEATER_AUTOPUSH"] = "0"
