"""Text metrics, escaping and number formatting.

Everything here is deterministic: the same string always produces the same
width, so golden-file tests stay stable across machines and Python versions.
"""

from __future__ import annotations

from xml.sax.saxutils import escape as _escape

# Advance widths for Helvetica/Arial in 1/1000 em. Enough accuracy for layout.
_WIDTHS = {
    " ": 278, "!": 278, '"': 355, "#": 556, "$": 556, "%": 889, "&": 667,
    "'": 191, "(": 333, ")": 333, "*": 389, "+": 584, ",": 278, "-": 333,
    ".": 278, "/": 278, ":": 278, ";": 278, "<": 584, "=": 584, ">": 584,
    "?": 556, "@": 1015, "[": 278, "\\": 278, "]": 278, "^": 469, "_": 556,
    "`": 333, "{": 334, "|": 260, "}": 334, "~": 584,
}
for _c in "0123456789":
    _WIDTHS[_c] = 556
for _c, _w in zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ",
                  (667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667, 556,
                   833, 722, 778, 667, 778, 722, 667, 611, 722, 667, 944, 667,
                   667, 611)):
    _WIDTHS[_c] = _w
for _c, _w in zip("abcdefghijklmnopqrstuvwxyz",
                  (556, 556, 500, 556, 556, 278, 556, 556, 222, 222, 500, 222,
                   833, 556, 556, 556, 556, 333, 500, 278, 556, 500, 722, 500,
                   500, 500)):
    _WIDTHS[_c] = _w

BOLD_FACTOR = 1.055


def text_width(text: str, size: float, bold: bool = False) -> float:
    """Approximate rendered width of *text* in user units."""
    total = 0
    for ch in text:
        total += _WIDTHS.get(ch, 600)
    width = total / 1000.0 * size
    if bold:
        width *= BOLD_FACTOR
    return width


def escape(text: str) -> str:
    return _escape(str(text), {'"': "&quot;"})


def num(value: float) -> str:
    """Format a coordinate without trailing noise."""
    value = round(float(value), 2)
    if value == int(value):
        return str(int(value))
    return ("%.2f" % value).rstrip("0").rstrip(".")


def wrap(text: str, size: float, max_width: float, bold: bool = False) -> list:
    """Greedy word wrap. Long words are hard-split so nothing overflows."""
    words = str(text).split()
    if not words:
        return [""]
    lines = []
    current = ""
    for word in words:
        candidate = word if not current else current + " " + word
        if text_width(candidate, size, bold) <= max_width:
            current = candidate
            continue
        if current:
            lines.append(current)
            current = ""
        while text_width(word, size, bold) > max_width:
            cut = len(word)
            while cut > 1 and text_width(word[:cut], size, bold) > max_width:
                cut -= 1
            lines.append(word[:cut])
            word = word[cut:]
        current = word
    if current:
        lines.append(current)
    return lines
