"""One-use finalization for Nova + MIND Free 2.0.3 public release content."""

from __future__ import annotations

from pathlib import Path


RELEASE_URL = "https://github.com/Stunspot/nova-the-optimal-ai-mind/releases/latest"
SOURCE_URL = "https://github.com/Stunspot/nova-the-optimal-ai-mind/archive/refs/heads/main.zip"
ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8", newline="\n")


def converge(path: str, old: str, new: str) -> None:
    text = read(path)
    if old in text:
        write(path, text.replace(old, new))
    elif new not in text:
        raise RuntimeError(f"cannot converge {path}: neither expected form is present")


def finalize_customer_docs() -> None:
    converge(
        "README.md",
        f"[Download the current Nova + MIND Free source package]({SOURCE_URL})",
        f"[Download Nova + MIND Free]({RELEASE_URL})",
    )
    converge(
        "README.md",
        "1. Download the current Nova + MIND Free source package ZIP.",
        "1. Download the latest Nova + MIND Free ZIP.",
    )
    converge(
        "README.md",
        "The source package includes each portable skill as a self-contained folder; the release builder can also produce per-skill ZIPs for Claude-compatible hosts.",
        "The release also includes portable per-skill ZIPs for Claude-compatible skill hosts.",
    )

    converge(
        "START-HERE.md",
        f"[Download the current Nova + MIND Free source package ZIP]({SOURCE_URL})",
        f"[Download the latest Nova + MIND Free ZIP]({RELEASE_URL})",
    )
    converge(
        "START-HERE.md",
        "Extract the source package ZIP and use the included `install.ps1`",
        "Extract the release ZIP and use the included `install.ps1`",
    )

    page = read("docs/index.html")
    page = page.replace(SOURCE_URL, RELEASE_URL)
    page = page.replace("Portable skill sources included", "Portable skill packages included")
    page = page.replace(
        "The source package carries each skill as a self-contained folder; generated releases can package them individually for Claude-compatible hosts.",
        "The ZIP also carries portable per-skill packages for Claude-compatible hosts.",
    )
    write("docs/index.html", page)

    write(
        "docs/INSTALL-CLAUDE.md",
        """# Use Nova skills in a Claude-compatible harness

Nova + MIND Free is integrated and verified primarily as a Codex package. The release also contains one portable ZIP for each included skill under `claude/zips/`.

## Install a portable skill

Give the skill ZIP to the harness and ask it to install and enable the skill. If the host has a dedicated skill-management interface, uploading the ZIP there is equivalent. Start a new conversation after installation so the host can discover it.

Each ZIP has one matching top-level folder with its `SKILL.md` and required local resources.

## Recreating more of Nova

You may install Nova, the MIND integrator, its sixteen Faculties, Capability Promotion, both TestForge skills, Promptcraft, and whichever specialists you want. The individual packages preserve their own contents, but this release does not claim that a Claude-compatible host reproduces Codex's shared MIND database, prompt hook, automatic capability reminders, or fully integrated Nova-with-MIND behavior.

In other words: the skills are portable; the complete cognitive runtime remains Codex-first until an equivalent host integration is exercised.

## If a ZIP is rejected

Preserve the host's error. Confirm that the archive contains one matching top-level folder and a direct `SKILL.md`. A structurally correct skill ZIP can still be declined by a host policy or version; those are different failures.
""",
    )


def finalize_release_state() -> None:
    converge(
        "design/FREE-NOVA-PACKAGE-MAP.md",
        "Status: published source package; 2.0.3 runtime correction",
        "Status: published product; 2.0.3 runtime correction",
    )
    converge(
        "RELEASE-NOTES.md",
        "This corrective source revision removes Nova and MIND's bundled MCP server",
        "This corrective release removes Nova and MIND's bundled MCP server",
    )

    verifier = read("tools/verify_package.py")
    old_check = '''    source_zip = "https://github.com/Stunspot/nova-the-optimal-ai-mind/archive/refs/heads/main.zip"
    for download_surface in (ROOT / "README.md", ROOT / "START-HERE.md", ROOT / "docs" / "index.html"):
        if source_zip not in download_surface.read_text(encoding="utf-8"):
            errors.append(f"current source-package download is missing: {download_surface.relative_to(ROOT)}")
'''
    new_check = '''    release_url = "https://github.com/Stunspot/nova-the-optimal-ai-mind/releases/latest"
    for download_surface in (ROOT / "README.md", ROOT / "START-HERE.md", ROOT / "docs" / "index.html"):
        if release_url not in download_surface.read_text(encoding="utf-8"):
            errors.append(f"current release download is missing: {download_surface.relative_to(ROOT)}")
'''
    if old_check in verifier:
        verifier = verifier.replace(old_check, new_check, 1)
    elif new_check not in verifier:
        raise RuntimeError("download-surface verifier block not found")
    write("tools/verify_package.py", verifier)


def remove_nonworkflow_machinery() -> None:
    for relative in (
        ".github/PUBLIC-RELEASE-WORKFLOW.md",
        ".github/FINAL-PUBLIC-DOCS-JOB.md",
        ".github/FINALIZE-PUBLIC-DOCS.md",
    ):
        target = ROOT / relative
        if target.exists():
            target.unlink()

    Path(__file__).unlink()


def main() -> int:
    finalize_customer_docs()
    finalize_release_state()
    remove_nonworkflow_machinery()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
