---
name: code-map
description: >-
  Generate a dependency-and-call-graph document for the OrderMaster codebase:
  a file-to-file Mermaid dependency graph plus, per method, its signature, a
  short description, and the methods it calls. Use when documenting the
  codebase, onboarding to a module, or reviewing how a change ripples through
  the call graph.
allowed-tools: Read, Bash(python scripts/gen_docs.py *), Edit
---

# Code map

1. Run `python scripts/gen_docs.py <package>` to produce the skeleton.
2. For each `<!-- describe -->` placeholder, read only that function's body
   and replace the placeholder with a one-line description of what it does.
3. Leave every signature, dependency edge, and call list exactly as the
   script emitted them — do not edit or "correct" them.
4. Write the finished document to `docs/code-map.md`.

See `references/output-format.md` for the exact heading and Mermaid spec.