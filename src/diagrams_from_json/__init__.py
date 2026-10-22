"""diagrams-from-json: a YAML/JSON spec to a clean SVG architecture diagram.

Public API:

    from diagrams_from_json import load_spec, render_spec, write_svg

    spec = load_spec("examples/ops-stack.yml")
    svg = render_spec(spec)                 # dark by default
    write_svg(spec, "out.svg", theme="light")
"""

from __future__ import annotations

from .render import render_spec, write_svg
from .schema import NODE_TYPES, SpecError, load_spec, loads, validate_spec
from .theme import Theme, get_theme

__version__ = "0.1.0"
__all__ = [
    "NODE_TYPES",
    "SpecError",
    "Theme",
    "__version__",
    "get_theme",
    "load_spec",
    "loads",
    "render_spec",
    "validate_spec",
    "write_svg",
]
