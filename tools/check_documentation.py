from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

MAINTAINED = (
    "README.md", "START-HERE.md", "LICENSE.md", "ATTRIBUTION.md", "NOTICE.md",
    "TRADEMARKS.md", "PROVENANCE.md", "SECURITY.md", "SUPPORT.md",
    "THIRD-PARTY-NOTICES.md", "RELEASE-NOTES.md", "docs/CAPABILITY-GUIDE.md",
    "docs/HOST-MATRIX.md", "docs/INSTALL-CLAUDE.md", "docs/INSTALL-CODEX.md",
    "docs/MAINTAINER-GUIDE.md", "docs/PRIVACY-AND-TRUST.md",
    "docs/TROUBLESHOOTING.md", "docs/UPGRADE.md", "docs/VERIFICATION.md",
)
LINK = re.compile(r"(!?)\[([^\]]*)\]\(([^)]+)\)")
HEADING = re.compile(r"^(#{1,6})\s+\S")
REQUIRED_FACTS = {
    "README.md": ("one plugin", "twenty-seven", "seventeen", "CC BY-ND 4.0", "nova-free-rights"),
    "START-HERE.md": ("one product and one plugin", "real invocation", "optional persistent state", "nova-free-rights"),
    "LICENSE.md": ("standard Collaborative Dynamics public-Augment split license", "MIT", "CC-BY-ND-4.0", "authentic, unmodified"),
    "ATTRIBUTION.md": ("Created by Sam Walker", "CC-BY-ND-4.0", "MIT"),
    "NOTICE.md": ("Permission and publication are different", "not a published release"),
    "TRADEMARKS.md": ("authentic, unmodified", "distinct identity"),
    "PROVENANCE.md": ("design/source-map.json", "design/source-lock.json", "separate source packages"),
    "THIRD-PARTY-NOTICES.md": ("Same-owner public-edition authorization", "permit public redistribution", "TestForge"),
    "docs/INSTALL-CLAUDE.md": ("nova-free-rights", "component notice packet"),
    "docs/MAINTAINER-GUIDE.md": ("rights bundle", "including untracked files", "separate user authority"),
    "docs/VERIFICATION.md": ("tools/build_release.py", "tools/verify_package.py", "does not establish", "nova-free-rights"),
}
FORBIDDEN_STALE_CLAIMS = (
    "blocked_pending_component_grants",
    "six included components still need",
    "six component-license matters remain",
    "must not be publicly redistributed",
    "hard redistribution blockers",
)


def local_reference_problem(source: Path, raw: str, repo: Path) -> str | None:
    value = raw.strip()
    if value.startswith("<") and ">" in value:
        value = value[1:value.index(">")]
    elif " " in value:
        value = value.split(" ", 1)[0]
    split = urlsplit(value)
    if split.scheme or split.netloc or value.startswith(("mailto:", "tel:", "#")):
        return None
    target = (source.parent / unquote(split.path)).resolve()
    try:
        target.relative_to(repo)
    except ValueError:
        return "reference leaves repository"
    if not target.exists():
        return f"target missing: {value}"
    return None


def inspect(repo: Path) -> dict[str, object]:
    findings: list[dict[str, object]] = []
    checked_links = 0
    for relative in MAINTAINED:
        path = repo / relative
        if not path.is_file():
            findings.append({"path": relative, "line": 0, "problem": "maintained document missing"})
            continue
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        if not lines or not lines[0].startswith("# "):
            findings.append({"path": relative, "line": 1, "problem": "document does not begin with one H1"})
        h1 = sum(1 for line in lines if line.startswith("# "))
        if h1 != 1:
            findings.append({"path": relative, "line": 0, "problem": f"expected one H1, found {h1}"})
        previous = 0
        fenced = False
        for number, line in enumerate(lines, 1):
            if line.rstrip() != line:
                findings.append({"path": relative, "line": number, "problem": "trailing whitespace"})
            if line.lstrip().startswith((chr(96) * 3, "~~~")):
                fenced = not fenced
            match = HEADING.match(line)
            if match and not fenced:
                level = len(match.group(1))
                if previous and level > previous + 1:
                    findings.append({"path": relative, "line": number, "problem": f"heading skips from H{previous} to H{level}"})
                previous = level
        if fenced:
            findings.append({"path": relative, "line": 0, "problem": "unclosed fenced code block"})
        for match in LINK.finditer(text):
            checked_links += 1
            if match.group(1) and not match.group(2).strip():
                findings.append({"path": relative, "line": text[:match.start()].count("\n") + 1, "problem": "image has empty alt text"})
            problem = local_reference_problem(path, match.group(3), repo)
            if problem:
                findings.append({"path": relative, "line": text[:match.start()].count("\n") + 1, "problem": problem})
        for phrase in REQUIRED_FACTS.get(relative, ()):
            if phrase.casefold() not in text.casefold():
                findings.append({"path": relative, "line": 0, "problem": f"required product boundary absent: {phrase}"})
        for phrase in FORBIDDEN_STALE_CLAIMS:
            if phrase.casefold() in text.casefold():
                findings.append({"path": relative, "line": 0, "problem": f"obsolete rights claim remains: {phrase}"})
    return {
        "schema": "nova-free-documentation-lint/v3",
        "maintained_documents": list(MAINTAINED),
        "documents_checked": len(MAINTAINED),
        "local_references_checked": checked_links,
        "findings": findings,
        "verdict": "PASS" if not findings else "FAIL",
        "evidence_boundary": "Markdown structure, selected semantic contracts, and source-tree local references only; not task usability, assistive-technology behavior, package extraction, or publication.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check maintained Nova Free documentation.")
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args()
    result = inspect(args.repo.resolve())
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    print(rendered)
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(rendered + "\n", encoding="utf-8", newline="\n")
    return 0 if result["verdict"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
