"""Command line entry point."""

from __future__ import annotations

import argparse
import os
import sys
from typing import List, Optional

from . import __version__
from .render import render_spec
from .schema import SpecError, load_spec


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="diagrams-from-json",
        description="Turn a YAML or JSON spec into a clean SVG architecture diagram.",
    )
    parser.add_argument("spec", help="path to a .yml, .yaml or .json spec")
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="output SVG path (default: spec path with .svg, use - for stdout)",
    )
    parser.add_argument("--light", action="store_true", help="use the light theme instead of the default dark theme")
    parser.add_argument("--title", default=None, help="override the title from the spec")
    parser.add_argument("-q", "--quiet", action="store_true", help="do not print the output path")
    parser.add_argument("--version", action="version", version="%(prog)s " + __version__)
    return parser


def _default_output(spec_path: str) -> str:
    base, _ = os.path.splitext(spec_path)
    return base + ".svg"


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        spec = load_spec(args.spec)
    except SpecError as exc:
        for message in exc.errors:
            print("error: %s" % message, file=sys.stderr)
        return 2

    if args.title:
        spec["title"] = args.title
    theme = "light" if args.light else None

    try:
        svg = render_spec(spec, theme=theme)
    except SpecError as exc:  # pragma: no cover - load_spec already validated
        for message in exc.errors:
            print("error: %s" % message, file=sys.stderr)
        return 2

    output = args.output if args.output is not None else _default_output(args.spec)
    if output == "-":
        sys.stdout.write(svg)
        return 0

    try:
        directory = os.path.dirname(os.path.abspath(output))
        if directory and not os.path.isdir(directory):
            os.makedirs(directory, exist_ok=True)
        with open(output, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(svg)
    except OSError as exc:
        print("error: cannot write %s (%s)" % (output, exc.strerror or exc), file=sys.stderr)
        return 1

    if not args.quiet:
        print("wrote %s" % output)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
