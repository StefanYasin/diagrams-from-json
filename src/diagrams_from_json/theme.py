"""Colour palettes for the dark (default) and light themes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

DEFAULT_THEME = "dark"


@dataclass(frozen=True)
class Theme:
    name: str
    bg: str
    panel: str
    panel_stroke: str
    node_fill: str
    text: str
    muted: str
    edge: str
    label_bg: str
    accents: Dict[str, str] = field(default_factory=dict)


DARK = Theme(
    name="dark",
    bg="#0b1016",
    panel="#111a23",
    panel_stroke="#22303d",
    node_fill="#16212c",
    text="#e9f0f7",
    muted="#8fa0b1",
    edge="#63768a",
    label_bg="#0b1016",
    accents={
        "service": "#4d9bff",
        "device": "#35d6a8",
        "user": "#f7c25c",
        "agent": "#b18cff",
        "db": "#f472b6",
    },
)

LIGHT = Theme(
    name="light",
    bg="#ffffff",
    panel="#f5f8fb",
    panel_stroke="#d5dfe8",
    node_fill="#ffffff",
    text="#16212c",
    muted="#5b6b7b",
    edge="#8092a3",
    label_bg="#ffffff",
    accents={
        "service": "#1f6feb",
        "device": "#0f9d76",
        "user": "#a86800",
        "agent": "#7c3aed",
        "db": "#c02678",
    },
)

THEMES = {"dark": DARK, "light": LIGHT}


def get_theme(name: str) -> Theme:
    try:
        return THEMES[name]
    except KeyError:
        raise ValueError(
            "unknown theme %r, expected one of: %s" % (name, ", ".join(sorted(THEMES)))
        )
