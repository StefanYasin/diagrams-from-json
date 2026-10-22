from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"


def run_cli(*args, cwd=None):
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run(
        [sys.executable, "-m", "diagrams_from_json", *args],
        capture_output=True,
        text=True,
        cwd=str(cwd or ROOT),
        env=env,
        check=False,
    )


def test_writes_the_requested_output(tmp_path):
    out = tmp_path / "stack.svg"
    result = run_cli(str(EXAMPLES / "ops-stack.yml"), "-o", str(out))
    assert result.returncode == 0, result.stderr
    assert out.exists()
    assert out.read_text(encoding="utf-8").startswith("<?xml")
    assert "wrote" in result.stdout


def test_defaults_to_the_spec_path(tmp_path):
    spec = tmp_path / "tiny.yml"
    spec.write_text(
        "title: Tiny\nnodes:\n  - id: api\n    type: service\n",
        encoding="utf-8",
    )
    result = run_cli(str(spec), cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "tiny.svg").exists()


def test_dash_writes_to_stdout():
    result = run_cli(str(EXAMPLES / "minimal.yml"), "-o", "-")
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("<?xml")
    assert result.stdout.rstrip().endswith("</svg>")


def test_light_flag_changes_the_background():
    dark = run_cli(str(EXAMPLES / "minimal.yml"), "-o", "-")
    light = run_cli(str(EXAMPLES / "minimal.yml"), "-o", "-", "--light")
    assert "#0b1016" in dark.stdout
    assert "#ffffff" in light.stdout
    assert "#0b1016" not in light.stdout


def test_title_override():
    result = run_cli(str(EXAMPLES / "minimal.yml"), "-o", "-", "--title", "Renamed")
    assert "<title id=\"diagram-title\">Renamed</title>" in result.stdout


def test_quiet_suppresses_the_path(tmp_path):
    out = tmp_path / "quiet.svg"
    result = run_cli(str(EXAMPLES / "minimal.yml"), "-o", str(out), "--quiet")
    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_invalid_spec_exits_2(tmp_path):
    spec = tmp_path / "bad.yml"
    spec.write_text("title: Bad\nnodes:\n  - id: api\n    type: queue\n", encoding="utf-8")
    result = run_cli(str(spec), "-o", str(tmp_path / "bad.svg"))
    assert result.returncode == 2
    assert "nodes[0].type" in result.stderr
    assert not (tmp_path / "bad.svg").exists()


def test_missing_file_exits_2(tmp_path):
    result = run_cli(str(tmp_path / "nope.yml"))
    assert result.returncode == 2
    assert "cannot read spec" in result.stderr


def test_version_flag():
    result = run_cli("--version")
    assert result.returncode == 0
    assert "0.1.0" in result.stdout
