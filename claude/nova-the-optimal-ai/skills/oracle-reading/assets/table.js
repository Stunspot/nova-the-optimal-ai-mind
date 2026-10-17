/* Shared reading-table projection. Meaning and reveal decisions belong to the host AI. */
(function(global){
"use strict";
const schema="oracle-reading/table-v1";
function text(v,max,label){if(typeof v!=="string"||v.length>max)throw Error("Invalid "+label);return v;}
function check(v,message){if(!v)throw Error(message);}
function normalize(raw,cat){
 check(raw&&raw.schema===schema,"Unsupported table schema");
 const r={schema,id:text(raw.id,80,"reading ID"),revision:raw.revision,tradition:raw.tradition,phase:raw.phase||"active"};
 check(r.id.length&&Number.isInteger(r.revision)&&r.revision>0,"Reading ID and positive revision required");
 check(["tarot","runes","iching","astrology"].includes(r.tradition),"Unknown tradition");
 check(["active","quiet","clear"].includes(r.phase),"Unknown table phase");
 if(r.phase==="clear")return r;
 r.question=text(raw.question||"",1500,"question");r.basis=raw.basis;
 check(["digital-random","user-supplied","illustrative"].includes(r.basis),"Unknown basis");
 r.thread=text(raw.thread||"",400,"shared phrase");
 r.focus=raw.focus===undefined?null:raw.focus;
 if(["tarot","runes"].includes(r.tradition)){
  check(Array.isArray(raw.results)&&raw.results.length>=1&&raw.results.length<=10,"Use 1-10 symbols");
  r.results=raw.results.map(x=>{
   check(x&&typeof x==="object","Invalid symbol");const id=x.id||(x.symbol&&x.symbol.id);
   check(cat[r.tradition].some(s=>s.id===id),"Unknown symbol");
   check(typeof x.reversed==="boolean"||x.reversed===undefined,"Invalid orientation");
   check(r.tradition==="tarot"||!x.reversed,"Rune convention is upright");
   return {id,position:text(x.position||"",100,"position"),reversed:!!x.reversed,phrase:text(x.phrase||"",160,"symbol phrase")};
  });
  const ids=r.results.map(x=>x.id);check(new Set(ids).size===ids.length,"Duplicate symbol");
  r.revealed=raw.revealed||[];check(Array.isArray(r.revealed)&&new Set(r.revealed).size===r.revealed.length&&r.revealed.every(x=>ids.includes(x)),"Invalid revealed set");
  check(r.focus===null||r.revealed.includes(r.focus),"Focus must be revealed");
 }else if(r.tradition==="iching"){
  check(Array.isArray(raw.lines)&&raw.lines.length===6&&raw.lines.every(x=>Number.isInteger(x)&&[6,7,8,9].includes(x)),"Six lines 6-9, bottom to top required");
  check(raw.showChanges===undefined||typeof raw.showChanges==='boolean','Reveal flags must be boolean');
  check(raw.showRelated===undefined||typeof raw.showRelated==='boolean','Reveal flags must be boolean');
  r.lines=raw.lines.slice();r.showChanges=raw.showChanges===true;r.showRelated=raw.showRelated===true;
  check(!r.showRelated||r.showChanges,"Reveal changes before related figure");
  check(r.focus===null||["primary","related"].includes(r.focus),"Invalid hexagram focus");
  check(r.focus!=="related"||r.showRelated,"Related figure is hidden");
 }else{
  check(Array.isArray(raw.placements)&&raw.placements.length>=1&&raw.placements.length<=10,"Known placements required");
  const planets=["Sun","Moon","Mercury","Venus","Mars","Jupiter","Saturn","Uranus","Neptune","Pluto"];
  const signs=["Aries","Taurus","Gemini","Cancer","Leo","Virgo","Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"];
  r.placements=raw.placements.map(x=>{
   check(x&&planets.includes(x.planet)&&signs.includes(x.sign),"Unknown planet/sign");
   check(x.house===undefined||Number.isInteger(x.house)&&x.house>=1&&x.house<=12,"Invalid known house");
   return {planet:x.planet,sign:x.sign,...(x.house===undefined?{}:{house:x.house}),phrase:text(x.phrase||"",160,"placement phrase")};
  });
  const ids=r.placements.map(x=>x.planet);check(new Set(ids).size===ids.length,"Duplicate planet");
  r.aspects=(raw.aspects||[]).map(x=>{
   check(x&&ids.includes(x.from)&&ids.includes(x.to)&&x.from!==x.to&&["conjunction","sextile","square","trine","opposition"].includes(x.kind),"Invalid supplied aspect");
   return {from:x.from,to:x.to,kind:x.kind};
  });check(r.aspects.length<=20,"Too many aspects");
  r.source=text(raw.source||"Supplied chart notes",200,"chart source");
  r.system=text(raw.system||"Western symbolic astrology",200,"chart convention");
  check(r.focus===null||ids.includes(r.focus)||r.focus==="relations","Invalid planetary focus");
 }
 return r;
}
function decode(lines,cat){
 const bits=lines.map(x=>x%2).join("");
 const related=lines.map(x=>[6,9].includes(x)?1-x%2:x%2).join("");
 return {primary:cat.iching.find(x=>x.bits===bits),related:cat.iching.find(x=>x.bits===related),changing:lines.flatMap((x,i)=>[6,9].includes(x)?[i+1]:[])};
}
function render(root,raw,resources){
 const cat=resources.catalog,r=normalize(raw,cat);
 root.replaceChildren();root.dataset.readingId=r.id;root.dataset.revision=String(r.revision);root.dataset.phase=r.phase;
 root.setAttribute("aria-label","Reading table");root.setAttribute("aria-live","polite");
 function el(tag,cls,value,parent=root){const e=document.createElement(tag);if(cls)e.className=cls;if(value!==undefined)e.textContent=value;parent.append(e);return e;}
 if(r.phase==="clear"){el("p","oracle-silence","The table is clear.");return r;}
 if(r.phase==="quiet"){el("p","oracle-silence","We can leave the table quiet.");return r;}
 if(r.question)el("h2","oracle-question",r.question);
 const stage=el("div","oracle-stage");
 if(["tarot","runes"].includes(r.tradition)){
  stage.classList.add("oracle-spread");
  for(const item of r.results){
   const symbol=cat[r.tradition].find(x=>x.id===item.id),shown=r.revealed.includes(item.id);
   const fig=el("figure","oracle-symbol"+(r.focus&&r.focus!==item.id?" oracle-resting":""),undefined,stage);
   fig.dataset.symbolId=item.id;fig.dataset.revealed=String(shown);
   el("p","oracle-position",item.position,fig);
   if(shown){
    if(r.tradition==="tarot"&&resources.images&&resources.images[item.id]){
     const img=el("img","oracle-card"+(item.reversed?" oracle-reversed":""),undefined,fig);
     img.src=resources.images[item.id];img.alt=symbol.name+(item.reversed?", reversed":", upright")+" — Rider-Waite-Smith";
     img.width=330;img.height=570;img.loading="eager";img.decoding="async";
     img.addEventListener("error",()=>{img.remove();el("p","oracle-art-missing","Card picture unavailable",fig);});
    }else if(r.tradition==="runes")el("h2","oracle-rune",symbol.glyph,fig);
    else el("div","oracle-card oracle-name-only",symbol.name,fig);
    el("figcaption","oracle-caption",symbol.name+(r.tradition==="tarot"?(item.reversed?" · reversed":" · upright"):""),fig);
    if(item.phrase)el("p","oracle-phrase",item.phrase,fig);
   }else{
    if(r.tradition==="tarot"&&resources.cardBack){
     const back=el("img","oracle-card oracle-card-back",undefined,fig);
     back.src=resources.cardBack;back.alt="Face-down card in "+item.position;
     back.width=330;back.height=570;back.loading="eager";back.decoding="async";
     back.addEventListener("error",()=>{back.remove();el("div","oracle-card oracle-name-only","Face-down card",fig);});
    }else{
     const back=el("div","oracle-card oracle-unrevealed",r.tradition==="tarot"?"Face-down card":"",fig);
     back.setAttribute("role","img");back.setAttribute("aria-label","Unrevealed symbol in "+item.position);
    }
   }
  }
 }else if(r.tradition==="iching"){
  stage.classList.add("oracle-hexagrams");const d=decode(r.lines,cat);
  function hex(symbol,values,which){
   const fig=el("figure","oracle-hexagram"+(r.focus&&r.focus!==which?" oracle-resting":""),undefined,stage);
   fig.dataset.figure=String(symbol.number);
   const lines=el("div","oracle-lines",undefined,fig);lines.setAttribute("role","img");
   lines.setAttribute("aria-label",symbol.number+" "+symbol.name+", lines from bottom to top "+values.join(", "));
   for(let i=5;i>=0;i--){
    const row=el("div","oracle-line"+(r.showChanges&&which==="primary"&&d.changing.includes(i+1)?" oracle-changing":""),undefined,lines);
    row.dataset.line=String(i+1);row.dataset.value=String(values[i]);
    if(values[i]%2)el("span","oracle-yang","",row);
    else{el("span","oracle-yin","",row);el("span","oracle-yin","",row);}
    if(r.showChanges&&which==="primary"&&d.changing.includes(i+1))el("span","oracle-change-mark",String(i+1)+" changes",row);
   }
   el("figcaption","oracle-caption",symbol.number+" · "+symbol.name,fig);
  }
  hex(d.primary,r.lines,"primary");
  if(r.showRelated)hex(d.related,r.lines.map(x=>[6,9].includes(x)?(x===6?7:8):x),"related");
  if(r.showChanges)el("p","oracle-movement",d.changing.length?"Changing lines "+d.changing.join(" and "):"No changing lines",root);
 }else{
  stage.classList.add("oracle-planets");
  const glyphs={Sun:"☉",Moon:"☾",Mercury:"☿",Venus:"♀",Mars:"♂",Jupiter:"♃",Saturn:"♄",Uranus:"♅",Neptune:"♆",Pluto:"♇"};
  for(const x of r.placements){
   const fig=el("figure","oracle-planet"+(r.focus&&r.focus!=="relations"&&r.focus!==x.planet?" oracle-resting":""),undefined,stage);
   fig.dataset.planet=x.planet;el("h2","oracle-planet-glyph",glyphs[x.planet],fig);
   el("figcaption","oracle-caption",x.planet+" in "+x.sign+(x.house?" · house "+x.house:""),fig);
   if(x.phrase)el("p","oracle-phrase",x.phrase,fig);
  }
  const relations=el("div","oracle-relations");
  for(const x of r.aspects)el("p","oracle-relation",x.from+" — "+x.kind+" — "+x.to,relations);
  el("p","oracle-source",r.source+" · "+r.system,root);
 }
 if(r.thread)el("p","oracle-thread",r.thread);
 const basis={"digital-random":"Digital cast","user-supplied":"Supplied by you",illustrative:"Illustrative selection"};
 el("p","oracle-basis",basis[r.basis]+(r.tradition==="tarot"?" · Rider-Waite-Smith":""));
 return r;
}
global.OracleTable={normalize,decode,render};
})(typeof window!=="undefined"?window:globalThis);
