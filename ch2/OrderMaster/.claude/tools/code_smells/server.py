#!/usr/bin/env python3
"""MCP server that wraps DPy for Python source code.

This exposes an existing console application to Claude Code as an MCP tool,
so the agent can call it with structured arguments instead of you shelling out
to it by hand.

"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# --- Configuration -----------------------------------------------------------
# Absolute path to your code-smell detector binary. Override at registration
# time with the TOOL_BINARY environment variable, or hard-code it here.
TOOL_BINARY = os.environ.get("TOOL_BINARY", os.path.abspath("./DPy"))

# How long (seconds) to let the binary run before giving up.
TIMEOUT_SECONDS = int(os.environ.get("TIMEOUT_SECONDS", "120"))

mcp = FastMCP("code-smell-detector")


def _resolve_target(path: str, is_create: bool = False) -> Path:
    """Resolve and validate the path to analyze."""
    target = Path(path).expanduser().resolve()

    if not target.exists():
        if is_create:
            target.mkdir(parents=True, exist_ok=True)
        else:
            raise FileNotFoundError(f"no such file or directory: {target}")
    return target


SMELL_CATEGORIES = ("arch", "implementation", "design", "ml")


def _summarize_output(output_dir: Path) -> dict[str, int]:
    """Read all JSON files in output_dir and return per-category smell counts.

    Each JSON file may contain smell entries with a category field whose value
    is one of: 'arch', 'implementation', 'design', 'ml'. Entries with an
    unrecognised or missing category are counted under 'other'.
    """
    totals: dict[str, int] = {cat: 0 for cat in SMELL_CATEGORIES}
    totals["other"] = 0

    for jf in sorted(output_dir.glob("**/*.json")):
        if not any(cat in jf.name for cat in SMELL_CATEGORIES):
            continue  # skip any JSON files that are part of the tool's own code
        try:
            data = json.loads(jf.read_text())
        except (json.JSONDecodeError, OSError):
            continue

        if not isinstance(data, list):
            continue
        smells = data

        file_category = next(
            (cat for cat in SMELL_CATEGORIES if cat in jf.name), ""
        )
        for smell in smells:
            category = (
                smell.get("category", file_category)
                if isinstance(smell, dict)
                else file_category
            )
            bucket = category if category in SMELL_CATEGORIES else "other"
            totals[bucket] += 1

    return totals


def _run_detector(target: Path, output_dir: Path):
    """Run the detector binary on the target path, writing to output_dir."""
    cmd = [TOOL_BINARY, "analyze", "-i", str(target), "-o", str(output_dir)]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return f"Analysis timed out after {TIMEOUT_SECONDS}s on {target}"
 
    # Many analyzers use a non-zero exit code to signal "issues were found",
    # which is NOT an error for our purposes. Only treat it as a real failure
    # when there is no usable output on stdout.
    if proc.returncode != 0 and not proc.stdout.strip():
        return (
            f"Detector exited with code {proc.returncode} and produced no output.\n"
            f"stderr:\n{proc.stderr.strip()}"
        )
    return "success"

def _summarize_counts(output_dir: Path) -> str:
    """Format the smell counts into a human-readable summary string."""
    counts = _summarize_output(output_dir)
    total = sum(counts.values())
    breakdown = ", ".join(f"{k}: {v}" for k, v in counts.items())
    summary = f"=== {total} smell(s) found — {breakdown} ==="
    parts = [summary]
    return "\n\n".join(parts)

@mcp.tool()
def detect_code_smells(source_path: str, output_path: str) -> str:
    """Analyze Python source code for code smells.

    Args:
        source_path: Directory of Python source to analyze.
        output_path: Directory where the detector should write its report.

    Returns:
        The detector's findings in json.
    """
    target = _resolve_target(source_path)
    output_dir = _resolve_target(output_path, is_create=True)

    # Confirm the binary exists (either on PATH or as an absolute path).
    if shutil.which(TOOL_BINARY) is None and not Path(TOOL_BINARY).exists():
        raise FileNotFoundError(
            f"detector binary not found at {TOOL_BINARY!r}; "
            f"set the TOOL_BINARY environment variable"
        )

    proc = _run_detector(target, output_dir)
    if proc != "success":
        return proc  # error message

    return _summarize_counts(output_dir)



if __name__ == "__main__":
    # Defaults to stdio transport, which is what Claude Code spawns.
    mcp.run()