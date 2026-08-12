from __future__ import annotations
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
import re

ROOT=Path(__file__).resolve().parent
PAGES=sorted(ROOT.glob('*.html'))
ASSETS=ROOT/'assets'

class Scan(HTMLParser):
    def __init__(self):
        super().__init__(); self.links=[]; self.ids=set(); self.images=[]; self.title=''; self._title=False
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if 'id' in a: self.ids.add(a['id'])
        if tag=='a' and 'href' in a: self.links.append(a['href'])
        if tag=='img': self.images.append((a.get('src',''),a.get('alt')))
    def handle_data(self,data):
        if self._title: self.title+=data
    def handle_startendtag(self,tag,attrs): self.handle_starttag(tag,attrs)
    def handle_endtag(self,tag):
        if tag=='title': self._title=False
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='title': self._title=True
        if 'id' in a: self.ids.add(a['id'])
        if tag=='a' and 'href' in a: self.links.append(a['href'])
        if tag=='img': self.images.append((a.get('src',''),a.get('alt')))

scans={}
errors=[]
for p in PAGES:
    s=Scan(); s.feed(p.read_text(encoding='utf-8')); scans[p.name]=s
    if not s.title.strip(): errors.append(f'{p.name}: missing title')
    if not re.search(r'<html\s+lang="[^"]+"',p.read_text(encoding='utf-8')): errors.append(f'{p.name}: missing html lang')
    if 'Skip to content' not in p.read_text(encoding='utf-8'): errors.append(f'{p.name}: missing skip link')
    for src,alt in s.images:
        if alt is None: errors.append(f'{p.name}: image missing alt: {src}')
        if src and not urlparse(src).scheme and not (p.parent/src.split('#',1)[0]).exists(): errors.append(f'{p.name}: missing image: {src}')
for p in PAGES:
    for href in scans[p.name].links:
        parsed=urlparse(href)
        if parsed.scheme or href.startswith('mailto:'): continue
        base,_,frag=href.partition('#')
        target=p if not base else p.parent/base
        if not target.exists(): errors.append(f'{p.name}: missing link target: {href}'); continue
        if frag and target.suffix=='.html':
            ts=scans.get(target.name)
            if ts and frag not in ts.ids: errors.append(f'{p.name}: missing fragment: {href}')
expected={'nova-mind-readme-hero.png':(1600,720),'nova-mind-pages-hero.png':(1200,800),'nova-mind-social-card.png':(1200,630)}
asset_hashes=set()
for name, expected_size in expected.items():
    path=ASSETS/name
    if not path.exists():
        errors.append(f'missing required asset: {name}')
        continue
    data=path.read_bytes()
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        errors.append(f'asset is not PNG: {name}')
        continue
    import hashlib, struct
    width,height=struct.unpack('>II',data[16:24])
    if (width,height) != expected_size:
        errors.append(f'wrong asset dimensions: {name} {(width,height)} expected {expected_size}')
    asset_hashes.add(hashlib.sha256(data).hexdigest())
if len(asset_hashes) != len(expected):
    errors.append('role-specific assets are not three distinct files')
print(f'pages={len(PAGES)} links={sum(len(s.links) for s in scans.values())} images={sum(len(s.images) for s in scans.values())}')
if errors:
    print('\n'.join('FAIL '+e for e in errors)); raise SystemExit(1)
print('PASS local Pages navigation, fragments, images, titles, language, and skip links')
