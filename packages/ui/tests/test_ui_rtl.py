"""RTL-safe styling enforcement (task 11.5, issue #77).

The repo's house CSS rule (and PRD §6's i18n intent) is: style the UI with CSS
*logical* properties (``text-align: start/end``, ``margin-inline-start/end``,
``padding-inline-start/end``, ``inset-inline-start/end``, ``border-inline-...``)
so the page mirrors correctly under ``dir="rtl"`` — *never* physical
``left``/``right``.

A real browser cannot run under pytest, so (as for 11.1–11.4) these tests assert
at the *serving* level. They are the durable deliverable: they FAIL the build if
any future CSS reintroduces a physical-direction declaration, and they confirm
the markup is genuinely RTL-capable (carries a ``dir`` attribute on ``<html>``).
"""

from __future__ import annotations

import re

from agent_debate.ui.app import create_app
from fastapi.testclient import TestClient

# Physical-direction CSS *property declarations* that break RTL mirroring. Each
# pattern targets a property at a declaration boundary (start-of-line or ``{``/
# ``;``/whitespace) so we never false-match a logical prop (``margin-inline-
# start``) or the word "right"/"left" appearing inside a value or content text.
_PHYSICAL_DECL_PATTERNS: dict[str, re.Pattern[str]] = {
    "margin-left": re.compile(r"(?:^|[{;\s])margin-left\s*:", re.MULTILINE),
    "margin-right": re.compile(r"(?:^|[{;\s])margin-right\s*:", re.MULTILINE),
    "padding-left": re.compile(r"(?:^|[{;\s])padding-left\s*:", re.MULTILINE),
    "padding-right": re.compile(r"(?:^|[{;\s])padding-right\s*:", re.MULTILINE),
    "border-left": re.compile(r"(?:^|[{;\s])border-left\b", re.MULTILINE),
    "border-right": re.compile(r"(?:^|[{;\s])border-right\b", re.MULTILINE),
    # Bare physical insets — ``left:``/``right:`` as a property (not part of a
    # logical ``inset-inline-...`` name, which the leading boundary excludes).
    "left": re.compile(r"(?:^|[{;\s])left\s*:", re.MULTILINE),
    "right": re.compile(r"(?:^|[{;\s])right\s*:", re.MULTILINE),
    "text-align: left": re.compile(r"text-align\s*:\s*left\b"),
    "text-align: right": re.compile(r"text-align\s*:\s*right\b"),
    "float: left": re.compile(r"float\s*:\s*left\b"),
    "float: right": re.compile(r"float\s*:\s*right\b"),
    "clear: left": re.compile(r"clear\s*:\s*left\b"),
    "clear: right": re.compile(r"clear\s*:\s*right\b"),
}


def _css() -> str:
    """Return the served stylesheet source."""
    client = TestClient(create_app())
    response = client.get("/static/style.css")
    assert response.status_code == 200
    return response.text


def _html() -> str:
    """Return the served index page source."""
    client = TestClient(create_app())
    response = client.get("/")
    assert response.status_code == 200
    return response.text


def _inline_style_blocks(html: str) -> str:
    """Concatenate any ``style="..."`` and ``<style>`` content in the HTML."""
    inline = re.findall(r'style\s*=\s*"([^"]*)"', html, re.IGNORECASE)
    blocks = re.findall(r"<style[^>]*>(.*?)</style>", html, re.IGNORECASE | re.S)
    return "\n".join(inline + blocks)


def test_stylesheet_has_no_physical_direction_declarations() -> None:
    """The served CSS uses only logical properties — no physical left/right."""
    css = _css()
    offenders = [name for name, rx in _PHYSICAL_DECL_PATTERNS.items() if rx.search(css)]
    assert not offenders, f"physical-direction CSS in style.css: {offenders}"


def test_inline_html_styles_have_no_physical_direction_declarations() -> None:
    """Any inline/`<style>` CSS in the HTML is also logical-only."""
    styles = _inline_style_blocks(_html())
    offenders = [n for n, rx in _PHYSICAL_DECL_PATTERNS.items() if rx.search(styles)]
    assert not offenders, f"physical-direction CSS in index.html: {offenders}"


def test_stylesheet_uses_logical_properties() -> None:
    """The CSS positively uses logical directional properties (meaningful test)."""
    css = _css()
    assert "inline-start" in css or "inline-end" in css
    assert re.search(r"text-align\s*:\s*start\b", css)
    assert "padding-inline" in css
    assert "margin-block" in css or "margin-inline" in css


def test_html_is_rtl_capable() -> None:
    """The document declares a ``dir`` on <html> so it mirrors under RTL."""
    html = _html()
    assert re.search(r"<html[^>]*\blang\s*=", html, re.IGNORECASE)
    assert re.search(r"<html[^>]*\bdir\s*=", html, re.IGNORECASE)
