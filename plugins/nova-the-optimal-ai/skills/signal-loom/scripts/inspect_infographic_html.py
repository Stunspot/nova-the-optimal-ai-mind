#!/usr/bin/env python3
"""Perform bounded static inspection of an infographic HTML file."""

from __future__ import annotations

import argparse
import re
import sys
from html.parser import HTMLParser
from pathlib import Path


class Inspector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.tags: dict[str, int] = {}
        self.h1_count = 0
        self.headings: list[int] = []
        self.has_lang = False
        self.has_title = False
        self.has_viewport = False
        self.has_og_title = False
        self.has_twitter_card = False
        self.animated = False
        self.reduced_motion = False
        self._in_title = False
        self._title_text = ""

    def handle_decl(self, decl: str) -> None:
        if decl.lower() != "doctype html":
            self.warnings.append("nonstandard doctype declaration")

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        data = {key.lower(): (value or "") for key, value in attrs}
        self.tags[tag] = self.tags.get(tag, 0) + 1
        if tag == "html" and data.get("lang", "").strip():
            self.has_lang = True
        if tag == "title":
            self._in_title = True
        if tag == "meta" and data.get("name", "").lower() == "viewport":
            self.has_viewport = True
        if tag == "meta" and data.get("property", "").lower() == "og:title":
            self.has_og_title = True
        if tag == "meta" and data.get("name", "").lower() == "twitter:card":
            self.has_twitter_card = True
        if tag in {"iframe", "object", "embed"}:
            self.errors.append(f"risky embedded element: <{tag}>")
        if tag == "script" and data.get("src"):
            self.errors.append(f"external script denied by default: {data['src']}")
        if tag == "img" and "alt" not in data:
            self.errors.append("image missing alt attribute")
        if tag == "canvas" and not (data.get("aria-label") or data.get("aria-describedby") or data.get("data-summary")):
            self.errors.append("canvas lacks a textual description hook")
        if tag == "a":
            href = data.get("href", "").strip().lower()
            if href.startswith("javascript:"):
                self.errors.append("javascript: URL found")
            if data.get("target", "").lower() == "_blank":
                rel = {part.lower() for part in data.get("rel", "").split()}
                if not {"noopener", "noreferrer"}.intersection(rel):
                    self.warnings.append("target=_blank link lacks noopener or noreferrer")
        for name in data:
            if name.startswith("on"):
                self.errors.append(f"inline event handler found: {name}")
        if re.fullmatch(r"h[1-6]", tag):
            level = int(tag[1])
            self.headings.append(level)
            if level == 1:
                self.h1_count += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._in_title = False
            self.has_title = bool(self._title_text.strip())

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title_text += data


def inspect(path: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return [f"unable to read UTF-8 HTML: {exc}"], warnings
    if not re.match(r"\s*<!doctype\s+html\s*>", text, flags=re.IGNORECASE):
        errors.append("missing HTML5 doctype")
    parser = Inspector()
    try:
        parser.feed(text)
    except Exception as exc:  # HTMLParser is forgiving; preserve any unexpected parser failure.
        errors.append(f"parser failure: {exc}")
    errors.extend(parser.errors)
    warnings.extend(parser.warnings)
    for region in ("header", "main", "footer"):
        if parser.tags.get(region, 0) == 0:
            errors.append(f"missing semantic <{region}> region")
    if not parser.has_lang:
        errors.append("html element lacks a non-empty lang attribute")
    if not parser.has_title:
        errors.append("document lacks a non-empty title")
    if not parser.has_viewport:
        errors.append("missing viewport metadata")
    if parser.h1_count != 1:
        errors.append(f"expected exactly one h1, found {parser.h1_count}")
    for before, after in zip(parser.headings, parser.headings[1:]):
        if after > before + 1:
            errors.append(f"heading level jumps from h{before} to h{after}")
    if not parser.has_og_title:
        warnings.append("missing og:title metadata")
    if not parser.has_twitter_card:
        warnings.append("missing twitter:card metadata")
    if re.search(r"(@keyframes|animation\s*:|transition\s*:)", text, flags=re.IGNORECASE):
        parser.animated = True
    if re.search(r"prefers-reduced-motion\s*:\s*reduce", text, flags=re.IGNORECASE):
        parser.reduced_motion = True
    if parser.animated and not parser.reduced_motion:
        errors.append("animation or transition found without prefers-reduced-motion treatment")
    if re.search(r"\b(TODO|PLACEHOLDER|LOREM IPSUM)\b", text, flags=re.IGNORECASE):
        warnings.append("placeholder marker found; confirm it is visibly disclosed or remove it")
    return errors, warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("html", type=Path)
    args = parser.parse_args(argv)
    errors, warnings = inspect(args.html)
    for warning in warnings:
        print(f"WARN: {warning}")
    for error in errors:
        print(f"ERROR: {error}")
    if errors:
        print(f"FAIL: {len(errors)} error(s), {len(warnings)} warning(s)")
        return 1
    print(f"PASS: bounded static HTML checks ({len(warnings)} warning(s))")
    print("LIMIT: no claim of sanitization, rendered accessibility, browser behavior, security, or visual quality")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
