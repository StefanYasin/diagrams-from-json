"""Golden file tests. Regenerate with:

    python scripts/build_goldens.py
"""

from __future__ import annotations

import difflib
from pathlib import Path

import pytest

from diagrams_from_json import load_spec, render_spec

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = Path(__file__).resolve().parent / "golden"
OPS_STACK = ROOT / "examples" / "ops-stack.yml"
MINIMAL = ROOT / "examples" / "minimal.yml"


def compare(name: str, svg: str) -> None:
    path = GOLDEN / name
    if not path.exists():  # pragma: no cover - guard against a missing fixture
        pytest.fail("missing golden file %s, run scripts/build_goldens.py" % name)
    expected = path.read_text(encoding="utf-8")
    if svg != expected:
        diff = "".join(
            difflib.unified_diff(expected.splitlines(True), svg.splitlines(True), fromfile=name, tofile="rendered")
        )
        pytest.fail("golden mismatch for %s\n%s" % (name, diff[:4000]))


def test_ops_stack_dark():
    compare("ops-stack.dark.svg", render_spec(load_spec(str(OPS_STACK))))


def test_ops_stack_light():
    compare("ops-stack.light.svg", render_spec(load_spec(str(OPS_STACK)), theme="light"))


def test_minimal_dark():
    compare("minimal.dark.svg", render_spec(load_spec(str(MINIMAL))))


def test_committed_preview_matches_the_renderer():
    """examples/ops-stack.svg is the README preview, so it must not drift."""
    preview = (ROOT / "examples" / "ops-stack.svg").read_text(encoding="utf-8")
    compare("ops-stack.dark.svg", preview)
