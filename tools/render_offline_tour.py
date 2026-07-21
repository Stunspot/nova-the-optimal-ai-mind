from __future__ import annotations

import argparse
import base64
from html import escape
from pathlib import Path


CSP = "; ".join(
    (
        "default-src 'none'",
        "script-src 'unsafe-inline'",
        "style-src 'unsafe-inline'",
        "img-src data:",
        "font-src data:",
        "connect-src 'none'",
        "frame-src 'none'",
        "object-src 'none'",
        "base-uri 'none'",
        "form-action 'none'",
    )
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Render Nova's visualization fragment as a self-contained offline document."
    )
    parser.add_argument("fragment", type=Path)
    parser.add_argument("stylesheet", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--logo",
        type=Path,
        help="Logo PNG to embed; defaults to collaborative-dynamics-logo.png beside the fragment",
    )
    parser.add_argument("--title", default="Meet Nova — 90-second tour")
    args = parser.parse_args()

    fragment = args.fragment.read_text(encoding="utf-8")
    stylesheet = args.stylesheet.read_text(encoding="utf-8")
    logo = args.logo or args.fragment.parent / "collaborative-dynamics-logo.png"
    if not logo.is_file():
        parser.error(f"logo asset is missing: {logo}")
    logo_uri = "data:image/png;base64," + base64.b64encode(logo.read_bytes()).decode("ascii")
    logo_reference = 'src="collaborative-dynamics-logo.png"'
    if fragment.count(logo_reference) != 1:
        parser.error("fragment must contain exactly one canonical logo reference")
    fragment = fragment.replace(logo_reference, f'src="{logo_uri}"', 1)
    document = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="referrer" content="no-referrer">
<meta http-equiv="Content-Security-Policy" content="{CSP}">
<title>{escape(args.title)}</title>
<style>
{stylesheet}
html > body {{
  box-sizing: border-box;
  width: 100%;
  max-width: 736px;
  margin: 0 auto;
  padding: 16px;
  background-color: var(--background) !important;
  background-image:
    linear-gradient(color-mix(in srgb, var(--primary) 8%, transparent) 1px, transparent 1px),
    linear-gradient(90deg, color-mix(in srgb, var(--primary) 8%, transparent) 1px, transparent 1px);
  background-size: 32px 32px;
}}
</style>
</head>
<body>
{fragment}
</body>
</html>
"""
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(document, encoding="utf-8")
    print(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
