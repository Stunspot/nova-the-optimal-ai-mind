'use strict';
// Raw input must remain unambiguous before it becomes a native case projection.
// Compare decimal values as written, not their binary floating-point expansion.
// 0.1 and 1e-1 remain supported; a token rounded to a different decimal value does not.
function decimalValue(token) {
  const parts=/^(-?)(\d+)(?:\.(\d+))?(?:[eE]([+-]?\d+))?$/.exec(token);
  let digits=(parts[2]+(parts[3]||'')).replace(/^0+/,'');
  if(!digits)return '0';
  const trailing=digits.length-digits.replace(/0+$/,'').length;
  digits=digits.slice(0,digits.length-trailing);
  const exponent=Number(parts[4]||0)-(parts[3]||'').length+trailing;
  if(!Number.isSafeInteger(exponent))return null;
  return parts[1]+digits+'e'+exponent;
}
function parseCaseJSON(raw) {
  let text=raw.replace(/^\uFEFF/,''),pos=0;
  const fail=message=>{throw Error(message+' at character '+pos);};
  const ws=()=>{while(/[\x20\t\r\n]/.test(text[pos]||'\0'))pos++;};
  function string(){const start=pos++;while(pos<text.length){const c=text[pos++];if(c==='"'){try{return JSON.parse(text.slice(start,pos));}catch{return fail('Invalid JSON string');}}if(c==='\\')pos++;}return fail('Unterminated JSON string');}
  function value(depth){if(depth>80)fail('JSON nesting exceeds 80 levels');ws();const c=text[pos];
    if(c==='"')return string();
    if(c==='{'||c==='['){pos++;const object=c==='{',out=object?Object.create(null):[],keys=new Set();ws();if(text[pos]===(object?'}':']')){pos++;return out;}while(pos<text.length){ws();let key;if(object){if(text[pos]!=='"')fail('Expected object key');key=string();if(keys.has(key))fail('Duplicate JSON key '+key);keys.add(key);ws();if(text[pos++]!==':')fail('Expected colon');}const v=value(depth+1);if(object)out[key]=v;else out.push(v);ws();const next=text[pos++];if(next===(object?'}':']'))return out;if(next!==',')fail('Expected comma or closing delimiter');}return fail('Unterminated container');}
    for(const [word,v] of [['true',true],['false',false],['null',null]])if(text.slice(pos,pos+word.length)===word){pos+=word.length;return v;}
    const number=/^-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?/.exec(text.slice(pos));if(number){pos+=number[0].length;const v=Number(number[0]);if(!Number.isFinite(v))fail('JSON numbers must be finite');if(decimalValue(number[0])!==decimalValue(String(v)))fail('A number would change value in this browser. Both selections are unchanged. Keep the original file; use the native case validator and inspect its original JSON text (see docs/RECOVERY.md). Do not round or automatically convert evidence to strings');return v;}
    return fail('Invalid JSON value');
  }
  const result=value(0);ws();if(pos!==text.length)fail('Trailing JSON data');return result;
}
function knownInstant(raw){
  if(typeof raw!=='string'||!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$/.test(raw)||raw.endsWith('-00:00'))return null;
  if(!raw.endsWith('Z')&&(Number(raw.slice(-5,-3))>23||Number(raw.slice(-2))>59))return null;
  const [y,m,d,h,min,sec]=raw.slice(0,19).split(/[-T:]/).map(Number);
  if(y<1||m<1||m>12||d<1||d>new Date(Date.UTC(y,m,0)).getUTCDate()||h>23||min>59||sec>59)return null;
  const result=Date.parse(raw);return Number.isFinite(result)?result:null;
}
