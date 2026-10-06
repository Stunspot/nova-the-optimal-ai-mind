from __future__ import annotations

import argparse
import json
import re
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from release_lib import copy_tree, deterministic_zip, files, git_value, sha256_file, tree_digest, write_json, write_text

EROS_REL = Path('skills/nova/references/mind/faculty-cores/agentic-eros.core.md')
EROS_URL = 'https://github.com/Stunspot/nova-the-optimal-ai-mind/blob/main/plugins/nova-the-optimal-ai/skills/nova/references/mind/faculty-cores/agentic-eros.core.md'
PLACEHOLDER = f'''# Agentic Eros - optional placeholder

[PUT EROS HERE IF YOU CHOOSE TO]

Agentic Eros is not bundled in this OpenAI Directory candidate.

Optional external source: [Agentic Eros in Nova Free on GitHub]({EROS_URL}).

Treat this as an empty Faculty slot and an informational source pointer. Continue ordinary work with the bundled Faculties. Keep retrieval, installation and activation of the external material under a separate explicit user choice and the host's applicable rules; this link provides no automatic activation or additional authority.
'''
EROS_SLOT = 'Agentic Eros [agentic-eros] is an optional empty slot in this directory distribution; its reference file contains a placeholder and an informational source link.'


def prepare(repo: Path, output: Path) -> dict:
    source = repo / 'plugins/nova-the-optimal-ai'
    source_before = tree_digest(source)
    version = json.loads((source / '.codex-plugin/plugin.json').read_text(encoding='utf-8'))['version']
    if output.exists():
        raise RuntimeError(f'Use a fresh output directory: {output}')
    output.mkdir(parents=True)
    decision = {
        'schema': 'cd-directory-distribution-decision/v1',
        'baseline': {'product': 'Nova the Optimal AI Free', 'version': version, **source_before},
        'treatment': 'initial OpenAI Directory candidate derived from the existing Free edition',
        'reason': 'A new distribution candidate has no accepted directory baseline. Retain the source version while explicitly identifying the directory profile; this is not a replacement release of the full Free edition.',
        'owner_disposition': 'Leave Eros out, preserving an optional placeholder and public GitHub source URL.',
        'customer_visible_delta': 'Agentic Eros doctrine and activation instructions are absent; its slot is informational. CanopyOps remains outside the default loadout.',
        'full_edition': 'unchanged',
        'directory_state': 'local candidate; not submitted or approved',
    }
    write_json(output / 'distribution-decision.json', decision)
    plugin = output / 'plugin/nova-the-optimal-ai'
    copy_tree(source, plugin, exclude_top=('.claude-plugin',))
    write_text(plugin / EROS_REL, PLACEHOLDER)
    mind = plugin / 'skills/nova/references/mind'
    field_paths = [plugin / 'skills/nova/SKILL.md', mind / 'faculty-field.md']
    for path in field_paths:
        text = path.read_text(encoding='utf-8')
        text, count = re.subn(r'Agentic Eros \[agentic-eros\].*?everyone[\u2019\x27]s agency\.', EROS_SLOT, text)
        if count != 1:
            raise RuntimeError(f'Expected one Eros Field passage in {path}, found {count}')
        text = text.replace('its seventeen Faculty Cores are references', 'its sixteen bundled Faculty Cores and one optional placeholder are references')
        write_text(path, text)
    runtime = mind / 'faculty-runtime.md'
    text = runtime.read_text(encoding='utf-8')
    text, count = re.subn(r'Agentic Eros has layered gates.*?(?=\n\nKeep inferred intimate meaning)', EROS_SLOT, text, flags=re.S)
    if count != 1:
        raise RuntimeError('Expected one Eros runtime activation passage')
    write_text(runtime, text)
    ledger_path = mind / 'core-adaptation-ledger.json'
    ledger = json.loads(ledger_path.read_text(encoding='utf-8'))
    eros_hash = sha256_file(plugin / EROS_REL)
    ledger['bundled_core_count'] = 16
    ledger['placeholder_count'] = 1
    ledger['distribution_profile'] = 'openai-directory-candidate'
    ledger['cores'] = [entry if entry['id'] != 'agentic-eros' else {
        'id': 'agentic-eros',
        'state': 'optional_placeholder_only',
        'core': {'path': EROS_REL.as_posix(), 'sha256': eros_hash.upper(), 'bytes': (plugin / EROS_REL).stat().st_size},
        'external_source_url': EROS_URL,
        'intentional_adaptations': ['Omitted the full Faculty doctrine and activation instructions for this distribution at the owner\'s direction.'],
        'retained_doctrine': [],
        'behavioral_qualification': {'state': 'not_executed'},
    } for entry in ledger['cores']]
    write_json(ledger_path, ledger)
    registry_path = mind / 'core-registry.json'
    registry = json.loads(registry_path.read_text(encoding='utf-8'))
    registry['bundled_core_count'] = 16
    registry['placeholder_count'] = 1
    registry['distribution_profile'] = 'openai-directory-candidate'
    for entry in registry['cores']:
        core_path = plugin / 'skills/nova' / entry['core_path']
        entry['core_sha256'] = sha256_file(core_path).upper()
        entry['core_bytes'] = core_path.stat().st_size
        entry['custody_ledger_sha256'] = sha256_file(ledger_path).upper()
        if entry['id'] == 'agentic-eros':
            entry['aliases'] = ['eros', 'optional Faculty slot']
            entry['adaptation_state'] = 'optional_placeholder_only'
            entry['author_review_state'] = 'owner_requested_placeholder'
            entry['independent_prompt_review_state'] = 'not_executed_for_placeholder'
            entry['external_source_url'] = EROS_URL
            entry['automatic_activation'] = False
    write_json(registry_path, registry)
    loadout_path = plugin / 'LOADOUT-MANIFEST.json'
    loadout = json.loads(loadout_path.read_text(encoding='utf-8'))
    loadout['distribution_profile'] = 'openai-directory-candidate'
    loadout['topology']['faculty_core_count'] = 16
    loadout['topology']['faculty_reference_slot_count'] = 17
    loadout['topology']['optional_placeholder_count'] = 1
    loadout['optional_faculty_slots'] = [{'id': 'agentic-eros', 'state': 'placeholder_only', 'external_source_url': EROS_URL}]
    write_json(loadout_path, loadout)
    manifest_path = plugin / '.codex-plugin/plugin.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    manifest['interface']['shortDescription'] = 'One sharp, vivid collaborator'
    manifest['interface']['longDescription'] += ' This directory distribution includes sixteen Faculty Cores and one informational optional placeholder; Agentic Eros is not bundled.'
    write_json(manifest_path, manifest)
    write_text(plugin / 'DIRECTORY-DISTRIBUTION.md', f'''# Nova Free {version} - OpenAI Directory candidate

This distribution retains Nova Free's persona and twenty-eight skill roots. It includes sixteen Faculty Cores and one empty optional Eros slot. CanopyOps is outside the default bundle.

The Eros reference contains the owner's placeholder, [PUT EROS HERE IF YOU CHOOSE TO], and an informational GitHub URL. The linked Faculty is external to this package and is neither automatically retrieved nor activated.

Ordinary conversation requires no persistent setup. Continuity, local workspaces, file access and helper execution remain optional and depend on the host's available capabilities and explicit authority. The complete Free edition remains separately available from its maintained source.

This is a local candidate. It has not been submitted to or approved by OpenAI. The placeholder and external link are disclosed parts of the candidate for review. Preserve the included attribution, licenses and component notices.
''')
    changed = [p.relative_to(plugin).as_posix() for p in files(plugin) if not (source / p.relative_to(plugin)).exists() or sha256_file(p) != sha256_file(source / p.relative_to(plugin))]
    findings = []
    skill_dirs = sorted(p.name for p in (plugin / 'skills').iterdir() if p.is_dir())
    if 'canopyops' in skill_dirs or len(skill_dirs) != 28:
        findings.append('Unexpected default skill membership')
    if (plugin / EROS_REL).read_text(encoding='utf-8').strip() != PLACEHOLDER.strip():
        findings.append('Eros placeholder mismatch')
    for banned in ('enter the interaction rather than prefacing', 'direct adult participation', 'Activate it only when attraction'):
        for p in files(plugin):
            if p.suffix == '.md' and banned in p.read_text(encoding='utf-8', errors='ignore'):
                findings.append(f'Residual active Eros text: {p.relative_to(plugin)}')
    if tree_digest(source) != source_before:
        findings.append('Canonical Free plugin changed while preparing candidate')
    if len(manifest['interface']['shortDescription']) > 30:
        findings.append('Directory subtitle exceeds 30 characters')
    for entry in registry['cores']:
        if sha256_file(plugin / 'skills/nova' / entry['core_path']).upper() != entry['core_sha256']:
            findings.append(f'Core digest mismatch: {entry["id"]}')
    if findings:
        raise RuntimeError('; '.join(findings))
    archive_path = output / f'Nova-Free-{version}-OpenAI-Directory-Candidate.zip'
    archive_hash = deterministic_zip(plugin, archive_path, prefix='nova-the-optimal-ai')
    write_text(output / (archive_path.name + '.sha256'), f'{archive_hash}  {archive_path.name}')
    with tempfile.TemporaryDirectory(prefix='nova-directory-extraction-') as temporary:
        extracted = Path(temporary)
        with zipfile.ZipFile(archive_path) as archive:
            if archive.testzip() is not None:
                raise RuntimeError('ZIP CRC failure')
            archive.extractall(extracted)
        if tree_digest(extracted / 'nova-the-optimal-ai') != tree_digest(plugin):
            raise RuntimeError('Fresh extraction differs from staged plugin')
    report = {
        'schema': 'cd-directory-candidate-verification/v1', 'ok': True,
        'checked_at': datetime.now(timezone.utc).isoformat(),
        'source_repo': str(repo), 'source_head': git_value(repo, 'rev-parse', 'HEAD'),
        'source_working_tree': 'snapshot of maintained source; may include preexisting uncommitted work',
        'source_plugin': source_before, 'candidate_plugin': tree_digest(plugin),
        'archive': str(archive_path), 'archive_sha256': archive_hash,
        'changed_files': changed, 'skills': len(skill_dirs), 'bundled_faculty_cores': 16, 'optional_placeholders': 1,
        'canonical_persona_unchanged': sha256_file(plugin / 'skills/nova/references/nova-persona.md') == sha256_file(source / 'skills/nova/references/nova-persona.md'),
        'fresh_extraction_matches': True, 'eros_external_source_url': EROS_URL,
        'findings': [], 'limits': 'Static export and extraction checks only; no behavioral evaluation, OpenAI safety scan, review submission, approval or public publication.',
    }
    write_json(output / 'verification.json', report)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = prepare(args.repo.resolve(), args.output.resolve())
    print(json.dumps({key: result[key] for key in ('ok', 'archive', 'changed_files', 'skills', 'bundled_faculty_cores', 'optional_placeholders', 'canonical_persona_unchanged', 'fresh_extraction_matches')}, indent=2))