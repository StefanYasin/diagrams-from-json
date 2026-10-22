"""Tiny geometric glyphs for the five node types.

Each glyph is drawn inside a 22x22 box and scaled to fit the icon well. No
external assets, no icon fonts, so output stays self contained.
"""

from __future__ import annotations

from .text import num

_PATHS = {
    "service": (
        '<rect x="2.5" y="4" width="17" height="14" rx="3"/>'
        '<path d="M6.5 9.5h9M6.5 13.5h5"/>'
    ),
    "device": (
        '<rect x="2.5" y="3.5" width="17" height="11.5" rx="2"/>'
        '<path d="M8 19h6M11 15v4"/>'
    ),
    "user": (
        '<circle cx="11" cy="7" r="3.8"/>'
        '<path d="M3.5 19c0-3.6 3.4-5.8 7.5-5.8s7.5 2.2 7.5 5.8"/>'
    ),
    "agent": (
        '<rect x="3" y="6.5" width="16" height="12" rx="3"/>'
        '<circle cx="8" cy="12.5" r="1.4" fill="currentColor" stroke="none"/>'
        '<circle cx="14" cy="12.5" r="1.4" fill="currentColor" stroke="none"/>'
        '<path d="M11 6.5V3.5"/><circle cx="11" cy="2.4" r="1"/>'
        '<path d="M7.5 18.5v2M14.5 18.5v2"/>'
    ),
    "db": (
        '<ellipse cx="11" cy="5.5" rx="7" ry="2.6"/>'
        '<path d="M4 5.5v11c0 1.44 3.13 2.6 7 2.6s7-1.16 7-2.6v-11"/>'
        '<path d="M4 10.5c0 1.44 3.13 2.6 7 2.6s7-1.16 7-2.6"/>'
    ),
}


def glyph(node_type: str, x: float, y: float, size: float, color: str) -> str:
    """Return the SVG markup for one glyph, anchored at x/y."""
    body = _PATHS.get(node_type, _PATHS["service"])
    scale = size / 22.0
    return (
        '<g transform="translate(%s %s) scale(%s)" fill="none" stroke="%s" '
        'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" '
        'color="%s" data-glyph="%s">%s</g>'
        % (num(x), num(y), num(scale), color, color, node_type, body)
    )
