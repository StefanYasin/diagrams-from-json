"""Geometry invariants: boxes stay in their band, arrows land on borders,
edge labels never sit on top of a node."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from diagrams_from_json import load_spec, render_spec, validate_spec
from diagrams_from_json.text import text_width

NS = "{http://www.w3.org/2000/svg}"


def node_boxes(root):
    boxes = {}
    for group in root.iter(NS + "g"):
        node_id = group.get("data-node-id")
        if not node_id:
            continue
        rect = group[0]
        boxes[node_id] = {
            "layer": group.get("data-layer"),
            "x": float(rect.get("x")),
            "y": float(rect.get("y")),
            "w": float(rect.get("width")),
            "h": float(rect.get("height")),
        }
    return boxes


def band_boxes(root):
    boxes = {}
    for group in root.iter(NS + "g"):
        if group.get("data-role") != "layers":
            continue
        for band in group:
            rect = band[0]
            boxes[band.get("data-layer")] = {
                "x": float(rect.get("x")),
                "y": float(rect.get("y")),
                "w": float(rect.get("width")),
                "h": float(rect.get("height")),
            }
    return boxes


def label_boxes(root):
    boxes = []
    for group in root.iter(NS + "g"):
        if group.get("data-edge-label"):
            rect = group[0]
            boxes.append(
                {
                    "id": group.get("data-edge-label"),
                    "x": float(rect.get("x")),
                    "y": float(rect.get("y")),
                    "w": float(rect.get("width")),
                    "h": float(rect.get("height")),
                }
            )
    return boxes


def overlap(a, b):
    dx = min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"])
    dy = min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"])
    return dx > 0 and dy > 0


def edge_paths(root):
    for group in root.iter(NS + "g"):
        if "data-edge" in group.attrib:
            yield group.get("data-edge"), group[0].get("d")


def test_nodes_sit_inside_their_band(ops_stack):
    root = ET.fromstring(render_spec(load_spec(ops_stack)))
    bands = band_boxes(root)
    for node_id, box in node_boxes(root).items():
        band = bands[box["layer"]]
        assert box["x"] >= band["x"]
        assert box["y"] >= band["y"]
        assert box["x"] + box["w"] <= band["x"] + band["w"] + 0.01
        assert box["y"] + box["h"] <= band["y"] + band["h"] + 0.01


def test_nodes_never_overlap(ops_stack):
    root = ET.fromstring(render_spec(load_spec(ops_stack)))
    boxes = node_boxes(root)
    ids = list(boxes)
    for i, first in enumerate(ids):
        for second in ids[i + 1:]:
            assert not overlap(boxes[first], boxes[second]), "%s overlaps %s" % (first, second)


def test_edges_start_and_end_on_a_node_border(ops_stack):
    root = ET.fromstring(render_spec(load_spec(ops_stack)))
    anchors = set()
    for box in node_boxes(root).values():
        anchors.add((round(box["x"] + box["w"] / 2, 2), round(box["y"], 2)))
        anchors.add((round(box["x"] + box["w"] / 2, 2), round(box["y"] + box["h"], 2)))
        anchors.add((round(box["x"], 2), round(box["y"] + box["h"] / 2, 2)))
        anchors.add((round(box["x"] + box["w"], 2), round(box["y"] + box["h"] / 2, 2)))
    for name, path in edge_paths(root):
        numbers = [float(value) for value in re.findall(r"-?\d+\.?\d*", path)]
        assert (round(numbers[0], 2), round(numbers[1], 2)) in anchors, name
        assert (round(numbers[-2], 2), round(numbers[-1], 2)) in anchors, name


def test_edge_labels_do_not_cover_nodes(ops_stack):
    root = ET.fromstring(render_spec(load_spec(ops_stack)))
    boxes = node_boxes(root)
    for label in label_boxes(root):
        for node_id, box in boxes.items():
            assert not overlap(label, box), "%s covers %s" % (label["id"], node_id)


def test_edge_labels_do_not_cover_each_other(ops_stack):
    root = ET.fromstring(render_spec(load_spec(ops_stack)))
    labels = label_boxes(root)
    for i, first in enumerate(labels):
        for second in labels[i + 1:]:
            assert not overlap(first, second), "%s overlaps %s" % (first["id"], second["id"])


def test_everything_fits_inside_the_canvas(ops_stack):
    root = ET.fromstring(render_spec(load_spec(ops_stack)))
    width = float(root.get("width"))
    height = float(root.get("height"))
    boxes = list(node_boxes(root).values()) + list(band_boxes(root).values()) + label_boxes(root)
    for box in boxes:
        assert box["x"] >= 0 and box["y"] >= 0
        assert box["x"] + box["w"] <= width + 0.01
        assert box["y"] + box["h"] <= height + 0.01


def test_node_text_fits_horizontally(ops_stack):
    root = ET.fromstring(render_spec(load_spec(ops_stack)))
    boxes = node_boxes(root)
    for group in root.iter(NS + "g"):
        node_id = group.get("data-node-id")
        if not node_id:
            continue
        box = boxes[node_id]
        for text in (child for child in group if child.tag == NS + "text"):
            size = float(text.get("font-size"))
            bold = int(text.get("font-weight") or 400) >= 600
            right = float(text.get("x")) + text_width(text.text or "", size, bold)
            assert right <= box["x"] + box["w"] - 4, node_id


def test_band_order_follows_the_spec(ops_stack):
    spec = load_spec(ops_stack)
    root = ET.fromstring(render_spec(spec))
    bands = band_boxes(root)
    order = sorted(bands, key=lambda name: bands[name]["y"])
    assert order == [layer["id"] for layer in spec["layers"]]


def test_implicit_general_layer_renders():
    spec = validate_spec({"title": "Loose", "nodes": [{"id": "only", "type": "db"}]})
    root = ET.fromstring(render_spec(spec))
    assert "general" in band_boxes(root)
