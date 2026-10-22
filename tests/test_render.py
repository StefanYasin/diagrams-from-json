from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from diagrams_from_json import get_theme, render_spec

NS = "{http://www.w3.org/2000/svg}"
ALL_TYPES = ["service", "device", "user", "agent", "db"]


def parse(svg):
    return ET.fromstring(svg)


def texts(root):
    return " ".join((node.text or "") for node in root.iter(NS + "text"))


def test_output_is_valid_xml(base_spec):
    root = parse(render_spec(base_spec))
    assert root.tag == NS + "svg"
    assert root.get("viewBox").startswith("0 0 ")


def test_output_is_accessible(base_spec):
    root = parse(render_spec(base_spec))
    assert root.get("role") == "img"
    assert root.get("aria-labelledby") == "diagram-title diagram-desc"


def test_dark_is_the_default_theme(base_spec):
    svg = render_spec(base_spec)
    assert get_theme("dark").bg in svg
    assert get_theme("light").bg not in svg


def test_light_theme_swaps_the_palette(base_spec):
    svg = render_spec(base_spec, theme="light")
    assert get_theme("light").bg in svg
    assert get_theme("dark").bg not in svg


def test_spec_theme_is_used(base_spec):
    base_spec["theme"] = "light"
    assert get_theme("light").bg in render_spec(base_spec)


def test_explicit_theme_wins_over_the_spec(base_spec):
    base_spec["theme"] = "light"
    assert get_theme("dark").bg in render_spec(base_spec, theme="dark")


def test_unknown_theme_raises():
    with pytest.raises(ValueError):
        get_theme("neon")


def test_every_node_type_has_a_glyph():
    spec = {
        "title": "Types",
        "nodes": [{"id": "n%d" % i, "type": t, "label": t} for i, t in enumerate(ALL_TYPES)],
    }
    root = parse(render_spec(spec))
    glyphs = {node.get("data-glyph") for node in root.iter(NS + "g") if node.get("data-glyph")}
    assert glyphs == set(ALL_TYPES)


def test_node_ids_and_types_are_exposed_as_attributes(base_spec):
    root = parse(render_spec(base_spec))
    nodes = {node.get("data-node-id"): node.get("data-node-type") for node in root.iter(NS + "g") if node.get("data-node-id")}
    assert nodes == {"api": "service", "store": "db"}


def test_desc_counts_nodes_and_edges(base_spec):
    root = parse(render_spec(base_spec))
    desc = root.find(NS + "desc").text
    assert "2 nodes" in desc
    assert "1 labeled connection" in desc


def test_labels_are_escaped(base_spec):
    base_spec["nodes"][0]["label"] = 'API & "edge" <x>'
    svg = render_spec(base_spec)
    assert 'API &amp; &quot;edge&quot; &lt;x&gt;' in svg
    assert "<x>" not in svg
    parse(svg)


def test_rendering_is_deterministic(base_spec):
    assert render_spec(base_spec) == render_spec(base_spec)


def test_bidirectional_edges_get_a_start_marker(base_spec):
    base_spec["edges"][0]["bidirectional"] = True
    root = parse(render_spec(base_spec))
    paths = [node for node in root.iter(NS + "path") if node.get("marker-end")]
    assert paths and paths[0].get("marker-start") == "url(#arrow)"


def test_dashed_edges_carry_a_dash_array(base_spec):
    base_spec["edges"][0]["style"] = "dashed"
    svg = render_spec(base_spec)
    assert 'stroke-dasharray="6 5"' in svg


def test_notes_are_rendered(base_spec):
    base_spec["notes"] = [{"label": "network", "text": "Traffic stays on the tailnet."}]
    root = parse(render_spec(base_spec))
    assert "Traffic stays on the tailnet." in texts(root)
    assert "NETWORK" in texts(root)


def test_no_external_resources(base_spec):
    svg = render_spec(base_spec)
    assert svg.count("http") == 1
    assert "http://www.w3.org/2000/svg" in svg
    for forbidden in ("<image", "xlink:href", "@import", "<script"):
        assert forbidden not in svg


def test_single_node_without_edges():
    svg = render_spec({"title": "One", "nodes": [{"id": "solo", "type": "service"}]})
    root = parse(svg)
    assert len([n for n in root.iter(NS + "g") if n.get("data-node-id")]) == 1


def test_long_labels_widen_the_node(base_spec):
    short = parse(render_spec(base_spec))
    base_spec["nodes"][0]["label"] = "A deliberately long service name"
    wide = parse(render_spec(base_spec))

    def first_node_width(root):
        for node in root.iter(NS + "g"):
            if node.get("data-node-id") == "api":
                return float(node[0].get("width"))
        raise AssertionError("api node missing")

    assert first_node_width(wide) > first_node_width(short)


def test_many_nodes_wrap_into_rows():
    def band_height(count):
        spec = {
            "title": "Rows",
            "layers": [{"id": "one", "label": "One"}],
            "nodes": [{"id": "n%d" % i, "type": "service", "label": "N%d" % i} for i in range(count)],
        }
        root = parse(render_spec(spec))
        layers = [g for g in root.iter(NS + "g") if g.get("data-role") == "layers"][0]
        return float(layers[0][0].get("height"))

    assert band_height(6) > band_height(2)
