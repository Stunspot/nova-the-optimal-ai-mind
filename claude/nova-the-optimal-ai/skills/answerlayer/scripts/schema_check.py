"""Interpreter for the fixed bundled schema vocabulary only."""
import re
from decimal import Decimal
from io_contract import LedgerError,dumps,moment

def _shape(value,node,schema,where='$',depth=0):
 """Interpreter only for the fixed bundled schema vocabulary; no network or optional library."""
 if depth>64:return [where+': nesting exceeds64']
 supported={'$schema','$id','title','description','$defs','$ref','type','const','enum','required','properties','additionalProperties','items','minItems','maxItems','uniqueItems','minLength','pattern','format','minimum','maximum','allOf'}
 if set(node)-supported:raise LedgerError('bundled schema uses unsupported validation keywords')
 if '$ref' in node:
  ref=node['$ref']
  if not isinstance(ref,str) or not ref.startswith('#/$defs/') or ref.count('/')!=2:raise LedgerError('bundled schema reference is not supported')
  return _shape(value,schema['$defs'][ref.split('/')[-1]],schema,where,depth+1)
 errors=[]
 for child in node.get('allOf',[]):errors+=_shape(value,child,schema,where,depth+1)
 types=node.get('type');types=types if isinstance(types,list) else [types] if types else []
 checks={'object':lambda:isinstance(value,dict),'array':lambda:isinstance(value,list),'string':lambda:isinstance(value,str),'integer':lambda:type(value) is int,'number':lambda:type(value) in (int,float,Decimal),'boolean':lambda:type(value) is bool,'null':lambda:value is None}
 if types and not any(checks[t]() for t in types):return [where+': wrong type; expected '+','.join(types)]
 if 'const' in node and value!=node['const']:errors.append(where+': wrong constant')
 if 'enum' in node and value not in node['enum']:errors.append(where+': invalid enum')
 if isinstance(value,dict):
  props=node.get('properties',{})
  errors += [where+': missing '+k for k in node.get('required',[]) if k not in value]
  if node.get('additionalProperties') is False:errors += [where+': unsupported '+k for k in value if k not in props]
  for k,v in value.items():
   if k in props:errors+=_shape(v,props[k],schema,where+'.'+k,depth+1)
 elif isinstance(value,list):
  if len(value)<node.get('minItems',0) or len(value)>node.get('maxItems',1000000):errors.append(where+': invalid array length')
  if node.get('uniqueItems') and len({dumps(x,canonical=True) for x in value})!=len(value):errors.append(where+': duplicate array values')
  if 'items' in node:
   for i,v in enumerate(value):errors+=_shape(v,node['items'],schema,where+'['+str(i)+']',depth+1)
 elif isinstance(value,str):
  if len(value)<node.get('minLength',0) or (node.get('minLength',0)>0 and not value.strip()):errors.append(where+': nonblank text required')
  if 'pattern' in node and not re.search(node['pattern'],value):errors.append(where+': invalid text pattern')
  if node.get('format')=='date-time':
   try:moment(value,where)
   except LedgerError as e:errors.append(str(e))
 elif type(value) in (int,float,Decimal):
  if value<node.get('minimum',float('-inf')) or value>node.get('maximum',float('inf')):errors.append(where+': outside permitted range')
 return errors

