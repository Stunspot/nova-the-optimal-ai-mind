from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

DOCS = Path(__file__).resolve().parent
REQUIRED = {"index.html", "install.html", "capabilities.html", "workflows.html", "trust.html", "support.html", "security.html", "notices.html", "upgrade.html", "troubleshooting.html", "404.html", "style.css"}
STALE_RUNTIME_PHRASES = ("forty-one visible", "shared MIND database", "automatic capability reminders", "standalone MIND package", "semantic arm's reach regression")

class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []
        self.ids: set[str] = set()
        self.images: list[dict[str, str]] = []
        self.h1_count = 0
        self.html_lang = ""
        self.main_ids: set[str] = set()
        self.skip_link = False
        self.nav_label = False
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = {key: value or "" for key, value in attrs}
        if tag == "html": self.html_lang = data.get("lang", "")
        if data.get("id"): self.ids.add(data["id"])
        if tag == "a" and data.get("href"):
            self.links.append(data["href"])
            if data.get("class") == "skip-link" and data["href"] == "#main": self.skip_link = True
        if tag == "img": self.images.append(data)
        if tag == "h1": self.h1_count += 1
        if tag == "main" and data.get("id"): self.main_ids.add(data["id"])
        if tag == "nav" and data.get("aria-label"): self.nav_label = True

def check_page(path: Path) -> list[str]:
    failures: list[str] = []
    text = path.read_text(encoding="utf-8")
    parser = PageParser(); parser.feed(text)
    if parser.html_lang != "en": failures.append("missing html lang=en")
    if parser.h1_count != 1: failures.append(f"expected one h1, found {parser.h1_count}")
    if "main" not in parser.main_ids or not parser.skip_link: failures.append("missing working skip link and #main landmark")
    if not parser.nav_label: failures.append("navigation lacks an accessible label")
    for image in parser.images:
        if "alt" not in image or not image["alt"].strip(): failures.append(f"image lacks useful alt text: {image.get('src', '<unknown>')}")
    lowered = text.casefold()
    for phrase in STALE_RUNTIME_PHRASES:
        if phrase.casefold() in lowered: failures.append(f"stale runtime phrase: {phrase}")
    for href in parser.links:
        split = urlsplit(href)
        if split.scheme or split.netloc or href.startswith(("mailto:", "tel:")): continue
        raw_path = unquote(split.path)
        target = path if not raw_path else (path.parent / raw_path).resolve()
        try:
            target.relative_to(DOCS)
        except ValueError:
            failures.append(f"link escapes deployed docs artifact: {href}"); continue
        if not target.exists():
            failures.append(f"missing link target: {href}"); continue
        if split.fragment and target.suffix.casefold() == ".html":
            target_parser = PageParser(); target_parser.feed(target.read_text(encoding="utf-8"))
            if split.fragment not in target_parser.ids: failures.append(f"missing link fragment: {href}")
    return failures

def main() -> int:
    failures: list[str] = []
    missing = sorted(REQUIRED - {path.name for path in DOCS.iterdir()})
    failures.extend(f"missing required site file: {name}" for name in missing)
    for page in sorted(DOCS.glob("*.html")):
        failures.extend(f"{page.name}: {failure}" for failure in check_page(page))
    css = (DOCS / "style.css").read_text(encoding="utf-8") if (DOCS / "style.css").exists() else ""
    if "prefers-reduced-motion" not in css: failures.append("style.css: missing reduced-motion accommodation")
    if not re.search(r":focus-visible|:focus\b", css): failures.append("style.css: missing visible focus treatment")
    if failures:
        print("SITE CHECK: FAIL")
        for item in failures: print(f"- {item}")
        return 1
    print(f"SITE CHECK: PASS ({len(list(DOCS.glob('*.html')))} pages)")
    return 0

if __name__ == "__main__": sys.exit(main())
