"""Deterministic layout: bands, node boxes, edge routes, notes panel.

No graph solver, no randomness. Nodes keep the order they appear in the spec,
which means the same spec always produces the same coordinates.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .text import num, text_width, wrap

PAD = 36
TITLE_SIZE = 20.0
SUBTITLE_SIZE = 12.5
BAND_HEADER = 34
BAND_PAD_X = 18
BAND_PAD_Y = 18
BAND_GAP = 18
NODE_H = 60
GAP_X = 42
GAP_Y = 22
MAX_COLS = 4
MIN_NODE_W = 132
MIN_BAND_W = 380
LABEL_SIZE = 14.0
NOTE_SIZE = 11.0
EDGE_LABEL_SIZE = 10.5
NOTES_SIZE = 12.0
NOTES_LINE_H = 17.0
NOTES_PAD = 20


@dataclass
class Band:
    id: str
    label: str
    x: float
    y: float
    w: float
    h: float
    rows: int


@dataclass
class NodeBox:
    id: str
    label: str
    type: str
    layer: str
    note: Optional[str]
    x: float
    y: float
    w: float
    h: float

    @property
    def cx(self) -> float:
        return self.x + self.w / 2.0

    @property
    def cy(self) -> float:
        return self.y + self.h / 2.0


@dataclass
class EdgeRoute:
    source: str
    target: str
    label: Optional[str]
    style: str
    bidirectional: bool
    path: str
    label_x: float
    label_y: float
    label_w: float


@dataclass
class NoteBlock:
    label: Optional[str]
    text: str
    x: float
    y: float
    lines: List[str]
    label_y: Optional[float] = None


@dataclass
class Layout:
    width: float
    height: float
    title: str
    subtitle: Optional[str]
    bands: List[Band] = field(default_factory=list)
    nodes: List[NodeBox] = field(default_factory=list)
    edges: List[EdgeRoute] = field(default_factory=list)
    notes: List[NoteBlock] = field(default_factory=list)
    notes_box: Optional[Tuple[float, float, float, float]] = None
    title_y: float = 0.0
    subtitle_y: float = 0.0


def _node_width(label: str, note: Optional[str]) -> float:
    inner = text_width(label, LABEL_SIZE, bold=True)
    if note:
        inner = max(inner, text_width(note, NOTE_SIZE))
    return float(max(MIN_NODE_W, math.ceil((66 + inner + 10) / 2.0) * 2))


def _bezier(p0, c1, c2, p3) -> str:
    return "M %s %s C %s %s, %s %s, %s %s" % (
        num(p0[0]), num(p0[1]),
        num(c1[0]), num(c1[1]),
        num(c2[0]), num(c2[1]),
        num(p3[0]), num(p3[1]),
    )


def _point_on(p0, c1, c2, p3, t: float) -> Tuple[float, float]:
    inv = 1.0 - t
    a = inv * inv * inv
    b = 3 * inv * inv * t
    c = 3 * inv * t * t
    d = t * t * t
    return (
        a * p0[0] + b * c1[0] + c * c2[0] + d * p3[0],
        a * p0[1] + b * c1[1] + c * c2[1] + d * p3[1],
    )


def _overlap_area(a: Tuple[float, float, float, float], b: Tuple[float, float, float, float]) -> float:
    dx = min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0])
    dy = min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1])
    if dx <= 0 or dy <= 0:
        return 0.0
    return dx * dy


def _midpoint(p0, c1, c2, p3) -> Tuple[float, float]:
    return (
        (p0[0] + 3 * c1[0] + 3 * c2[0] + p3[0]) / 8.0,
        (p0[1] + 3 * c1[1] + 3 * c2[1] + p3[1]) / 8.0,
    )


def _route(source: NodeBox, target: NodeBox) -> Dict[str, Any]:
    """Pick anchors and control points for one edge.

    Cross band edges run vertically. Same row edges arc above the nodes so the
    label has room and the line never runs through a box.
    """
    same_band = source.layer == target.layer
    if same_band and abs(source.cy - target.cy) < 0.5:
        p0 = (source.cx, source.y)
        p3 = (target.cx, target.y)
        lift = 28.0 + min(6.0, abs(p3[0] - p0[0]) * 0.04)
        c1 = (p0[0], p0[1] - lift)
        c2 = (p3[0], p3[1] - lift)
    elif same_band:
        if target.cy > source.cy:
            p0 = (source.cx, source.y + source.h)
            p3 = (target.cx, target.y)
            span = max(24.0, (p3[1] - p0[1]) * 0.45)
            c1 = (p0[0], p0[1] + span)
            c2 = (p3[0], p3[1] - span)
        else:
            p0 = (source.cx, source.y)
            p3 = (target.cx, target.y + target.h)
            span = max(24.0, (p0[1] - p3[1]) * 0.45)
            c1 = (p0[0], p0[1] - span)
            c2 = (p3[0], p3[1] + span)
    elif target.y > source.y:
        p0 = (source.cx, source.y + source.h)
        p3 = (target.cx, target.y)
        span = max(36.0, (p3[1] - p0[1]) * 0.45)
        c1 = (p0[0], p0[1] + span)
        c2 = (p3[0], p3[1] - span)
    else:
        p0 = (source.cx, source.y)
        p3 = (target.cx, target.y + target.h)
        span = max(36.0, (p0[1] - p3[1]) * 0.45)
        c1 = (p0[0], p0[1] - span)
        c2 = (p3[0], p3[1] + span)

    return {
        "p0": p0,
        "c1": c1,
        "c2": c2,
        "p3": p3,
        "mid": _midpoint(p0, c1, c2, p3),
        "path": _bezier(p0, c1, c2, p3),
    }


def _place_label(route, label_w: float, boxes, placed) -> Tuple[float, float]:
    """Slide an edge label along its curve until it stops covering boxes.

    Labels are drawn above nodes, so a bad position is still readable, but a
    clean one looks intentional. The search is deterministic and small.
    """
    steps = (0.5, 0.46, 0.54, 0.42, 0.58, 0.38, 0.62, 0.34, 0.66, 0.30, 0.70, 0.26, 0.74)
    best = None
    best_cost = None
    for t in steps:
        px, py = _point_on(route["p0"], route["c1"], route["c2"], route["p3"], t)
        rect = (px - label_w / 2.0 - 2.0, py - 10.0, label_w + 4.0, 20.0)
        cost = sum(_overlap_area(rect, box) for box in boxes)
        cost += sum(_overlap_area(rect, other) * 1.5 for other in placed)
        if cost == 0:
            return px, py
        if best_cost is None or cost < best_cost:
            best_cost = cost
            best = (px, py)
    return best if best else route["mid"]


def build_layout(spec: Dict[str, Any], min_width: float = 0.0) -> Layout:
    layers = spec["layers"]
    layer_labels = {layer["id"]: layer["label"] for layer in layers}
    order = [layer["id"] for layer in layers]

    grouped: Dict[str, List[Dict[str, Any]]] = {layer_id: [] for layer_id in order}
    for node in spec["nodes"]:
        grouped.setdefault(node["layer"], []).append(node)

    widths = {node["id"]: _node_width(node["label"], node["note"]) for node in spec["nodes"]}

    title = spec["title"]
    subtitle = spec.get("subtitle")
    title_y = PAD + TITLE_SIZE
    subtitle_y = title_y + 20 if subtitle else 0.0
    bands_top = (subtitle_y + 22) if subtitle else (title_y + 22)

    bands: List[Band] = []
    nodes: List[NodeBox] = []
    y = bands_top
    for layer_id in order:
        members = grouped.get(layer_id) or []
        if not members:
            continue
        rows = [members[i:i + MAX_COLS] for i in range(0, len(members), MAX_COLS)]
        content_w = 0.0
        for row in rows:
            row_w = sum(widths[n["id"]] for n in row) + GAP_X * (len(row) - 1)
            content_w = max(content_w, row_w)
        band_w = max(MIN_BAND_W, content_w + 2 * BAND_PAD_X)
        band_h = BAND_HEADER + BAND_PAD_Y + len(rows) * NODE_H + (len(rows) - 1) * GAP_Y + BAND_PAD_Y
        bands.append(
            Band(id=layer_id, label=layer_labels.get(layer_id, layer_id), x=0, y=y, w=band_w, h=band_h, rows=len(rows))
        )
        cursor_y = y + BAND_HEADER + BAND_PAD_Y
        for row in rows:
            cursor_x = 0.0
            for member in row:
                w = widths[member["id"]]
                nodes.append(
                    NodeBox(
                        id=member["id"],
                        label=member["label"],
                        type=member["type"],
                        layer=member["layer"],
                        note=member["note"],
                        x=cursor_x,
                        y=cursor_y,
                        w=w,
                        h=NODE_H,
                    )
                )
                cursor_x += w + GAP_X
            cursor_y += NODE_H + GAP_Y
        y += band_h + BAND_GAP

    max_band_w = 0.0
    for band in bands:
        max_band_w = max(max_band_w, band.w)
    width = max(max_band_w, min_width, MIN_BAND_W) + 2 * PAD
    for band in bands:
        band.x = PAD
        band.w = width - 2 * PAD
    for node in nodes:
        band = next(b for b in bands if b.id == node.layer)
        node.x += band.x + BAND_PAD_X

    by_id = {node.id: node for node in nodes}

    edges: List[EdgeRoute] = []
    placed_labels: List[Tuple[float, float, float, float]] = []
    box_rects = [(n.x, n.y, n.w, n.h) for n in nodes]
    for edge in spec["edges"]:
        source = by_id[edge["from"]]
        target = by_id[edge["to"]]
        route = _route(source, target)
        label_w = text_width(edge["label"] or "", EDGE_LABEL_SIZE) + 12 if edge["label"] else 0.0
        label_x, label_y = route["mid"]
        if edge["label"]:
            label_x, label_y = _place_label(route, label_w, box_rects, placed_labels)
            placed_labels.append((label_x - label_w / 2.0, label_y - 8.0, label_w, 16.0))
        edges.append(
            EdgeRoute(
                source=edge["from"],
                target=edge["to"],
                label=edge["label"],
                style=edge["style"],
                bidirectional=edge["bidirectional"],
                path=route["path"],
                label_x=label_x,
                label_y=label_y,
                label_w=label_w,
            )
        )

    layout = Layout(width=width, height=0, title=title, subtitle=subtitle, bands=bands, nodes=nodes, edges=edges,
                    title_y=title_y, subtitle_y=subtitle_y)

    bottom = bands[-1].y + bands[-1].h if bands else bands_top
    if spec["notes"]:
        panel_x = PAD
        panel_w = width - 2 * PAD
        panel_y = bottom + 24
        cursor = panel_y + NOTES_PAD + 26
        last_baseline = cursor
        for note in spec["notes"]:
            label_y = None
            if note.get("label"):
                label_y = cursor
                cursor += 15
            lines = wrap(note["text"], NOTES_SIZE, panel_w - 2 * NOTES_PAD - 14)
            layout.notes.append(
                NoteBlock(
                    label=note.get("label"),
                    text=note["text"],
                    x=panel_x + NOTES_PAD,
                    y=cursor,
                    lines=lines,
                    label_y=label_y,
                )
            )
            last_baseline = cursor + (len(lines) - 1) * NOTES_LINE_H
            cursor += len(lines) * NOTES_LINE_H + 8
        notes_h = (last_baseline + 12 + NOTES_PAD) - panel_y
        layout.notes_box = (panel_x, panel_y, panel_w, notes_h)
        bottom = panel_y + notes_h

    layout.height = bottom + PAD
    return layout
