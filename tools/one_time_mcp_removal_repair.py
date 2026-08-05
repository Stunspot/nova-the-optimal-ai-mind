"""One-use repository repair for the Nova + MIND MCP-removal correction.

This file is installed temporarily, executed only against the dedicated repair
branch, and removed after the verified repair is merged.
"""

from __future__ import annotations

from pathlib import Path


SOURCE_ZIP = (
    "https://github.com/Stunspot/nova-the-optimal-ai-mind/"
    "archive/refs/heads/main.zip"
)


def read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    Path(path).write_text(text, encoding="utf-8", newline="\n")


def replace(path: str, old: str, new: str, *, count: int = -1) -> None:
    text = read(path)
    if old not in text:
        raise RuntimeError(f"missing expected text in {path}: {old!r}")
    write(path, text.replace(old, new, count))


def remove(path: str, text_to_remove: str) -> None:
    replace(path, text_to_remove, "")


def repair_versions() -> None:
    replace(
        "plugins/augment-of-mind/scripts/verify_release.py",
        'PLUGIN_VERSION = "2.1.0"',
        'PLUGIN_VERSION = "2.1.1"',
    )
    replace(
        "plugins/augment-of-mind/scripts/build_integrated_fingerprint.py",
        '"augment-of-mind":"2.1.0"',
        '"augment-of-mind":"2.1.1"',
    )
    replace(
        "plugins/augment-of-mind/scripts/build_integrated_fingerprint.py",
        '"product_version":"2.1.0"',
        '"product_version":"2.1.1"',
    )
    replace(
        "plugins/augment-of-mind/skills/augment-of-mind/evals/eval-manifest.yaml",
        '"package_version": "2.1.0"',
        '"package_version": "2.1.1"',
    )
    replace(
        "plugins/augment-of-mind/skills/augment-of-mind/evals/faculty-runtime-cases.yaml",
        '"package_version": "2.1.0"',
        '"package_version": "2.1.1"',
    )
    replace(
        "plugins/augment-of-mind/skills/augment-of-mind/"
        "references/faculty-runtime/faculty-registry.json",
        '"runtime_version": "2.1.0"',
        '"runtime_version": "2.1.1"',
    )
    replace(
        "plugins/augment-of-mind/install.ps1",
        "MIND 2.1 is installed",
        "MIND 2.1.1 is installed",
    )


def repair_hook_and_fixture() -> None:
    old = (
        '        "the host\'s normal skill-discovery and filesystem '
        'skill-loading paths. "\n'
        '        "Skills are not MCP resources; do not call MCP tools or '
        'resource readers."\n'
    )
    new = (
        '        "the host\'s normal skill-discovery and filesystem '
        'skill-loading paths. "\n'
        '        "Do not treat the unavailable reminder field as evidence '
        'that installed "\n'
        '        "skills are absent."\n'
    )
    replace("plugins/augment-of-mind/hooks/mind_prompt_submit.py", old, new)
    replace(
        "verification/associative-smoke/hook-contextual.json",
        "Skills are not MCP resources; do not call MCP tools or resource readers.",
        "Do not treat the unavailable reminder field as evidence that installed "
        "skills are absent.",
    )


def repair_active_mind_docs() -> None:
    remove(
        "plugins/augment-of-mind/OPTIONAL-CORE.md",
        "MIND does not register or require an MCP server. Skills remain ordinary\n"
        "filesystem capabilities discovered and loaded by the host.\n\n",
    )
    remove(
        "plugins/augment-of-mind/PACKAGE-REFERENCE.md",
        "MIND does not register or require MCP. Skills are loaded through the "
        "host's ordinary filesystem skill mechanism.\n\n",
    )
    replace(
        "plugins/augment-of-mind/SECURITY.md",
        "Security reports currently cover the latest published MIND `1.0.x` "
        "release\nand the bundled MIND Core `0.2.x` component.",
        "Security reports currently cover the MIND `2.1.x` source line and "
        "the\nbundled MIND Core `0.2.x` component.",
    )
    replace(
        "plugins/augment-of-mind/SECURITY.md",
        "MIND does not register or require an MCP server. Skills are loaded "
        "through the\nhost's ordinary filesystem skill mechanism and are never "
        "exposed as MCP\nresources.\n\n",
        "Skills are filesystem entrypoints discovered by the host. Core's direct "
        "Python\nAPI, CLI, and framed query path do not grant host permissions.\n\n",
    )

    notes_path = "plugins/augment-of-mind/RELEASE-NOTES.md"
    notes = read(notes_path)
    if "## 2.1.1" not in notes:
        section = (
            "## 2.1.1\n\n"
            "This corrective source revision removes the bundled MCP registration, "
            "launcher, server implementation, and automatic MCP-tool request from "
            "MIND's default package. Filesystem skills, the prompt-submit hook, and "
            "the direct local association library and CLI remain available.\n\n"
            "It also synchronizes the plugin manifest, standalone builder and "
            "verifier, evaluation metadata, Faculty registry, and integrated "
            "capability fingerprint.\n\n"
        )
        write(notes_path, notes.replace("## 2.1.0\n", section + "## 2.1.0\n", 1))

    replace(
        "plugins/augment-of-mind/INSTALL-CODEX.md",
        "hook and reminder service",
        "hook and direct local query runtime",
    )
    replace(
        "plugins/augment-of-mind/HOST-COMPATIBILITY.md",
        "local contextual reminder service",
        "local contextual reminder runtime",
    )
    replace(
        "plugins/augment-of-mind/HOST-COMPATIBILITY.md",
        "MIND’s local reminder service",
        "MIND’s local reminder runtime",
    )
    replace(
        "plugins/augment-of-mind/DATA-AND-PRIVACY.md",
        "a local reminder service",
        "a local reminder runtime",
    )
    replace(
        "plugins/augment-of-mind/TROUBLESHOOTING.md",
        "prompt hook or reminder service",
        "prompt hook or reminder runtime",
    )
    replace(
        "plugins/augment-of-mind/TROUBLESHOOTING.md",
        "local reminder service",
        "local reminder runtime",
    )


def repair_root_docs_and_pages() -> None:
    replace(
        "RELEASE-NOTES.md",
        "This corrective release removes Nova and MIND's bundled MCP server, "
        "registration, launcher, and automatic MCP-tool invocation. The bundled "
        "skills remain ordinary filesystem capabilities loaded through their "
        "`SKILL.md` entrypoints, while the prompt hook and local query path continue "
        "to support Arm's Reach association without an MCP dependency.\n\n"
        "The change fixes a failure mode where models attempted to load installed "
        "skills as MCP resources, repeatedly retried unavailable servers, compacted "
        "around the false dependency, and stopped useful work. This package imposes "
        "no restriction on unrelated MCP servers a user configures independently.",
        "This corrective source revision removes Nova and MIND's bundled MCP server, "
        "registration, launcher, and automatic MCP-tool invocation. The bundled "
        "skills remain filesystem capabilities loaded through their `SKILL.md` "
        "entrypoints, while the prompt hook and direct local query path continue to "
        "support Arm's Reach association.\n\n"
        "The change fixes a failure mode where models attempted to load installed "
        "skills as MCP resources, repeatedly retried unavailable servers, compacted "
        "around the false dependency, and stopped useful work.",
    )

    package_map_path = "design/FREE-NOVA-PACKAGE-MAP.md"
    package_map = read(package_map_path)
    package_map = package_map.replace(
        "Status: published product; 2.0.2 presentation correction in progress",
        "Status: published source package; 2.0.3 runtime correction",
    ).replace(
        "Product: **Nova + MIND Free 2.0.2**",
        "Product: **Nova + MIND Free 2.0.3**",
    ).replace(
        "Canonical repository: `Stunspot/nova-the-optimal-ai`",
        "Canonical repository: `Stunspot/nova-the-optimal-ai-mind`",
    ).replace(
        "MIND does not register or require an MCP server. Skills are host-discovered "
        "filesystem capabilities with `SKILL.md` entrypoints.\n\n",
        "",
    )
    write(package_map_path, package_map)

    replace(
        "docs/PRIVACY-AND-TRUST.md",
        "hook and association-service code",
        "hook and direct local association code",
    )
    replace(
        "docs/PRIVACY-AND-TRUST.md",
        "installer, hook, and reminder service",
        "installer, hook, and direct local query runtime",
    )
    replace(
        "docs/INSTALL-CODEX.md",
        "hook and reminder service",
        "hook and direct local query runtime",
    )

    replace(
        "README.md",
        "[Download Nova + MIND Free](https://github.com/Stunspot/"
        "nova-the-optimal-ai-mind/releases/latest)",
        f"[Download the current Nova + MIND Free source package]({SOURCE_ZIP})",
    )
    replace(
        "README.md",
        "1. Download the latest Nova + MIND Free ZIP.",
        "1. Download the current Nova + MIND Free source package ZIP.",
    )
    replace(
        "README.md",
        "The package also includes portable per-skill ZIPs for Claude-compatible "
        "skill hosts.",
        "The source package includes each portable skill as a self-contained folder; "
        "the release builder can also produce per-skill ZIPs for Claude-compatible "
        "hosts.",
    )
    replace(
        "START-HERE.md",
        "[Download the latest Nova + MIND Free ZIP](https://github.com/Stunspot/"
        "nova-the-optimal-ai-mind/releases/latest)",
        f"[Download the current Nova + MIND Free source package ZIP]({SOURCE_ZIP})",
    )
    replace(
        "START-HERE.md",
        "Extract the ZIP and use the included `install.ps1`",
        "Extract the source package ZIP and use the included `install.ps1`",
    )

    page_path = "docs/index.html"
    page = read(page_path)
    page = page.replace(
        "https://github.com/Stunspot/nova-the-optimal-ai-mind/releases/latest",
        SOURCE_ZIP,
    ).replace(
        "Portable skill packages included",
        "Portable skill sources included",
    ).replace(
        "The ZIP also carries portable per-skill packages for Claude-compatible "
        "hosts.",
        "The source package carries each skill as a self-contained folder; generated "
        "releases can package them individually for Claude-compatible hosts.",
    )
    write(page_path, page)

    write(
        "docs/INSTALL-CLAUDE.md",
        """# Use Nova skills in a Claude-compatible harness

Nova + MIND Free is integrated and verified primarily as a Codex package. The current repository ZIP contains each included skill as a self-contained source folder under `plugins/*/skills/`.

## Install a portable skill

Select the skill folder you need and package that folder as a ZIP whose single top-level directory has the same name and contains a direct `SKILL.md`. Give that ZIP to the harness and ask it to install and enable the skill. If the host accepts folders directly, the source folder is equivalent.

Maintainers can run `python -X utf8 tools/build_release.py` to produce prebuilt per-skill archives under `dist/claude/zips/`.

## Recreating more of Nova

You may install Nova, the MIND integrator, its sixteen Faculties, Capability Promotion, both TestForge skills, Promptcraft, and whichever specialists you want. The individual packages preserve their own contents, but this source revision does not claim that a Claude-compatible host reproduces Codex's shared MIND database, prompt hook, automatic capability reminders, or fully integrated Nova-with-MIND behavior.

In other words: the skills are portable; the complete cognitive runtime remains Codex-first until an equivalent host integration is exercised.

## If a ZIP is rejected

Preserve the host's error. Confirm that the archive contains one matching top-level folder and a direct `SKILL.md`. A structurally correct skill ZIP can still be declined by a host policy or version; those are different failures.
""",
    )

    replace(
        "docs/VERIFICATION.md",
        "The release verifier checks the expected skill set, unique handles, metadata, "
        "Nova and Promptcraft source integrity, TestForge inclusion, release exclusions, "
        "plugin topology, reminder assets, customer links, and portable Claude ZIP "
        "shape.",
        "The release verifier checks the expected skill set, unique handles, metadata, "
        "Nova and Promptcraft source integrity, TestForge inclusion, release exclusions, "
        "plugin topology, reminder assets, customer links, portable Claude ZIP shape, "
        "MIND version consistency, integrated fingerprint integrity, and absence of "
        "removed runtime paths.",
    )
    replace(
        "docs/MAINTAINER-GUIDE.md",
        "Inspect the release manifest, checksums, final customer ZIP, representative "
        "Claude archives, public Pages, and the canonical artwork.",
        "Keep the MIND plugin manifest, standalone builder and verifier, evaluation "
        "metadata, Faculty registry, release notes, and integrated fingerprint "
        "synchronized. Inspect the release manifest, checksums, final customer ZIP, "
        "representative Claude archives, public Pages, and the canonical artwork.",
    )


def strengthen_verifier() -> None:
    path = "tools/verify_package.py"
    verifier = read(path)
    verifier = verifier.replace(
        "import hashlib\n", "import hashlib\nimport importlib.util\n", 1
    )
    anchor = '''    if mind_manifest.get("version") != "2.1.1":
        errors.append("MIND plugin version must be 2.1.1")

'''
    if anchor not in verifier:
        raise RuntimeError("tools/verify_package.py version anchor not found")
    block = '''    mind_version = str(mind_manifest.get("version", ""))
    if "mcpServers" in mind_manifest:
        errors.append("MIND plugin manifest still registers an MCP server")
    for removed_path in (
        MIND / ".mcp.json",
        MIND / "mind_core" / "mcp_server.py",
        MIND / "scripts" / "mind_mcp_server.py",
    ):
        if removed_path.exists():
            errors.append(f"removed MIND runtime path still exists: {removed_path.relative_to(ROOT)}")

    standalone_verifier_text = (MIND / "scripts" / "verify_release.py").read_text(encoding="utf-8")
    standalone_version = re.search(r'(?m)^PLUGIN_VERSION = "([^"]+)"$', standalone_verifier_text)
    if not standalone_version or standalone_version.group(1) != mind_version:
        errors.append("standalone MIND release verifier version does not match the plugin manifest")

    eval_manifest = load_json(MIND / "skills" / "augment-of-mind" / "evals" / "eval-manifest.yaml")
    eval_cases = load_json(MIND / "skills" / "augment-of-mind" / "evals" / "faculty-runtime-cases.yaml")
    registry = load_json(MIND / "skills" / "augment-of-mind" / "references" / "faculty-runtime" / "faculty-registry.json")
    if eval_manifest.get("package_version") != mind_version or eval_cases.get("package_version") != mind_version:
        errors.append("MIND evaluation metadata does not match the plugin version")
    if registry.get("runtime_version") != mind_version:
        errors.append("MIND Faculty registry version does not match the plugin version")

    fingerprint_path = MIND / "skills" / "augment-of-mind" / "assets" / "integrated-capability-fingerprint.json"
    fingerprint_builder_path = MIND / "scripts" / "build_integrated_fingerprint.py"
    spec = importlib.util.spec_from_file_location("mind_integrated_fingerprint", fingerprint_builder_path)
    if spec is None or spec.loader is None:
        errors.append("cannot load the integrated fingerprint builder")
    else:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        observed_fingerprint = load_json(fingerprint_path)
        expected_fingerprint = module.build()
        if observed_fingerprint != expected_fingerprint:
            errors.append("integrated MIND capability fingerprint is stale")
        if observed_fingerprint.get("product_version") != mind_version:
            errors.append("integrated MIND fingerprint version does not match the plugin version")

    hook_text = (MIND / "hooks" / "mind_prompt_submit.py").read_text(encoding="utf-8")
    for forbidden_hook_phrase in (
        "do not call MCP tools or resource readers",
        "read_mcp_resource",
        "associate_capabilities",
    ):
        if forbidden_hook_phrase in hook_text:
            errors.append(f"obsolete MCP routing instruction remains in the MIND hook: {forbidden_hook_phrase}")

    source_zip = "https://github.com/Stunspot/nova-the-optimal-ai-mind/archive/refs/heads/main.zip"
    for download_surface in (ROOT / "README.md", ROOT / "START-HERE.md", ROOT / "docs" / "index.html"):
        if source_zip not in download_surface.read_text(encoding="utf-8"):
            errors.append(f"current source-package download is missing: {download_surface.relative_to(ROOT)}")

    package_map_text = (ROOT / "design" / "FREE-NOVA-PACKAGE-MAP.md").read_text(encoding="utf-8")
    if "Product: **Nova + MIND Free 2.0.3**" not in package_map_text:
        errors.append("Free Nova package map version is stale")
    if "Canonical repository: `Stunspot/nova-the-optimal-ai-mind`" not in package_map_text:
        errors.append("Free Nova package map points at the wrong canonical repository")

    stale_customer_phrases = {
        ROOT / "docs" / "PRIVACY-AND-TRUST.md": ("association-service code", "reminder service"),
        ROOT / "docs" / "INSTALL-CODEX.md": ("reminder service",),
        MIND / "INSTALL-CODEX.md": ("reminder service",),
        MIND / "HOST-COMPATIBILITY.md": ("reminder service",),
        MIND / "DATA-AND-PRIVACY.md": ("reminder service",),
        MIND / "TROUBLESHOOTING.md": ("reminder service",),
    }
    for document, phrases in stale_customer_phrases.items():
        text = document.read_text(encoding="utf-8")
        for phrase in phrases:
            if phrase in text:
                errors.append(f"stale architecture phrase remains in {document.relative_to(ROOT)}: {phrase}")

'''
    write(path, verifier.replace(anchor, anchor + block, 1))


def main() -> int:
    repair_versions()
    repair_hook_and_fixture()
    repair_active_mind_docs()
    repair_root_docs_and_pages()
    strengthen_verifier()
    trigger = Path(".github/repair-trigger.txt")
    if trigger.exists():
        trigger.unlink()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
