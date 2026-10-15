#!/usr/bin/env python3
"""Assemble ordered drafts without silently replacing a separately edited report."""
import argparse,json,re,secrets
from pathlib import Path
from custody import reject_links
from evidence_contract import native_files
from file_ops import atomic

def assemble(directory,replace=False):
    directory=reject_links(directory);native_files(directory)
    drafts=sorted((directory/'draft').glob('*.md'))
    if not drafts:raise ValueError('no Markdown section drafts found')
    text='\n\n'.join(reject_links(p).read_text(encoding='utf-8').strip() for p in drafts)+'\n'
    if not text.strip():raise ValueError('section drafts are empty')
    report=directory/'report.md';previous=report.read_bytes() if report.is_file() else None
    placeholder=Path(__file__).parents[1]/'assets/campaign-vault/report.md'
    changed=previous not in (None,text.encode(),placeholder.read_bytes())
    if changed and not replace:raise ValueError('report.md differs from drafts; inspect both before --replace. Existing report preserved.')
    backup=None
    if changed:
        backup=directory/'.assembly-history'/('report-'+secrets.token_hex(8)+'.md');atomic(backup,previous)
    atomic(report,text)
    words=re.findall(r"\b[\w'-]+\b",text)
    result={'sections':[p.name for p in drafts],'words':len(words),'estimated_pages_300_words':round(len(words)/300,1),'estimated_pages_500_words':round(len(words)/500,1),'estimate_boundary':'Layout-dependent estimate, not rendered pages. Rerun citation integrity and actual affected semantic review after changed content.','prior_report':str(backup) if backup else None}
    atomic(directory/'report-metrics.json',json.dumps(result,indent=2)+'\n');return result

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory',type=Path);parser.add_argument('--replace',action='store_true',help='After comparison, replace differing report and retain prior bytes in .assembly-history.');args=parser.parse_args()
    try:print(json.dumps(assemble(args.directory,args.replace),indent=2));return 0
    except (OSError,ValueError,TypeError) as exc:print('ERROR: '+str(exc));return 1
if __name__=='__main__':raise SystemExit(main())
