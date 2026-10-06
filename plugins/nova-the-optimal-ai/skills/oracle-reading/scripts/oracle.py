"""Exact casts and catalog lookup. Python 3.10+, standard library only."""
import argparse, json, secrets, sys
from pathlib import Path
CAT=json.loads((Path(__file__).resolve().parents[1]/'references/catalog.json').read_text(encoding='utf-8'))
RNG=secrets.SystemRandom()
def decode(lines):
 if len(lines)!=6 or any(type(x) is not int or x not in (6,7,8,9) for x in lines): raise ValueError('Enter exactly six integers 6–9, bottom to top.')
 bits=''.join(str(x%2) for x in lines)
 related=''.join(str(1-x%2 if x in (6,9) else x%2) for x in lines)
 bybits={x['bits']:x for x in CAT['iching']}
 return {'lines':lines,'primary':bybits[bits],'related':bybits[related],'changing':[i+1 for i,x in enumerate(lines) if x in (6,9)]}
def main():
 p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest='op',required=True)
 d=sub.add_parser('draw');d.add_argument('tradition',choices=['tarot','runes','iching']);d.add_argument('--count',type=int,default=3);d.add_argument('--reversals',action='store_true')
 h=sub.add_parser('iching');h.add_argument('lines',nargs='+',type=int)
 l=sub.add_parser('lookup');l.add_argument('tradition',choices=list(('tarot','runes','iching')));l.add_argument('query')
 a=p.parse_args()
 try:
  if a.op=='iching': result={'basis':'user-supplied',**decode(a.lines)}
  elif a.op=='lookup':
   q=a.query.casefold(); found=[x for x in CAT[a.tradition] if q in (x['id'].casefold(),x['name'].casefold(),str(x.get('number','')))]
   if not found: raise ValueError('No exact entry; use a catalog name, ID, or figure number.')
   result=found
  elif a.tradition=='iching': result={'basis':'digital-random','method':'three fair coins; tails=2, heads=3; bottom to top',**decode([sum(RNG.choice((2,3)) for _ in range(3)) for _ in range(6)])}
  else:
   if not 1<=a.count<=10: raise ValueError('Count must be between 1 and 10.')
   if a.tradition=='runes' and a.reversals: raise ValueError('Default rune convention is upright.')
   result={'basis':'digital-random','catalogVersion':CAT['version'],'tradition':a.tradition,'results':[dict(symbol=x,position=str(i+1),reversed=bool(RNG.randrange(2)) if a.reversals else False) for i,x in enumerate(RNG.sample(CAT[a.tradition],a.count))]}
  print(json.dumps(result,ensure_ascii=False,indent=2))
 except ValueError as e: p.error(str(e))
if __name__=='__main__':
 if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
 main()
