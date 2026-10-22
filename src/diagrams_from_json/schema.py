"""Load and validate diagram specs written as YAML or JSON.

The spec is deliberately small. Validation returns a normalised dict so the
renderer never has to guess about missing keys, and every error carries the
path of the offending field.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List

import yaml

NODE_TYPES = ("service", "device", "user", "agent", "db")
EDGE_STYLES = ("solid", "dashed")
THEME_NAMES = ("dark", "light")
SPEC_VERSION = 1
FALLBACK_LAYER = {"id": "general", "label": "General"}

_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


class SpecError(ValueError):
    """Raised when a spec is unreadable or fails validation."""

    def __init__(self, errors: List[str]):
        self.errors = list(errors)
        super().__init__("\n".join(self.errors))


def _is_text(value: Any) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _fail(errors: List[str], path: str, message: str) -> None:
    errors.append("%s: %s" % (path, message))


def _check_id(errors: List[str], path: str, value: Any) -> bool:
    if not _is_text(value):
        _fail(errors, path, "must be a non-empty string")
        return False
    if not _ID_RE.match(value):
        _fail(errors, path, "must match [a-z0-9][a-z0-9._-]*, got %r" % value)
        return False
    return True


def _optional_text(errors: List[str], path: str, obj: Dict[str, Any], key: str) -> Any:
    if key not in obj or obj[key] is None:
        return None
    value = obj[key]
    if not isinstance(value, str):
        _fail(errors, "%s.%s" % (path, key), "must be a string")
        return None
    return value


def validate_spec(raw: Any) -> Dict[str, Any]:
    """Validate a parsed spec and return a normalised copy."""
    errors: List[str] = []
    if not isinstance(raw, dict):
        raise SpecError(["spec: expected a mapping at the top level"])

    version = raw.get("version", SPEC_VERSION)
    if isinstance(version, bool) or not isinstance(version, int) or version != SPEC_VERSION:
        _fail(errors, "version", "unsupported spec version %r, expected %d" % (version, SPEC_VERSION))

    title = raw.get("title")
    if not _is_text(title):
        _fail(errors, "title", "is required and must be a non-empty string")
        title = None

    subtitle = _optional_text(errors, "spec", raw, "subtitle")

    theme = raw.get("theme")
    if theme is not None:
        if not isinstance(theme, str) or theme not in THEME_NAMES:
            _fail(errors, "theme", "must be one of: %s" % ", ".join(THEME_NAMES))
            theme = None

    layers: List[Dict[str, str]] = []
    layer_ids: List[str] = []
    raw_layers = raw.get("layers", [])
    if raw_layers is None:
        raw_layers = []
    if not isinstance(raw_layers, list):
        _fail(errors, "layers", "must be a list")
        raw_layers = []
    for index, item in enumerate(raw_layers):
        path = "layers[%d]" % index
        if not isinstance(item, dict):
            _fail(errors, path, "must be a mapping with an id")
            continue
        layer_id = item.get("id")
        if not _check_id(errors, path + ".id", layer_id):
            continue
        if layer_id in layer_ids:
            _fail(errors, path + ".id", "duplicate layer id %r" % layer_id)
            continue
        label = item.get("label", layer_id)
        if not _is_text(label):
            _fail(errors, path + ".label", "must be a non-empty string")
            label = layer_id
        layer_ids.append(layer_id)
        layers.append({"id": layer_id, "label": label})

    if not layers:
        layers.append(dict(FALLBACK_LAYER))
        layer_ids.append(FALLBACK_LAYER["id"])

    raw_nodes = raw.get("nodes")
    if not isinstance(raw_nodes, list) or not raw_nodes:
        _fail(errors, "nodes", "must be a non-empty list")
        raw_nodes = []

    nodes: List[Dict[str, Any]] = []
    node_ids: List[str] = []
    implicit_layer = False
    for index, item in enumerate(raw_nodes):
        path = "nodes[%d]" % index
        if not isinstance(item, dict):
            _fail(errors, path, "must be a mapping")
            continue
        node_id = item.get("id")
        if not _check_id(errors, path + ".id", node_id):
            continue
        if node_id in node_ids:
            _fail(errors, path + ".id", "duplicate node id %r" % node_id)
            continue
        node_type = item.get("type")
        if not isinstance(node_type, str) or node_type not in NODE_TYPES:
            _fail(
                errors,
                path + ".type",
                "must be one of: %s, got %r" % (", ".join(NODE_TYPES), node_type),
            )
            node_type = None
        label = item.get("label", node_id)
        if not _is_text(label):
            _fail(errors, path + ".label", "must be a non-empty string")
            label = str(node_id)
        note = _optional_text(errors, path, item, "note")
        layer_id = item.get("layer")
        if layer_id is None:
            layer_id = FALLBACK_LAYER["id"]
            implicit_layer = True
        elif not isinstance(layer_id, str):
            _fail(errors, path + ".layer", "must be a string")
            layer_id = None
        elif layer_id not in layer_ids:
            _fail(
                errors,
                path + ".layer",
                "unknown layer %r, declare it under layers" % layer_id,
            )
            layer_id = None
        node_ids.append(node_id)
        nodes.append(
            {
                "id": node_id,
                "label": label,
                "type": node_type,
                "layer": layer_id,
                "note": note,
            }
        )

    if implicit_layer and FALLBACK_LAYER["id"] not in layer_ids:
        layers.append(dict(FALLBACK_LAYER))
        layer_ids.append(FALLBACK_LAYER["id"])

    raw_edges = raw.get("edges", [])
    if raw_edges is None:
        raw_edges = []
    if not isinstance(raw_edges, list):
        _fail(errors, "edges", "must be a list")
        raw_edges = []

    edges: List[Dict[str, Any]] = []
    for index, item in enumerate(raw_edges):
        path = "edges[%d]" % index
        if not isinstance(item, dict):
            _fail(errors, path, "must be a mapping")
            continue
        source = item.get("from")
        target = item.get("to")
        ok = True
        if not _is_text(source):
            _fail(errors, path + ".from", "must be a node id")
            ok = False
        elif source not in node_ids:
            _fail(errors, path + ".from", "unknown node %r" % source)
            ok = False
        if not _is_text(target):
            _fail(errors, path + ".to", "must be a node id")
            ok = False
        elif target not in node_ids:
            _fail(errors, path + ".to", "unknown node %r" % target)
            ok = False
        if ok and source == target:
            _fail(errors, path, "an edge cannot connect %r to itself" % source)
            ok = False
        label = _optional_text(errors, path, item, "label")
        style = item.get("style", "solid")
        if not isinstance(style, str) or style not in EDGE_STYLES:
            _fail(errors, path + ".style", "must be one of: %s" % ", ".join(EDGE_STYLES))
            style = "solid"
        bidirectional = item.get("bidirectional", False)
        if not isinstance(bidirectional, bool):
            _fail(errors, path + ".bidirectional", "must be true or false")
            bidirectional = False
        if not ok:
            continue
        edges.append(
            {
                "from": source,
                "to": target,
                "label": label,
                "style": style,
                "bidirectional": bidirectional,
            }
        )

    raw_notes = raw.get("notes", [])
    if raw_notes is None:
        raw_notes = []
    if not isinstance(raw_notes, list):
        _fail(errors, "notes", "must be a list")
        raw_notes = []

    notes: List[Dict[str, str]] = []
    for index, item in enumerate(raw_notes):
        path = "notes[%d]" % index
        if isinstance(item, str):
            if not _is_text(item):
                _fail(errors, path, "must not be empty")
                continue
            notes.append({"label": None, "text": item})
            continue
        if not isinstance(item, dict):
            _fail(errors, path, "must be a string or a mapping with text")
            continue
        text = item.get("text")
        if not _is_text(text):
            _fail(errors, path + ".text", "is required and must be a non-empty string")
            continue
        label = _optional_text(errors, path, item, "label")
        notes.append({"label": label, "text": text})

    if errors:
        raise SpecError(errors)

    return {
        "version": SPEC_VERSION,
        "title": title,
        "subtitle": subtitle,
        "theme": theme,
        "layers": layers,
        "nodes": nodes,
        "edges": edges,
        "notes": notes,
    }


def _format_yaml_error(exc: yaml.YAMLError) -> str:
    mark = getattr(exc, "problem_mark", None)
    problem = getattr(exc, "problem", None) or str(exc)
    if mark is not None:
        return "line %d, column %d: %s" % (mark.line + 1, mark.column + 1, problem)
    return problem


def loads(text: str, fmt: str = "yaml", source: str = "<string>") -> Dict[str, Any]:
    """Parse *text* as YAML or JSON and validate it."""
    fmt = (fmt or "yaml").lower().lstrip(".")
    if fmt in ("yml", "yaml"):
        try:
            raw = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            raise SpecError(["%s: invalid YAML, %s" % (source, _format_yaml_error(exc))])
    elif fmt == "json":
        try:
            raw = json.loads(text)
        except json.JSONDecodeError as exc:
            raise SpecError(
                ["%s: invalid JSON, line %d, column %d: %s" % (source, exc.lineno, exc.colno, exc.msg)]
            )
    else:
        raise SpecError(["%s: unknown format %r, expected yaml or json" % (source, fmt)])
    return validate_spec(raw)


def load_spec(path: str) -> Dict[str, Any]:
    """Read a .yml/.yaml/.json file and return a validated spec."""
    path = os.fspath(path)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            text = handle.read()
    except OSError as exc:
        raise SpecError(["%s: cannot read spec (%s)" % (path, exc.strerror or exc)])
    suffix = os.path.splitext(path)[1].lower()
    fmt = "json" if suffix == ".json" else "yaml"
    return loads(text, fmt=fmt, source=os.path.basename(path))
