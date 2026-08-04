#!/usr/bin/env python3
"""Audit the static MIND Pages source and its three required visual roles."""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
import struct
import sys
from urllib.parse import urlparse


REQUIRED_IMAGES = {
    "assets/mind-icon-1024.png": (1024, 1024, "icon", "1:1"),
    "assets/mind-hero.png": (1600, 900, "hero", "16:9"),
    "assets/mind-capability-card-1080x1350.png": (1080, 1350, "capability_card", "4:5"),
}


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: list[str] = []
        self.links: list[str] = []
        self.images: list[dict[str, str | None]] = []
        self.headings: list[int] = []
        self.html_lang = ""
        self.stylesheets: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "html":
            self.html_lang = values.get("lang") or ""
        if values.get("id"):
            self.ids.append(str(values["id"]))
        if tag == "a" and values.get("href"):
            self.links.append(str(values["href"]))
        if tag == "img":
            self.images.append(
                {
                    "src": values.get("src"),
                    "alt": values.get("alt"),
                    "width": values.get("width"),
                    "height": values.get("height"),
                }
            )
        if tag in {f"h{level}" for level in range(1, 7)}:
            self.headings.append(int(tag[1]))
        if tag == "link" and values.get("rel") == "stylesheet" and values.get("href"):
            self.stylesheets.append(str(values["href"]))


def png_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()[:24]
    if len(data) != 24 or data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise ValueError("not a PNG with a readable IHDR")
    return struct.unpack(">II", data[16:24])


def audit(root: Path) -> dict[str, object]:
    index = root / "index.html"
    parser = PageParser()
    parser.feed(index.read_text(encoding="utf-8"))
    issues: list[str] = []

    if parser.html_lang != "en":
        issues.append("html lang must be en")
    if parser.headings.count(1) != 1:
        issues.append("page must contain exactly one H1")
    for previous, current in zip(parser.headings, parser.headings[1:]):
        if current > previous + 1:
            issues.append(f"heading level skips from H{previous} to H{current}")
    duplicates = sorted({value for value in parser.ids if parser.ids.count(value) > 1})
    if duplicates:
        issues.append(f"duplicate ids: {duplicates}")
    if "style.css" not in parser.stylesheets:
        issues.append("style.css is not linked")

    ids = set(parser.ids)
    for href in parser.links:
        if href.startswith("#"):
            if href[1:] not in ids:
                issues.append(f"broken internal anchor: {href}")
            continue
        parsed = urlparse(href)
        if parsed.scheme:
            if parsed.scheme != "https":
                issues.append(f"external link is not HTTPS: {href}")
            continue
        target = (root / parsed.path).resolve()
        try:
            target.relative_to(root.resolve())
        except ValueError:
            issues.append(f"link escapes site root: {href}")
            continue
        if not target.exists():
            issues.append(f"missing local link target: {href}")

    observed_sources = {str(item["src"]) for item in parser.images if item["src"]}
    for image in parser.images:
        if image["src"] is None:
            issues.append("image is missing src")
        if image["alt"] is None:
            issues.append(f"image is missing alt: {image['src']}")
        if image["width"] is None or image["height"] is None:
            issues.append(f"image is missing intrinsic dimensions: {image['src']}")

    visual_records: list[dict[str, object]] = []
    for relative, (width, height, role, ratio) in REQUIRED_IMAGES.items():
        path = root / relative
        if relative not in observed_sources:
            issues.append(f"required {role} is not rendered: {relative}")
            continue
        try:
            observed = png_dimensions(path)
        except (OSError, ValueError) as error:
            issues.append(f"cannot inspect {role}: {relative}: {error}")
            continue
        if observed != (width, height):
            issues.append(f"{role} dimensions are {observed[0]}x{observed[1]}, expected {width}x{height}")
        visual_records.append(
            {
                "role": role,
                "path": relative,
                "width": observed[0],
                "height": observed[1],
                "aspect_ratio": ratio,
                "rendered": True,
            }
        )

    return {
        "format": "cd-mind-pages-audit/v1",
        "ok": not issues,
        "html": "index.html",
        "heading_count": len(parser.headings),
        "link_count": len(parser.links),
        "image_element_count": len(parser.images),
        "visuals": visual_records,
        "issues": issues,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=Path("docs"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        result = audit(args.root.resolve())
    except (OSError, UnicodeDecodeError, ValueError) as error:
        result = {"format": "cd-mind-pages-audit/v1", "ok": False, "issues": [str(error)]}
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8", newline="\n")
    print(rendered, end="")
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
