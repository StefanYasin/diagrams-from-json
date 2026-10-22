from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"


@pytest.fixture()
def base_spec():
    return {
        "version": 1,
        "title": "Tiny stack",
        "layers": [{"id": "core", "label": "Core"}],
        "nodes": [
            {"id": "api", "type": "service", "label": "API", "layer": "core"},
            {"id": "store", "type": "db", "layer": "core"},
        ],
        "edges": [{"from": "api", "to": "store", "label": "SQL"}],
    }


@pytest.fixture()
def ops_stack():
    return str(EXAMPLES / "ops-stack.yml")
