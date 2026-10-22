from __future__ import annotations

import json

import pytest

from diagrams_from_json import SpecError, load_spec, loads, validate_spec


def test_accepts_a_minimal_spec(base_spec):
    spec = validate_spec(base_spec)
    assert spec["title"] == "Tiny stack"
    assert [node["id"] for node in spec["nodes"]] == ["api", "store"]
    assert spec["edges"][0]["label"] == "SQL"


def test_label_defaults_to_the_node_id(base_spec):
    spec = validate_spec(base_spec)
    assert spec["nodes"][1]["label"] == "store"


def test_edge_defaults_to_solid_and_one_way(base_spec):
    spec = validate_spec(base_spec)
    assert spec["edges"][0]["style"] == "solid"
    assert spec["edges"][0]["bidirectional"] is False


def test_node_without_a_layer_lands_in_a_general_band(base_spec):
    base_spec["nodes"][1].pop("layer")
    spec = validate_spec(base_spec)
    assert [layer["id"] for layer in spec["layers"]] == ["core", "general"]
    assert spec["nodes"][0]["layer"] == "core"
    assert spec["nodes"][1]["layer"] == "general"


def test_a_spec_without_layers_gets_one_general_band(base_spec):
    del base_spec["layers"]
    for node in base_spec["nodes"]:
        node.pop("layer", None)
    spec = validate_spec(base_spec)
    assert spec["layers"] == [{"id": "general", "label": "General"}]
    assert {node["layer"] for node in spec["nodes"]} == {"general"}


def test_rejects_a_missing_title(base_spec):
    del base_spec["title"]
    with pytest.raises(SpecError) as err:
        validate_spec(base_spec)
    assert "title" in str(err.value)


def test_rejects_an_unknown_node_type(base_spec):
    base_spec["nodes"][0]["type"] = "queue"
    with pytest.raises(SpecError) as err:
        validate_spec(base_spec)
    message = str(err.value)
    assert "nodes[0].type" in message
    assert "queue" in message
    assert "service" in message


def test_rejects_duplicate_node_ids(base_spec):
    base_spec["nodes"].append({"id": "api", "type": "device"})
    with pytest.raises(SpecError) as err:
        validate_spec(base_spec)
    assert "duplicate node id" in str(err.value)


def test_rejects_a_layer_that_is_not_declared(base_spec):
    base_spec["nodes"][0]["layer"] = "edge"
    with pytest.raises(SpecError) as err:
        validate_spec(base_spec)
    assert "unknown layer 'edge'" in str(err.value)


def test_rejects_duplicate_layer_ids(base_spec):
    base_spec["layers"].append({"id": "core", "label": "Again"})
    with pytest.raises(SpecError) as err:
        validate_spec(base_spec)
    assert "duplicate layer id" in str(err.value)


def test_rejects_an_edge_to_an_unknown_node(base_spec):
    base_spec["edges"][0]["to"] = "cache"
    with pytest.raises(SpecError) as err:
        validate_spec(base_spec)
    assert "unknown node 'cache'" in str(err.value)


def test_rejects_a_self_edge(base_spec):
    base_spec["edges"][0]["to"] = "api"
    with pytest.raises(SpecError) as err:
        validate_spec(base_spec)
    assert "cannot connect" in str(err.value)


def test_rejects_an_unsupported_version(base_spec):
    base_spec["version"] = 3
    with pytest.raises(SpecError) as err:
        validate_spec(base_spec)
    assert "version" in str(err.value)


def test_rejects_a_version_that_is_a_boolean(base_spec):
    base_spec["version"] = True
    with pytest.raises(SpecError) as err:
        validate_spec(base_spec)
    assert "version" in str(err.value)


def test_rejects_an_unknown_theme(base_spec):
    base_spec["theme"] = "sepia"
    with pytest.raises(SpecError) as err:
        validate_spec(base_spec)
    assert "theme" in str(err.value)


def test_rejects_an_unknown_edge_style(base_spec):
    base_spec["edges"][0]["style"] = "dotted"
    with pytest.raises(SpecError) as err:
        validate_spec(base_spec)
    assert "edges[0].style" in str(err.value)


def test_rejects_an_empty_node_list(base_spec):
    base_spec["nodes"] = []
    with pytest.raises(SpecError) as err:
        validate_spec(base_spec)
    assert "nodes" in str(err.value)


def test_rejects_a_bad_note_entry(base_spec):
    base_spec["notes"] = [{"label": "network"}]
    with pytest.raises(SpecError) as err:
        validate_spec(base_spec)
    assert "notes[0].text" in str(err.value)


def test_accepts_note_strings_and_mappings(base_spec):
    base_spec["notes"] = ["plain text", {"label": "network", "text": "stays on the tailnet"}]
    spec = validate_spec(base_spec)
    assert spec["notes"][0] == {"label": None, "text": "plain text"}
    assert spec["notes"][1]["label"] == "network"


def test_reports_every_problem_at_once(base_spec):
    base_spec["nodes"][0]["type"] = "queue"
    base_spec["edges"][0]["to"] = "cache"
    with pytest.raises(SpecError) as err:
        validate_spec(base_spec)
    assert len(err.value.errors) == 2


def test_validation_is_idempotent(base_spec):
    once = validate_spec(base_spec)
    twice = validate_spec(once)
    assert once == twice


def test_yaml_errors_report_a_line_number():
    with pytest.raises(SpecError) as err:
        loads("title: [unclosed\nnodes: []\n", fmt="yaml", source="broken.yml")
    assert "broken.yml" in str(err.value)
    assert "invalid YAML" in str(err.value)


def test_json_errors_report_a_line_number():
    with pytest.raises(SpecError) as err:
        loads('{"title": "x",,}', fmt="json", source="broken.json")
    assert "broken.json" in str(err.value)
    assert "line 1" in str(err.value)


def test_json_specs_load(base_spec):
    spec = loads(json.dumps(base_spec), fmt="json", source="spec.json")
    assert spec["title"] == "Tiny stack"


def test_missing_file_is_a_spec_error(tmp_path):
    with pytest.raises(SpecError) as err:
        load_spec(str(tmp_path / "nope.yml"))
    assert "cannot read spec" in str(err.value)


def test_example_ops_stack_loads(ops_stack):
    spec = load_spec(ops_stack)
    assert spec["title"] == "Ops stack"
    assert len(spec["layers"]) == 4
    assert len(spec["nodes"]) == 11
    assert len(spec["edges"]) == 12
    assert len(spec["notes"]) == 2
    types = {node["type"] for node in spec["nodes"]}
    assert types == {"service", "device", "user", "agent", "db"}
