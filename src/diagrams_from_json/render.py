"""Render a validated spec into a standalone SVG document."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from .glyphs import glyph
from .layout import (
    EDGE_LABEL_SIZE,
    LABEL_SIZE,
    NOTE_SIZE,
    NOTES_SIZE,
    PAD,
    SUBTITLE_SIZE,
    TITLE_SIZE,
    Layout,
    NodeBox,
    build_layout,
)
from .schema import validate_spec
from .text import escape, num, text_width
from .theme import Theme, get_theme

FONT_STACK = (
    "'Inter', 'Segoe UI', 'Helvetica Neue', Helvetica, Arial, sans-serif"
)


def _text(
    x: float,
    y: float,
    value: str,
    size: float,
    fill: str,
    weight: Optional[int] = None,
    anchor: Optional[str] = None,
    letter_spacing: Optional[float] = None,
) -> str:
    bits = [
        'x="%s"' % num(x),
        'y="%s"' % num(y),
        'font-size="%s"' % num(size),
        'fill="%s"' % fill,
    ]
    if weight:
        bits.append('font-weight="%d"' % weight)
    if anchor:
        bits.append('text-anchor="%s"' % anchor)
    if letter_spacing:
        bits.append('letter-spacing="%s"' % num(letter_spacing))
    return "<text %s>%s</text>" % (" ".join(bits), escape(value))


def _node_markup(node: NodeBox, theme: Theme) -> str:
    accent = theme.accents[node.type]
    parts = [
        '<g data-node-id="%s" data-node-type="%s" data-layer="%s">'
        % (escape(node.id), escape(node.type), escape(node.layer)),
        '<rect x="%s" y="%s" width="%s" height="%s" rx="10" fill="%s" stroke="%s" stroke-width="1.2"/>'
        % (num(node.x), num(node.y), num(node.w), num(node.h), theme.node_fill, theme.panel_stroke),
        '<rect x="%s" y="%s" width="26" height="26" rx="7" fill="%s" fill-opacity="0.16"/>'
        % (num(node.x + 14), num(node.y + 17), accent),
        glyph(node.type, node.x + 16, node.y + 19, 22, accent),
    ]
    label_x = node.x + 50
    if node.note:
        parts.append(_text(label_x, node.y + 27, node.label, LABEL_SIZE, theme.text, weight=600))
        parts.append(_text(label_x, node.y + 44, node.note, NOTE_SIZE, theme.muted))
    else:
        parts.append(_text(label_x, node.y + 34.5, node.label, LABEL_SIZE, theme.text, weight=600))
    parts.append("</g>")
    return "".join(parts)


def _edge_path_markup(edge, theme: Theme) -> str:
    dash = ' stroke-dasharray="6 5"' if edge.style == "dashed" else ""
    start = ' marker-start="url(#arrow)"' if edge.bidirectional else ""
    return (
        '<g data-edge="%s-%s">'
        '<path d="%s" fill="none" stroke="%s" stroke-width="1.4" stroke-linecap="round" '
        'marker-end="url(#arrow)"%s%s/>'
        "</g>"
        % (escape(edge.source), escape(edge.target), edge.path, theme.edge, start, dash)
    )


def _edge_label_markup(edge, theme: Theme) -> str:
    if not edge.label:
        return ""
    w = edge.label_w
    x = edge.label_x - w / 2.0
    y = edge.label_y - 8
    return (
        '<g data-edge-label="%s-%s">'
        '<rect x="%s" y="%s" width="%s" height="16" rx="5" fill="%s" stroke="%s" stroke-width="1"/>'
        "%s"
        "</g>"
        % (
            escape(edge.source),
            escape(edge.target),
            num(x),
            num(y),
            num(w),
            theme.panel,
            theme.panel_stroke,
            _text(edge.label_x, edge.label_y + 3.5, edge.label, EDGE_LABEL_SIZE, theme.text, anchor="middle"),
        )
    )


def _band_markup(band, theme: Theme) -> str:
    return (
        '<g data-layer="%s">'
        '<rect x="%s" y="%s" width="%s" height="%s" rx="14" fill="%s" stroke="%s" stroke-width="1"/>'
        "%s"
        "</g>"
        % (
            escape(band.id),
            num(band.x),
            num(band.y),
            num(band.w),
            num(band.h),
            theme.panel,
            theme.panel_stroke,
            _text(band.x + 18, band.y + 23, band.label.upper(), 10.5, theme.muted, weight=600, letter_spacing=1.6),
        )
    )


def _notes_markup(layout: Layout, theme: Theme) -> str:
    if not layout.notes_box:
        return ""
    x, y, w, h = layout.notes_box
    parts = [
        '<g data-notes="true">',
        '<rect x="%s" y="%s" width="%s" height="%s" rx="12" fill="%s" stroke="%s" stroke-width="1"/>'
        % (num(x), num(y), num(w), num(h), theme.panel, theme.panel_stroke),
        _text(x + 20, y + 24, "NOTES", 10.5, theme.muted, weight=600, letter_spacing=1.6),
    ]
    for note in layout.notes:
        if note.label_y is not None:
            parts.append(
                _text(note.x, note.label_y, str(note.label).upper(), 9.5, theme.muted, weight=600, letter_spacing=1.2)
            )
        parts.append('<circle cx="%s" cy="%s" r="2" fill="%s"/>' % (num(note.x + 4), num(note.y - 4), theme.muted))
        for index, line in enumerate(note.lines):
            parts.append(_text(note.x + 14, note.y + index * 17, line, NOTES_SIZE, theme.text))
    parts.append("</g>")
    return "".join(parts)


def render_spec(spec: Dict[str, Any], theme: Optional[str] = None) -> str:
    """Validate *spec* and return the SVG document as a string."""
    data = validate_spec(spec)
    theme_name = theme or data.get("theme") or "dark"
    palette = get_theme(theme_name)

    widest_text = text_width(data["title"], TITLE_SIZE, bold=True)
    if data.get("subtitle"):
        widest_text = max(widest_text, text_width(data["subtitle"], SUBTITLE_SIZE))
    layout = build_layout(data, min_width=widest_text + 2 * PAD + 12)

    width = layout.width
    height = layout.height
    band_count = len(layout.bands)
    node_count = len(layout.nodes)
    edge_count = len(layout.edges)
    desc = "Architecture diagram with %d %s across %d %s and %d labeled %s." % (
        node_count,
        "node" if node_count == 1 else "nodes",
        band_count,
        "layer" if band_count == 1 else "layers",
        edge_count,
        "connection" if edge_count == 1 else "connections",
    )

    out = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<svg xmlns="http://www.w3.org/2000/svg" width="%s" height="%s" viewBox="0 0 %s %s" '
        'role="img" aria-labelledby="diagram-title diagram-desc" '
        'font-family="%s" shape-rendering="geometricPrecision">'
        % (num(width), num(height), num(width), num(height), FONT_STACK),
        "<title id=\"diagram-title\">%s</title>" % escape(data["title"]),
        "<desc id=\"diagram-desc\">%s</desc>" % escape(desc),
        "<defs>"
        '<marker id="arrow" viewBox="0 0 9 9" refX="9" refY="4.5" markerWidth="9" markerHeight="9" '
        'markerUnits="userSpaceOnUse" orient="auto-start-reverse">'
        '<path d="M0 0 L9 4.5 L0 9 z" fill="%s"/>'
        "</marker></defs>" % palette.edge,
        '<rect class="background" x="0" y="0" width="%s" height="%s" fill="%s"/>' % (num(width), num(height), palette.bg),
        '<g data-role="header">',
        _text(PAD, layout.title_y, data["title"], TITLE_SIZE, palette.text, weight=600),
    ]
    if data.get("subtitle"):
        out.append(_text(PAD, layout.subtitle_y, data["subtitle"], SUBTITLE_SIZE, palette.muted))
    out.append("</g>")

    out.append('<g data-role="layers">')
    out.extend(_band_markup(band, palette) for band in layout.bands)
    out.append("</g>")

    out.append('<g data-role="edges">')
    out.extend(_edge_path_markup(edge, palette) for edge in layout.edges)
    out.append("</g>")

    out.append('<g data-role="nodes">')
    out.extend(_node_markup(node, palette) for node in layout.nodes)
    out.append("</g>")

    out.append('<g data-role="edge-labels">')
    out.extend(markup for markup in (_edge_label_markup(edge, palette) for edge in layout.edges) if markup)
    out.append("</g>")

    out.append(_notes_markup(layout, palette))
    out.append("</svg>")
    out.append("")
    return "\n".join(out)


def write_svg(spec: Dict[str, Any], path: str, theme: Optional[str] = None) -> str:
    """Render *spec* and write it to *path*. Returns the SVG text."""
    svg = render_spec(spec, theme=theme)
    directory = os.path.dirname(os.path.abspath(path))
    if directory and not os.path.isdir(directory):
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(svg)
    return svg
