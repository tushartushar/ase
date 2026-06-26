#!/usr/bin/env python3
#
# After a Write or Edit, run the relevant test file.
# - If the edited file is a test file under app/tests/, run it.
# - If the edited file is a source file under app/, run the
#   matching test file (app/x.py -> app/tests/test_x.py) if it exists.
# - Otherwise, do nothing.

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

payload = json.load(sys.stdin)
edited = payload.get("tool_input", {}).get("file_path", "")
if not edited:
    sys.exit(0)

edited_path = Path(edited)
test_target = None

if edited_path.match("app/tests/test_*.py"):
    test_target = edited_path
elif edited_path.match("app/*.py"):
    candidate = REPO_ROOT / "app" / "tests" / f"test_{edited_path.name}"
    if candidate.exists():
        test_target = candidate

if test_target is None:
    sys.exit(0)

result = subprocess.run(
    ["pytest", "-x", "--tb=short", "-q", str(test_target)],
    capture_output=True,
    text=True,
    cwd=REPO_ROOT,
)

# Surface output to the agent regardless of pass/fail.
sys.stdout.write(result.stdout)
sys.stderr.write(result.stderr)

# Non-zero only on test failure — the hook itself didn't fail,
# the tests did, and we want Claude to see that.
if result.returncode != 0:
    sys.exit(2)
sys.exit(result.returncode)
