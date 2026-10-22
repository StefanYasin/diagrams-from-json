"""Regenerate the golden SVGs. Run from the repo root with the venv python."""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from diagrams_from_json import load_spec, render_spec

GOLDEN = os.path.join(ROOT, "tests", "golden")


def write(name: str, svg: str) -> None:
    os.makedirs(GOLDEN, exist_ok=True)
    path = os.path.join(GOLDEN, name)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(svg)
    print("wrote %s (%d bytes)" % (os.path.relpath(path, ROOT), len(svg)))


def main() -> int:
    ops = load_spec(os.path.join(ROOT, "examples", "ops-stack.yml"))
    minimal = load_spec(os.path.join(ROOT, "examples", "minimal.yml"))
    dark = render_spec(ops)
    write("ops-stack.dark.svg", dark)
    write("ops-stack.light.svg", render_spec(ops, theme="light"))
    write("minimal.dark.svg", render_spec(minimal))
    with open(os.path.join(ROOT, "examples", "ops-stack.svg"), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(dark)
    print("refreshed examples/ops-stack.svg")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
