#!/usr/bin/env python3
# .claude/hooks/block_direct_status_writes.py
#
# Rejects writes that assign to .status directly, anywhere except
# the state machine module itself. CLAUDE.md says transitions go
# through order_router.update_status(); this makes that rule hold.

import json, re, sys

ALLOWED_SUFFIXES = {"app/order_router.py"}
PATTERN = re.compile(r"\.status\s*=\s*\S|\"status\"\s*:\s*OrderStatus\.")

payload = json.load(sys.stdin)
tool_input = payload.get("tool_input", {})
path = tool_input.get("file_path", "")
content = tool_input.get("content", "") or tool_input.get("new_string", "")

if any(path.endswith(suffix) for suffix in ALLOWED_SUFFIXES):
    sys.exit(0)

if PATTERN.search(content):
    print(
        "Blocked: direct assignment to .status detected in "
        f"{path}. State transitions must go through "
        "order_router.update_status(order, new_status). "
        "See CLAUDE.md > State machine.",
        file=sys.stderr,
    )
    sys.exit(2)  # non-zero, with reason

sys.exit(0)