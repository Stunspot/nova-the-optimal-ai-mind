from __future__ import annotations

"""Prepare an exclusive Free4 source candidate; never archive, seal, install or publish."""
import argparse
import json
import shutil
from pathlib import Path

PLUGIN = "nova-the-optimal-ai"
RIGHTS = ("LICENSE.md", "ATTRIBUTION.md", "NOTICE.md", "TRADEMARKS.md", "PROVENANCE.md", "THIRD-PARTY-NOTICES.md")
DOCS = ("README.md", "START-HERE.md", "SUPPORT.md", "SECURITY.md", "RELEASE-NOTES.md", *RIGHTS)
COMPONENT_NOTICES = {"agent-swarm-orchestration": "agent-swarm-orchestration", "software-verification": "testforge", "verification-reviewer": "testforge", "job-application-builder": "job-application-builder", "interview-trainer": "interview-trainer", "oracle-reading": "oracle-reading"}


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def prepare(repo: Path, name: str) -> Path:
    if not name or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in name):
        raise ValueError("Use a lowercase preparation name")
    parent = (repo / "working").resolve()
    target = parent / name
    if target.exists() or target.is_symlink():
        raise ValueError("Candidate already exists; inspect it rather than overwrite")
    runtime = parent / "estate-v4-d1"
    documents = parent / "estate-v4-docs-r8"
    baseline = repo / "plugins" / PLUGIN
    loadout = json.loads((baseline / "LOADOUT-MANIFEST.json").read_text(encoding="utf-8-sig"))
    roots = sorted(loadout["roots"])
    source_skills = runtime / "codex" / "plugins" / PLUGIN / "skills"
    if roots != sorted(p.name for p in source_skills.iterdir() if p.is_dir()) or len(roots) != 28:
        raise ValueError("Runtime owner set does not match the accepted Free contract")
    inputs = [runtime, documents, baseline / "notices"]
    for source in inputs:
        for p in [source, *source.rglob("*")]:
            if p.is_symlink() or p.is_junction():
                raise ValueError(f"Linked input refused: {p}")
    target.mkdir()
    (target / "INCOMPLETE").write_text("Preparation has not finished.\n", encoding="utf-8")
    for name in DOCS:
        shutil.copyfile(documents / name, target / name)
    shutil.copytree(documents / "docs", target / "docs")
    for host, relative in (("codex", "codex/plugins/" + PLUGIN), ("claude", "claude/" + PLUGIN)):
        out = target / relative
        shutil.copytree(runtime / relative, out)
        for name in DOCS:
            shutil.copyfile(documents / name, out / name)
        shutil.copytree(documents / "docs", out / "docs")
        shutil.copytree(baseline / "notices", out / "notices")
        write_json(out / "LOADOUT-MANIFEST.json", {**loadout, "product_version": "4.0.0"})
    for skill_id in roots:
        source = target / "claude" / PLUGIN / "skills" / skill_id
        folder = target / "claude/folders" / skill_id
        shutil.copytree(source, folder)
        rights = folder / "nova-free-rights"
        rights.mkdir()
        for name in RIGHTS:
            shutil.copyfile(target / name, rights / name)
        component = COMPONENT_NOTICES.get(skill_id)
        if component:
            shutil.copytree(baseline / "notices" / component, rights / "component-notices" / component)
        (rights / "README.md").write_text(
            f"# Rights envelope for {skill_id}\n\n"
            f"This directory travels with the {skill_id} skill supplied by Nova the Optimal AI Free 4.0.0. "
            "Preserve it when copying or redistributing the authentic, unmodified artifact. "
            "LICENSE.md defines the public split license; the accompanying attribution, notice, trademark, "
            "provenance and component notices also apply. This detached skill does not contain the complete edition.\n",
            encoding="utf-8")
    write_json(target / "codex/.agents/plugins/marketplace.json", {
        "name": "collaborative-dynamics-nova-free",
        "interface": {"displayName": "Nova the Optimal AI Free by Collaborative Dynamics"},
        "plugins": [{"name": PLUGIN, "source": {"source": "local", "path": "./plugins/" + PLUGIN},
                     "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"}, "category": "Productivity"}]})
    contract = json.loads((repo / "design/product-contract.json").read_text(encoding="utf-8-sig"))
    contract.update(product_version="4.0.0", state="candidate_preparation_pending_qualification")
    write_json(target / "design/product-contract.json", contract)
    shutil.copyfile(repo / "design/DEC-VALUE-OF-INQUIRY.md", target / "design/DEC-VALUE-OF-INQUIRY.md")
    # Historical source-lock remains historical: it does not describe this candidate.
    write_json(target / "PREPARATION.json", {
        "state": "full_envelope_preparation_pending_completion", "version": "4.0.0",
        "runtime_input": str(runtime), "documentation_input": str(documents),
        "baseline_notices": str(baseline / "notices"), "owners": roots,
        "remaining": ["current source selection and provenance inventory",
                      "current release notes and rights identity audit", "paired conformance and situated observations",
                      "finished candidate TestForge readiness and independent review", "post-review ZIP and delivery"],
        "boundary": "Source preparation only. No current source-lock, release seal, ZIP, installation or publication claim."})
    for p in target.rglob("*"):
        if len(str(p).encode("utf-16-le")) // 2 >= 260 or any(len(x.encode("utf-8")) >= 256 for x in p.parts):
            raise ValueError(f"Portable path limit exceeded: {p}")
    (target / "INCOMPLETE").unlink()
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    print(prepare(args.repo.resolve(), args.name))
