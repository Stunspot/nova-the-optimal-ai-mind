"""Bind this authorized edition suffix to its current source without false Git parity."""
import json
from pathlib import Path
import generate_source_lock as locks

root=Path(__file__).resolve().parents[1]
path=root/'design/source-map.json'
value=json.loads(path.read_text(encoding='utf8'))
lock=json.loads((root/'design/source-lock.json').read_text(encoding='utf8'))
record=next(r for r in value['records'] if r['id']=='nova')
tree=next(r for r in lock['records'] if r['id']=='nova')['imported_tree']
record.update(source_state='owner_authorized_working_tree_cutoff',source_file_count=tree['file_count'],source_tree_sha256=tree['tree_sha256'])
record['source_lineage']['current_update']='2026-09-26 Free 3.4.0 edition identity suffix only; retained Git coordinates identify the unchanged cognitive baseline, not current working-tree parity.'
common=next(r for r in value['records'] if r['id']=='commonplace')
marker='2026-09-26 existing read-only Dennis adapter rebound to exact 0.4.0 Nova owner bytes; no new selector or owner writes'
if marker not in common['edition_overlays']:common['edition_overlays'].append(marker)
path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
for sidecar in [root/'delivery-sidecars/Nova the Optimal AI Free T-Free v3.4.0 Extra.md',Path('E:/Github/nova-emergent-source/delivery-sidecars/Nova Emergent v1.3.0 Extra.md')]:
    text=sidecar.read_text(encoding='utf8')
    usage='Optional local workspaces require Python 3.10+. Open the packaged launcher and follow VISUAL-WORKSPACES.md; substantive records remain outside installation. No external publishing, world mutation or generated-media provider is assumed. Ask before creating desktop shortcuts.'
    text=text.replace(usage+'\n\n','')
    text=text.replace('# Changelog',usage+'\n\n# Changelog',1)
    if sidecar.name.startswith('Nova the'):
        text=text.replace('v3.4.0 - 2026-09-23 capability update.','v3.3.0 - 2026-09-23 capability update.')
    else:text=text.replace('v1.3.0 - 2026-09-23 capability update.','v1.2.0 - 2026-09-23 capability update.')
    sidecar.write_text(text,encoding='utf8',newline='\n')
