#!/usr/bin/env python3
"""Extract a dependency-and-call-graph skeleton from a Python package.

Emits a Markdown document: a Mermaid file-to-file dependency graph, then,
per function/method, its signature, the docstring (or a <!-- describe -->
placeholder when none exists), and the methods it statically appears to call.
All extraction is mechanical; the prose descriptions are left for the agent.
"""
from __future__ import annotations
import argparse
import ast
import sys
from pathlib import Path


def module_names(root: Path) -> set[str]:
    """The set of importable module stems that live in this package."""
    return {p.stem for p in root.glob("*.py")}


def local_imports(tree: ast.AST, local: set[str]) -> set[str]:
    """Intra-package modules that this file imports (ignores third-party/stdlib)."""
    deps: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                head = alias.name.split(".")[0]
                if head in local:
                    deps.add(head)
        elif isinstance(node, ast.ImportFrom) and node.module:
            head = node.module.split(".")[0]
            if head in local:
                deps.add(head)
    return deps


def signature(fn: ast.FunctionDef | ast.AsyncFunctionDef, name: str) -> str:
    """Reconstruct a readable signature, annotations included, via ast.unparse."""
    args = [ast.unparse(a) for a in fn.args.args]
    if fn.args.vararg:
        args.append("*" + ast.unparse(fn.args.vararg))
    if fn.args.kwarg:
        args.append("**" + ast.unparse(fn.args.kwarg))
    returns = f" -> {ast.unparse(fn.returns)}" if fn.returns else ""
    return f"{name}({', '.join(args)}){returns}"


def call_edges(fn: ast.AST) -> list[str]:
    """Best-effort: names invoked inside this function body (deduped, ordered)."""
    seen: dict[str, None] = {}
    for node in ast.walk(fn):
        if isinstance(node, ast.Call):
            target = node.func
            if isinstance(target, ast.Name):
                seen.setdefault(target.id, None)
            elif isinstance(target, ast.Attribute):
                seen.setdefault(target.attr, None)
    return list(seen)


def functions(tree: ast.AST):
    """Yield (qualified_name, node) for module functions and class methods."""
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node.name, node
        elif isinstance(node, ast.ClassDef):
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    yield f"{node.name}.{sub.name}", sub


def render(root: Path) -> str:
    local = module_names(root)
    edges: list[tuple[str, str]] = []
    out: list[str] = ["# OrderMaster code map\n"]

    files = sorted(root.glob("*.py"))
    for path in files:
        tree = ast.parse(path.read_text())
        for dep in sorted(local_imports(tree, local)):
            if dep != path.stem:
                edges.append((path.stem, dep))

    out.append("## Dependency graph\n")
    out.append("```mermaid\nflowchart LR")
    for src, dst in edges:
        out.append(f"    {src} --> {dst}")
    out.append("```\n")

    for path in files:
        tree = ast.parse(path.read_text())
        deps = sorted(d for d in local_imports(tree, local) if d != path.stem)
        out.append(f"## {path.name}")
        out.append(f"Depends on: {' · '.join(deps) if deps else '(none)'}\n")
        for name, fn in functions(tree):
            if name.startswith("_") and "." not in name:
                continue  # skip private module-level helpers
            out.append(f"### {signature(fn, name)}")
            doc = ast.get_docstring(fn)
            out.append(doc.strip().splitlines()[0] if doc else "<!-- describe -->")
            calls = call_edges(fn)
            out.append(f"Calls: {' · '.join(calls) if calls else '(none)'}\n")
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path, help="package directory to document")
    args = parser.parse_args()
    print(render(args.root))
    return 0


if __name__ == "__main__":
    sys.exit(main())