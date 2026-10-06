"""Render the host AI's reading state. Python 3.10+, standard library only."""
import argparse, base64, hashlib, json, sys
from pathlib import Path
from urllib.parse import quote
import oracle
ROOT=Path(__file__).resolve().parents[1]
SCHEMA='oracle-reading/table-v1'
def require(test,message):
 if not test: raise ValueError(message)
def text(value,limit,label):
 require(type(value) is str and len(value)<=limit,'Invalid '+label);return value
def normalize(raw):
 require(type(raw) is dict,'Reading must be an object')
 if raw.get('schema')=='oracle-reading/v1':
  require(raw.get('catalogVersion')==oracle.CAT['version'],'Unsupported legacy catalog')
  tradition=raw.get('tradition');old=raw.get('results')
  require(type(old) is list,'Legacy results must be an array')
  raw={**raw,'schema':SCHEMA,'revision':1,'phase':'active',
       'revealed':[x.get('id') for x in old] if tradition in ('tarot','runes') else []}
  if tradition=='iching':raw.update(lines=old,showChanges=True,showRelated=True)
  if tradition=='astrology':
   require(all(type(x) is dict and type(x.get('houseKnown')) is bool for x in old),'Invalid legacy chart')
   raw.update(placements=[{'planet':x.get('planet'),'sign':x.get('sign'),**({'house':x.get('house')} if x['houseKnown'] else {})} for x in old],
              source='; '.join(dict.fromkeys(x.get('source','') for x in old)),
              system='; '.join(dict.fromkeys(x.get('system','') for x in old)))
 require(raw.get('schema')==SCHEMA,'Unsupported table schema')
 r={'schema':SCHEMA,'id':text(raw.get('id'),80,'reading ID'),'revision':raw.get('revision'),
    'tradition':raw.get('tradition'),'phase':raw.get('phase','active')}
 require(r['id'] and type(r['revision']) is int and r['revision']>0,'Reading ID and positive revision required')
 require(r['tradition'] in ('tarot','runes','iching','astrology'),'Unknown tradition')
 require(r['phase'] in ('active','quiet','clear'),'Unknown phase')
 if r['phase']=='clear':return r
 r.update(question=text(raw.get('question',''),1500,'question'),basis=raw.get('basis'),
          thread=text(raw.get('thread',''),400,'shared phrase'),focus=raw.get('focus'))
 require(r['basis'] in ('digital-random','user-supplied','illustrative'),'Unknown basis')
 if r['tradition'] in ('tarot','runes'):
  source=raw.get('results');require(type(source) is list and 1<=len(source)<=10,'Use 1-10 symbols')
  known={x['id'] for x in oracle.CAT[r['tradition']]};results=[]
  for x in source:
   require(type(x) is dict,'Invalid symbol')
   ident=x.get('id') or x.get('symbol',{}).get('id')
   require(ident in known,'Unknown symbol ID')
   require(type(x.get('reversed',False)) is bool,'Invalid orientation')
   require(r['tradition']=='tarot' or not x.get('reversed',False),'Rune convention is upright')
   results.append({'id':ident,'position':text(x.get('position',''),100,'position'),
                   'reversed':x.get('reversed',False),'phrase':text(x.get('phrase',''),160,'symbol phrase')})
  ids=[x['id'] for x in results];require(len(set(ids))==len(ids),'Duplicate symbol')
  revealed=raw.get('revealed',[]);require(type(revealed) is list and all(type(x) is str for x in revealed),'Invalid revealed set')
  require(len(set(revealed))==len(revealed) and all(x in ids for x in revealed),'Invalid revealed set')
  require(r['focus'] is None or r['focus'] in revealed,'Focus must be revealed')
  r.update(results=results,revealed=revealed)
 elif r['tradition']=='iching':
  lines=raw.get('lines');oracle.decode(lines if type(lines) is list else [])
  require(type(raw.get('showChanges',False)) is bool and type(raw.get('showRelated',False)) is bool,'Reveal flags must be boolean')
  r.update(lines=lines,showChanges=raw.get('showChanges',False),showRelated=raw.get('showRelated',False))
  require(not r['showRelated'] or r['showChanges'],'Reveal changes before related figure')
  require(r['focus'] in (None,'primary','related') and (r['focus']!='related' or r['showRelated']),'Invalid hexagram focus')
 else:
  ps=raw.get('placements');require(type(ps) is list and 1<=len(ps)<=10,'Known placements required')
  planets=['Sun','Moon','Mercury','Venus','Mars','Jupiter','Saturn','Uranus','Neptune','Pluto']
  signs=['Aries','Taurus','Gemini','Cancer','Leo','Virgo','Libra','Scorpio','Sagittarius','Capricorn','Aquarius','Pisces']
  r['placements']=[]
  for x in ps:
   require(type(x) is dict and x.get('planet') in planets and x.get('sign') in signs,'Unknown planet/sign')
   require('house' not in x or type(x['house']) is int and 1<=x['house']<=12,'Invalid known house')
   r['placements'].append({'planet':x['planet'],'sign':x['sign'],**({'house':x['house']} if 'house' in x else {}),
                           'phrase':text(x.get('phrase',''),160,'placement phrase')})
  ids=[x['planet'] for x in r['placements']];require(len(set(ids))==len(ids),'Duplicate planet')
  aspects=raw.get('aspects',[]);require(type(aspects) is list and len(aspects)<=20,'Invalid aspects')
  r['aspects']=[]
  for x in aspects:
   require(type(x) is dict and x.get('from') in ids and x.get('to') in ids and x['from']!=x['to']
           and x.get('kind') in ('conjunction','sextile','square','trine','opposition'),'Invalid supplied aspect')
   r['aspects'].append({k:x[k] for k in ('from','to','kind')})
  r.update(source=text(raw.get('source','Supplied chart notes'),200,'chart source'),
           system=text(raw.get('system','Western symbolic astrology'),200,'chart convention'))
  require(r['focus'] is None or r['focus'] in ids or r['focus']=='relations','Invalid planetary focus')
 return r
def canonical(r):
 return json.dumps(r,sort_keys=True,ensure_ascii=False,separators=(',',':'))
def facts(r):
 keys=('tradition','question','basis','lines','placements','aspects','source','system')
 f={k:r[k] for k in keys if k in r}
 if 'results' in r:f['results']=[{k:x[k] for k in ('id','position','reversed')} for x in r['results']]
 if 'placements' in f:f['placements']=[{k:v for k,v in x.items() if k!='phrase'} for x in f['placements']]
 return f
def continuity(r,previous):
 if previous is None:
  require(r['revision']==1,'Continuation requires --previous canonical record');return
 p=normalize(previous);require(r['id']==p['id'],'Use a fresh revision-1 record for a new reading')
 require(r['tradition']==p['tradition'],'Same-ID update changed tradition')
 require(r['revision']==p['revision']+1 or canonical(r)==canonical(p),'Increment revision by one, or retry identical state')
 if r['phase']!='clear':
  require(p['phase']!='clear','Begin a new reading after clear; retain an earlier canonical record to resume')
  require(facts(r)==facts(p),'Same-ID update changed question, basis, cast or supplied chart facts')
def read(path):
 require(path.stat().st_size<=100000,'Record exceeds 100 KB');return json.loads(path.read_text(encoding='utf-8-sig'))
def safe_json(obj):
 return json.dumps(obj,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
STANDALONE_STYLE="""
:root{--background:#171526;--foreground:#f5eee2;--muted:#262236;--muted-foreground:#c9c0cb;--border:#655c70;--viz-series-1:#e6c889;color-scheme:dark}
body{margin:0;background:var(--background);color:var(--foreground);font:18px/1.6 Georgia,serif}
main{max-width:1000px;margin:auto;padding:32px 24px}
h1{font-size:1.1rem;font-weight:400;letter-spacing:.08em;margin:0 0 20px}
h2{font-size:1.45rem;font-weight:400}p{margin:0}
.oracle-table{padding-bottom:44px}.oracle-basis,.oracle-source{font:14px/1.6 system-ui,sans-serif}
a{color:inherit}footer{font:14px/1.6 system-ui,sans-serif;text-align:center;padding:24px}
"""
def fragment(r,inline):
 display={k:[{a:x[a] for a in ('id','name','number','bits','glyph') if a in x} for x in oracle.CAT[k]] for k in ('tarot','runes','iching')}
 resources={'catalog':display,'images':{}}
 if r['phase']=='active' and r['tradition']=='tarot':
  if any(x['id'] not in r['revealed'] for x in r['results']):
   p=ROOT/'assets/card-back.jpg'
   resources['cardBack']='data:image/jpeg;base64,'+base64.b64encode(p.read_bytes()).decode()
  for x in r['results']:
   if x['id'] in r['revealed']:
    p=ROOT/'assets/cards'/(x['id']+'.jpg')
    if p.is_file():resources['images'][x['id']]='data:image/jpeg;base64,'+base64.b64encode(p.read_bytes()).decode()
 identity=hashlib.sha256((r['id']+str(r['revision'])).encode()).hexdigest()[:12]
 root='oracle-'+identity
 css=(ROOT/'assets/table.css').read_text(encoding='utf-8')
 js=(ROOT/'assets/table.js').read_text(encoding='utf-8')
 # Scope geometry to this exact root; shared JS only writes inside it.
 css=css.replace('.oracle-', '#'+root+' .oracle-').replace('#'+root+' .oracle-table','#'+root)
 record=safe_json(r)
 output=f'<div id="{root}" class="oracle-table" role="region"></div>\n<style>\n{css}\n</style>\n<script>\n{js}\nOracleTable.render(document.getElementById("{root}"),{record},{safe_json(resources)});\n</script>\n'
 if inline:require(len(output.encode())<1000000,'Inline projection exceeds 1 MB; use standalone or a smaller revealed set at its true conversation stage')
 return output
def receipt(r,path=None,content=None):
 result={'id':r['id'],'revision':r['revision'],'phase':r['phase'],'tradition':r['tradition'],'focus':r.get('focus')}
 if r['phase']=='active':
  result['visible']=r.get('revealed',[]) if r['tradition'] in ('tarot','runes') else (['primary']+(['changes'] if r.get('showChanges') else [])+(['related'] if r.get('showRelated') else []) if r['tradition']=='iching' else [x['planet'] for x in r['placements']])
 else:result['visible']=[]
 if path is not None:result.update(output=str(path.resolve()),sha256=hashlib.sha256(content.encode()).hexdigest())
 return result
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('record',type=Path);p.add_argument('--output',type=Path)
 p.add_argument('--inline',action='store_true');p.add_argument('--previous',type=Path);p.add_argument('--url',action='store_true')
 a=p.parse_args()
 try:
  r=normalize(read(a.record));continuity(r,read(a.previous) if a.previous else None)
  if a.url:
   print(json.dumps({**receipt(r),'url':'https://stunspot.github.io/oracle-reading/#table='+quote(canonical(r),safe=''),
                     'custody':'URL fragment can remain in browser history and copied links. Prefer local/inline for private readings.'},ensure_ascii=False));return
  require(a.output is not None,'--output is required unless --url is used')
  content=fragment(r,a.inline)
  if not a.inline:
   content='<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Oracle Reading</title><style>'+STANDALONE_STYLE+'</style></head><body><main><h1>Oracle Reading</h1>'+content+'</main></body></html>\n'
  a.output.parent.mkdir(parents=True,exist_ok=True)
  temp=a.output.with_name(a.output.name+'.tmp');temp.write_text(content,encoding='utf-8');temp.replace(a.output)
  print(json.dumps(receipt(r,a.output,content),ensure_ascii=False))
 except (ValueError,OSError,TypeError,KeyError) as e:p.error(str(e))
if __name__=='__main__':
 if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
 main()
