#!/usr/bin/env python3
"""Verify current Omnara product dependencies and exact packaged bytes."""
from __future__ import annotations
import argparse,hashlib,json,re,sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote,urlsplit
from custody import reject_links,namespace
from product_files import inventory,TOP,DIRECTORIES
from evidence_contract import loads
EXPECTED_HASHES={'references/canonical/inquiry-engine-v1.md':'351183c36a1d14b1fa28b1ddce9d0ad0437ecf627cff90150f4acbb02928afd0'}
RUNTIME_REQUIRED=['SKILL.md','VERSION','Open.cmd','Open.command','agents/openai.yaml','personas/omnara-investigative-research-intelligence.md','references/operating-doctrine.md','references/review-contract.md','references/research-design-and-idea-development.md','references/research-to-manuscript.md','references/canonical/inquiry-engine-v1.md','assets/campaign-vault/campaign.json','scripts/research_campaign.py','scripts/citation_audit.py','scripts/assemble_report.py','scripts/evidence_contract.py','scripts/custody.py','scripts/file_ops.py','scripts/product_files.py','scripts/validate_release.py','workspace/open.py','workspace/create_entry.py','workspace/assets/omnara.ico','workspace/assets/omnara.icns','workspace/assets/omnara-icon.png','workspace/runtime.py','workspace/campaign.py','workspace/index.html','workspace/app.js','workspace/style.css','workspace/skins.css','workspace/assets/tracework.png','workspace/assets/survey-folio.png','workspace/assets/proof-cabinet.png']
SOURCE_REQUIRED=sorted(set(RUNTIME_REQUIRED+list(TOP)+['docs/INSTALLATION.md','docs/VALIDATION.md','docs/CAMPAIGN-ROOM.md','examples/README.md','examples/sea-level-comparison/report.md','verification/documentation-review.md']))

class HTML(HTMLParser):
    def __init__(self):super().__init__();self.targets=[];self.ids=set()
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if attrs.get('id'):self.ids.add(attrs['id'])
        for key in ['href','src']:
            if key in attrs:self.targets.append(attrs[key])

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def links(root,files):
    errors=[];checked=0
    for file in files:
        if file.suffix not in {'.md','.html'}:continue
        content=file.read_text(encoding='utf-8')
        if file.suffix=='.html':parser=HTML();parser.feed(content);targets=parser.targets
        else:
            targets=[]
            for match in re.finditer(r'!?\[[^\]]*\]\(([^)]+)\)',content):
                value=match.group(1).strip();targets.append(value[1:value.index('>')] if value.startswith('<') and '>' in value else value.split(' ',1)[0])
        for value in targets:
            parts=urlsplit(value)
            if parts.scheme or parts.netloc or not parts.path:continue
            target=reject_links(file.parent/unquote(parts.path))
            if not target.is_relative_to(root):errors.append(f'local link escapes product: {file.relative_to(root)} -> {value}');continue
            checked+=1
            if not target.exists():errors.append(f'broken local link: {file.relative_to(root)} -> {value}')
            elif parts.fragment and target.suffix=='.html':
                parser=HTML();parser.feed(target.read_text(encoding='utf-8'))
                if unquote(parts.fragment) not in parser.ids:errors.append(f'missing HTML anchor: {file.relative_to(root)} -> {value}')
    return errors,checked

def validate(root,profile='auto'):
    errors=[];count=0;profile='source' if profile=='auto' else profile
    try:
        root=reject_links(root)
        if not root.is_dir():return ['product directory does not exist'],0,profile
        required=SOURCE_REQUIRED if profile=='source' else RUNTIME_REQUIRED
        errors.extend('missing '+name for name in required if not (root/name).is_file())
        files=inventory(root) # Both profiles inspect the complete delivered closure, never history/tests.
        for relative,expected in EXPECTED_HASHES.items():
            if (root/relative).is_file() and sha(root/relative)!=expected:errors.append('canonical hash mismatch: '+relative)
        for p in files:
            if p.suffix=='.json':loads(p.read_text(encoding='utf-8'))
            if p.suffix=='.jsonl':
                for line in p.read_text(encoding='utf-8').splitlines():
                    if line.strip() and not isinstance(loads(line),dict):errors.append('JSONL needs objects: '+str(p.relative_to(root)))
        manifest=root/'PACKAGE-CONTENTS.json'
        if manifest.is_file():
            m=loads(manifest.read_text(encoding='utf-8'))
            if not isinstance(m,dict) or m.get('format')!='omnara-package/v1' or not isinstance(m.get('files'),dict):errors.append('invalid package manifest')
            else:
                actual={p.relative_to(root).as_posix():sha(p) for p in files}
                if m['files']!=actual:errors.append('package files or hashes differ from PACKAGE-CONTENTS.json')
                # Reject unlisted payload within the extracted customer tree, while source history is permitted without a manifest.
                all_files={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
                if all_files!=set(actual)|{'PACKAGE-CONTENTS.json'}:errors.append('unlisted or missing package payload')
        le,count=links(root,files);errors.extend(le)
    except (OSError,ValueError,TypeError,KeyError) as exc:errors.append(str(exc))
    return errors,count,profile

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('root',nargs='?',type=Path,default=Path(__file__).parents[1]);parser.add_argument('--profile',choices=['auto','source','runtime'],default='auto');args=parser.parse_args(argv);errors,count,profile=validate(args.root,args.profile)
    for error in errors:print('ERROR: '+error)
    if errors:return 1
    print(f'VALID current product structure and packaged identity\nPROFILE: {profile}\nLOCAL_LINKS: {count}\nBoundary: no semantic truth, live host activation or renderer conformance established.');return 0
if __name__=='__main__':raise SystemExit(main())
