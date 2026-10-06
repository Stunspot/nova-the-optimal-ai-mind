'use strict';
const $ = id => document.getElementById(id);
const GROUPS = ['sources','captures','observations','claims','events','entities','relations','inferences','hypotheses','contradictions','assessments','recommendations','decisions','outcomes','artifacts','checks','blockers','history'];
const LENSES = ['Situation','Sequence','Evidence chains','Challenge','Sources','Compare'];
let current = null, baseline = null, active = 'Situation', sourceMode = '', selectedId = null, returnFocus = null;

function el(tag, content, attrs = {}) {
  const node = document.createElement(tag);
  if (content !== null && content !== undefined) node.textContent = String(content);
  for (const [key, val] of Object.entries(attrs)) node.setAttribute(key, val);
  return node;
}
function add(parent, ...children) { children.flat().filter(Boolean).forEach(child => parent.append(child)); return parent; }
function btn(label, action, className = '') {
  const node = el('button', label, {type:'button'});
  if (className) node.className = className;
  node.addEventListener('click', action);
  return node;
}
function title(object) { return object.title || object.statement || object.summary || object.name || object.description || object.id; }
function value(v) { return v === undefined || v === null || v === '' ? 'Not recorded' : typeof v === 'object' ? JSON.stringify(v) : String(v); }
function refs(object) { return [...new Set(Object.entries(object).filter(([key, val]) => key.endsWith('_ids') && Array.isArray(val)).flatMap(([, val]) => val))]; }
function findRecord(id, caseData = current) {
  if (!caseData) return null;
  for (const kind of GROUPS) {
    const object = caseData[kind].find(item => item.id === id);
    if (object) return {kind, object};
  }
  return null;
}
function validate(caseData) {
  if (!caseData || caseData.format !== 'cd-observatory-case/v1' || !caseData.case_id || !caseData.question) throw Error('Expected a named cd-observatory-case/v1 with question.');
  const ids = new Set();
  for (const kind of GROUPS) {
    if (!Array.isArray(caseData[kind])) throw Error('Missing typed object array: ' + kind + '.');
    for (const object of caseData[kind]) {
      if (!object || typeof object !== 'object' || typeof object.id !== 'string' || !object.id.trim()) throw Error('Object without ID in ' + kind + '.');
      if (ids.has(object.id)) throw Error('Duplicate object ID: ' + object.id + '.');
      ids.add(object.id);
    }
  }
  return caseData;
}
async function load(file, isBaseline = false) {
  if (!file) return;
  const status = $('status');
  status.textContent = 'Reading ' + (isBaseline ? 'baseline' : 'current case') + ' locally…';
  try {
    if (file.size > 5e6) throw Error('Case exceeds the 5 MB limit.');
    const next = validate(JSON.parse((await file.text()).replace(/^\uFEFF/,'')));
    if (isBaseline) baseline = next;
    else { current = next; sourceMode = 'native file'; active = 'Situation'; }
    closeInspector(false);
    render();
    status.textContent = (isBaseline ? 'Baseline' : 'Current case') + ' loaded as dated, read-only case data. No background monitoring.';
    $('case-controls').open = false;
  } catch (error) {
    status.textContent = 'Case rejected; previous selection retained. ' + error.message;
  }
}
function stamp(raw) {
  if (!raw) return 'Time not recorded';
  const date = new Date(raw);
  return Number.isNaN(date.getTime()) ? String(raw) : new Intl.DateTimeFormat('en', {day:'2-digit', month:'short', year:'numeric', hour:'2-digit', minute:'2-digit', timeZone:'UTC', timeZoneName:'short'}).format(date);
}
function stateClass(raw) {
  const status = String(raw || '').toLowerCase();
  if (/unsupported|corrected|superseded|excluded|contradicted|rejected/.test(status)) return 'is-warn';
  if (/open|pending|unverified|provisional|candidate|draft|unresolved/.test(status)) return 'is-hold';
  if (/supported|reviewable|approved|resolved|preserved|passed|observed|available/.test(status)) return 'is-clear';
  return '';
}
function badge(status, className = '') { return el('span', value(status), {class:'state-tag ' + stateClass(status) + ' ' + className}); }
function label(text) { return el('p', text, {class:'micro-label'}); }
function region(heading, className = '') { return add(el('section', null, {class:className}), el('h2', heading)); }
function recordButton(kind, object, className = '') {
  const singular = {hypotheses:'hypothesis',records:'record'}[kind] || kind.slice(0,-1);
  const node = btn('', () => openInspector(object.id), 'record-button ' + className);
  add(node, el('span', singular + ' / ' + object.id, {class:'micro-label'}), el('strong', title(object)), badge(object.status));
  return node;
}
function field(parent, name, content) {
  if (content === undefined || content === null || content === '') return;
  add(parent, el('dt', name.replaceAll('_',' ')), el('dd', value(content)));
}
function exactRecord(kind, object, linked = true) {
  const article = el('article', null, {class:'exact-record'});
  add(article, label(kind + ' / ' + object.id), el('h3', title(object)));
  const tags = el('div', null, {class:'tag-row'});
  add(tags, badge(object.status), el('span','Confidence: ' + value(object.confidence),{class:'state-tag'}));
  article.append(tags);
  if (object.uncertainty !== undefined) add(article, label('Recorded uncertainty'), el('p',value(object.uncertainty),{class:'uncertainty-text'}));
  const fields = el('dl',null,{class:'record-fields'});
  const displayed = ['description','summary','statement','body','reason','event_start','event_end','observed_at','published_at','retrieved_at','first_seen_at','last_seen_at','relation_type','from_id','to_id','location','original_url','canonical_url','preservation_status'];
  for (const key of displayed) if (object[key] !== undefined && value(object[key]) !== title(object)) field(fields,key,object[key]);
  if (fields.children.length) article.append(fields);
  if (linked) {
    const links = el('div',null,{class:'record-links'});
    const ids = refs(object);
    if (kind === 'relations') ids.push(object.from_id,object.to_id);
    for (const id of [...new Set(ids.filter(Boolean))]) links.append(btn('↗ ' + id, () => openInspector(id)));
    if (links.children.length) add(article,label('Follow its recorded evidence'),links);
    else add(article,el('p','No exact provenance or challenge reference recorded.',{class:'muted-note'}));
  }
  const original = el('details',null,{class:'raw-fields'});
  add(original,el('summary','All original fields'),el('pre',JSON.stringify(object,null,2)));
  article.append(original);
  return article;
}
function openInspector(id) {
  if (!current) return;
  const found = findRecord(id), pane = $('inspector');
  if (pane.hidden) returnFocus = document.activeElement;
  selectedId = id;
  pane.replaceChildren();
  const head = el('div',null,{class:'inspector-head'});
  add(head,label('The original evidence record'),btn('Close ×',() => closeInspector(true),'close-inspector'));
  pane.append(head);
  if (found) pane.append(exactRecord(found.kind,found.object));
  else add(pane,el('h2','Unresolved reference'),el('p','No native record with ID ' + id + ' exists in this case. The gap remains visible.'));
  pane.hidden = false;
  pane.setAttribute('tabindex','-1');
  pane.focus({preventScroll:true});
}
function closeInspector(restore = true) {
  $('inspector').hidden = true;
  $('inspector').replaceChildren();
  selectedId = null;
  if (restore && returnFocus && returnFocus.isConnected) returnFocus.focus();
  returnFocus = null;
}
function caseHeader() {
  const hero = el('section',null,{class:'case-hero'});
  const top = el('div',null,{class:'case-hero-top'});
  add(top,label(sourceMode === 'synthetic' ? 'SYNTHETIC FIXTURE · DATED SNAPSHOT' : 'YOUR INVESTIGATION · DATED SNAPSHOT'),el('span',current.case_id,{class:'case-id'}));
  add(hero,top,el('h1',current.title),el('p',current.question,{class:'case-question'}));
  const meta = el('div',null,{class:'case-meta'});
  add(meta,add(el('div'),label('Posture'),el('strong',value(current.posture))),add(el('div'),label('Horizon'),el('strong',value(current.time_horizon))),add(el('div'),label('Audience / decision'),el('strong',value(current.audience_or_decision))));
  hero.append(meta);
  return hero;
}
function renderEmpty(main) {
  const start = el('section',null,{class:'welcome'});
  add(start,label('01 / An investigation in view'),el('h1','A story changes. Keep the evidence in view.'),el('p','Trace what was claimed, what a source actually recorded, what changed over time, and what remains unresolved. Open a native case to see its evidence as a connected situation.'),btn('Explore the synthetic case ↗',loadSample,'primary-action'));
  const open = el('label',null,{class:'open-file'});
  add(open,el('span','Open your investigation file'),el('input',null,{type:'file',accept:'.json,application/json','aria-label':'Open your investigation file'}));
  open.querySelector('input').addEventListener('change', event => load(event.target.files[0]));
  start.append(open);
  const guide = el('div',null,{class:'welcome-guide'});
  add(guide,add(el('div'),label('See together'),el('p','Assessment, competing accounts, timeline and provenance stay connected.')),add(el('div'),label('Follow a thread'),el('p','Select a claim or event to inspect the exact native record and its references.')),add(el('div'),label('Know the boundary'),el('p','Local read-only projection. No collection, monitoring, publication or approval.')));
  start.append(guide);
  main.append(start);
}
function renderSituation(main) {
  const assessment = current.assessments.at(-1);
  const blocker = current.blockers.find(item => String(item.status).toLowerCase() === 'open');
  const briefing = el('section',null,{class:'briefing'});
  const lead = el('div',null,{class:'briefing-lead'});
  add(lead,label('Current assessment · ' + (assessment ? assessment.id : 'none recorded')),el('h2',assessment ? title(assessment) : 'No assessment recorded yet.'));
  if (assessment) add(lead,badge(assessment.status),el('p','Uncertainty: ' + value(assessment.uncertainty),{class:'briefing-uncertainty'}),btn('Inspect assessment ↗',() => openInspector(assessment.id),'text-action'));
  const decision = el('div',null,{class:'decision-cue'});
  add(decision,label('Next human move'),el('h2',value(current.next_action?.action)),el('p','Next step for: ' + value(current.next_action?.owner)));
  if (blocker) add(decision,label('Open boundary'),btn(title(blocker) + ' ↗',() => openInspector(blocker.id),'blocker-action'));
  add(briefing,lead,decision);
  main.append(briefing);
  const grid = el('div',null,{class:'situation-grid'});
  const claims = region('Claims in play','claim-field');
  add(claims,el('p','Status is a recorded judgment, not a truth certificate.',{class:'section-intro'}));
  if (current.claims.length) current.claims.forEach((object,index) => {
    const row = recordButton('claims',object,'claim-line');
    row.prepend(el('span',String(index+1).padStart(2,'0'),{class:'claim-number'}));
    const context = el('span',value(object.uncertainty),{class:'claim-uncertainty'});
    row.append(context);
    claims.append(row);
  });
  else claims.append(el('p','No claims recorded. The case may still be gathering evidence.',{class:'empty-note'}));
  const accounts = region('Rival accounts','rival-field');
  add(accounts,el('p','Keep explanations separate until evidence discriminates between them.',{class:'section-intro'}));
  if (current.hypotheses.length) current.hypotheses.forEach(object => {
    const card = recordButton('hypotheses',object,'rival-card');
    card.append(el('span',value(object.uncertainty),{class:'rival-uncertainty'}));
    accounts.append(card);
  });
  else accounts.append(el('p','No competing explanation recorded.',{class:'empty-note'}));
  add(grid,claims,accounts);
  main.append(grid);
  const thread = region('Time, with its clocks separated','time-preview');
  const moments = timeMoments().slice(-6);
  const rail = el('div',null,{class:'moment-rail'});
  moments.forEach(item => rail.append(momentButton(item)));
  if (!moments.length) rail.append(el('p','No dated event, observation or capture recorded.',{class:'empty-note'}));
  add(thread,el('p','Event, observation, publication and retrieval times describe different things.',{class:'section-intro'}),rail,btn('Read full sequence →',() => switchLens('Sequence'),'text-action'));
  main.append(thread);
}
function timeMoments() {
  const moments = [];
  for (const object of current.events) if (object.event_start) moments.push({kind:'Event',clock:'Event time',time:object.event_start,object});
  for (const object of current.observations) if (object.observed_at) moments.push({kind:'Observation',clock:'Observed',time:object.observed_at,object});
  for (const object of current.captures) {
    if (object.published_at) moments.push({kind:'Capture',clock:'Published',time:object.published_at,object});
    if (object.retrieved_at) moments.push({kind:'Capture',clock:'Retrieved',time:object.retrieved_at,object});
  }
  return moments.sort((a,b) => {const aa=Date.parse(a.time),bb=Date.parse(b.time);return Number.isFinite(aa)&&Number.isFinite(bb)?aa-bb:Number.isFinite(aa)?-1:Number.isFinite(bb)?1:String(a.time).localeCompare(String(b.time));});
}
function momentButton(item) {
  const button = btn('',() => openInspector(item.object.id),'moment');
  add(button,label(item.clock + ' / ' + item.kind),el('time',stamp(item.time),{dateTime:item.time}),el('strong',title(item.object)),badge(item.object.status));
  return button;
}
function renderSequence(main) {
  const section = region('Sequence of recorded clocks','sequence-page');
  add(section,el('p','A report being published, a capture being retrieved, and an event happening are separate moments. The sequence below uses only recorded timestamps.',{class:'section-intro'}));
  const list = el('div',null,{class:'sequence-list'});
  for (const moment of timeMoments()) list.append(momentButton(moment));
  if (!list.children.length) list.append(el('p','No dated objects in this case.',{class:'empty-note'}));
  section.append(list);
  const undated = [...current.events,...current.observations,...current.captures].filter(object => !object.event_start && !object.observed_at && !object.published_at && !object.retrieved_at);
  if (undated.length) {
    add(section,label('Time not recorded'),el('div',null,{class:'undated-list'}));
    undated.forEach(object => section.lastChild.append(recordButton('records',object)));
  }
  main.append(section);
}
function renderEvidenceChains(main) {
  const section = region('Evidence chains','chains-page');
  add(section,el('p','Follow native source → capture → claim references. These paths show custody and dependence; several captures can still be one evidence lineage.',{class:'section-intro'}));
  const chains = el('div',null,{class:'chains'});
  for (const source of current.sources) {
    const chain = el('article',null,{class:'chain'});
    const captures = current.captures.filter(item => (item.source_ids || []).includes(source.id));
    const claims = current.claims.filter(item => (item.capture_ids || []).some(id => captures.some(capture => capture.id === id)));
    add(chain,recordButton('sources',source,'chain-source'));
    const capturesColumn = el('div',null,{class:'chain-column'});
    add(capturesColumn,label('Recorded captures'));
    captures.forEach(object => capturesColumn.append(recordButton('captures',object)));
    if (!captures.length) capturesColumn.append(el('p','No capture references this source.'));
    const claimsColumn = el('div',null,{class:'chain-column'});
    add(claimsColumn,label('Claims citing those captures'));
    claims.forEach(object => claimsColumn.append(recordButton('claims',object)));
    if (!claims.length) claimsColumn.append(el('p','No claim cites these captures.'));
    add(chain,capturesColumn,claimsColumn);
    chains.append(chain);
  }
  if (!chains.children.length) chains.append(el('p','No source chain recorded.',{class:'empty-note'}));
  section.append(chains);
  const relations = region('Declared relationships only','declared-relations');
  add(relations,el('p','Similar names and co-occurrence create no link here.',{class:'section-intro'}));
  for (const relation of current.relations) {
    const row = el('div',null,{class:'relation-row'});
    const from = findRecord(relation.from_id), to = findRecord(relation.to_id);
    add(row,btn(from ? title(from.object) : 'Unresolved ' + relation.from_id,() => openInspector(relation.from_id)),add(el('div'),label(value(relation.relation_type)),badge(relation.status),el('span','→',{class:'relation-arrow'})),btn(to ? title(to.object) : 'Unresolved ' + relation.to_id,() => openInspector(relation.to_id)),btn('Inspect relation',() => openInspector(relation.id),'text-action'));
    relations.append(row);
  }
  if (!current.relations.length) relations.append(el('p','No typed relations recorded.',{class:'empty-note'}));
  add(main,section,relations);
}
function renderChallenge(main) {
  const section = region('Explanations under challenge','challenge-page');
  add(section,el('p','Compare recorded hypotheses without turning their visual weight into evidentiary weight.',{class:'section-intro'}));
  const grid = el('div',null,{class:'hypothesis-grid'});
  for (const object of current.hypotheses) {
    const card = el('article',null,{class:'hypothesis'});
    add(card,label(object.id),el('h3',title(object)),badge(object.status),el('p',value(object.uncertainty),{class:'uncertainty-text'}),el('p',refs(object).length + ' exact native reference' + (refs(object).length === 1 ? '' : 's'),{class:'micro-label'}),btn('Inspect hypothesis ↗',() => openInspector(object.id),'text-action'));
    grid.append(card);
  }
  if (!grid.children.length) grid.append(el('p','No hypotheses recorded.',{class:'empty-note'}));
  section.append(grid);
  const lower = el('div',null,{class:'challenge-lower'});
  for (const [name,kind] of [['Contradictions','contradictions'],['Publication and decision boundaries','blockers']]) {
    const panel = region(name,'challenge-list');
    if (current[kind].length) current[kind].forEach(object => panel.append(recordButton(kind,object)));
    else panel.append(el('p','None recorded.',{class:'empty-note'}));
    lower.append(panel);
  }
  section.append(lower);
  main.append(section);
}
function renderSources(main) {
  const section = region('Source and capture ledger','sources-page');
  add(section,el('p','Recorded origin, preservation, and retrieval are available for inspection. No URL or file opens automatically.',{class:'section-intro'}));
  const search = el('input',null,{type:'search',id:'source-search',placeholder:'Find a source or capture','aria-label':'Find a source or capture'});
  const result = el('div',null,{class:'source-results'});
  const update = () => {
    const query = search.value.toLowerCase();
    result.replaceChildren();
    for (const kind of ['sources','captures']) for (const object of current[kind]) {
      if (JSON.stringify(object).toLowerCase().includes(query)) result.append(recordButton(kind,object,'source-entry'));
    }
    if (!result.children.length) result.append(el('p','No matching source or capture.',{class:'empty-note'}));
  };
  search.addEventListener('input',update);
  add(section,search,result);
  update();
  main.append(section);
}
function stableJSON(value){if(Array.isArray(value))return '['+value.map(stableJSON).join(',')+']';if(value&&typeof value==='object')return '{'+Object.keys(value).sort().map(k=>JSON.stringify(k)+':'+stableJSON(value[k])).join(',')+'}';return JSON.stringify(value);}
function changes() {
  if (!current || !baseline) return [];
  const rows = [];
  for (const kind of GROUPS) {
    const old = new Map(baseline[kind].map(object => [object.id,object]));
    const now = new Map(current[kind].map(object => [object.id,object]));
    for (const [id,object] of now) {
      const prior = old.get(id);
      if (!prior || stableJSON(prior) !== stableJSON(object)) rows.push({kind,id,state:prior ? 'CHANGED' : 'NEW',prior,current:object});
    }
    for (const [id,object] of old) if (!now.has(id)) rows.push({kind,id,state:'NO LONGER REPRESENTED',prior:object,current:null});
  }
  return rows;
}
function renderCompare(main) {
  const section = region('What differs between two records','compare-page');
  add(section,el('p','This compares exact typed IDs and fields. It does not decide whether a difference is material, true, or decision-relevant.',{class:'section-intro'}));
  if (!baseline) {
    const note = el('div',null,{class:'baseline-empty'});
    add(note,label('No baseline selected'),el('h3','Set a point of comparison.'),el('p','Open a baseline JSON from Case files, or explore the synthetic Harbor Lantern case with its paired baseline.'),btn('Open case files',() => { $('case-controls').open = true; $('case-controls').querySelector('summary').focus(); },'primary-action'));
    section.append(note);main.append(section);return;
  }
  add(section,el('p','Baseline: ' + baseline.case_id + '  /  Current: ' + current.case_id,{class:'comparison-ids'}));
  if (baseline.case_id !== current.case_id) add(section,el('p','Different case IDs are shown explicitly; no identity merge is inferred.',{class:'caution'}));
  const rows = changes();
  const summary = el('div',null,{class:'delta-summary'});
  for (const state of ['NEW','CHANGED','NO LONGER REPRESENTED']) add(summary,add(el('div'),el('strong',rows.filter(row => row.state === state).length),label(state)));
  section.append(summary);
  if (!rows.length) section.append(el('p','No typed object differences found.',{class:'empty-note'}));
  for (const row of rows) {
    const block = el('details',null,{class:'delta-entry'});
    add(block,add(el('summary'),badge(row.state),el('strong',row.current ? title(row.current) : title(row.prior)),el('span',row.kind + ' / ' + row.id,{class:'micro-label'})));
    const pair = el('div',null,{class:'delta-pair'});
    const before = add(el('div'),label('Baseline'),row.prior ? exactRecord(row.kind,row.prior,false) : el('p','Not represented in baseline.'));
    const after = add(el('div'),label('Current'),row.current ? exactRecord(row.kind,row.current,false) : el('p','No longer represented in current case.'));
    add(pair,before,after);
    block.append(pair);
    section.append(block);
  }
  main.append(section);
}
function switchLens(name) {
  if (!current) return;
  active = name;
  closeInspector(false);
  render();
  $('main').focus({preventScroll:true});
  window.scrollTo({top:0,behavior:'instant'});
}
function renderNav() {
  const nav = $('nav');
  nav.replaceChildren();
  nav.hidden = !current;
  if (!current) return;
  LENSES.forEach((name,index) => {
    const button = btn(name,() => switchLens(name));
    button.setAttribute('aria-current',name === active ? 'page' : 'false');
    button.prepend(el('span',String(index+1).padStart(2,'0'),{class:'nav-number'}));
    nav.append(button);
  });
}
function render() {
  renderNav();
  const main = $('main');
  main.replaceChildren();
  if (!current) { renderEmpty(main); return; }
  main.append(caseHeader());
  if (active === 'Situation') renderSituation(main);
  if (active === 'Sequence') renderSequence(main);
  if (active === 'Evidence chains') renderEvidenceChains(main);
  if (active === 'Challenge') renderChallenge(main);
  if (active === 'Sources') renderSources(main);
  if (active === 'Compare') renderCompare(main);
}
function loadSample() {
  current = validate(structuredClone(OBS_SAMPLE.current));
  baseline = validate(structuredClone(OBS_SAMPLE.baseline));
  sourceMode = 'synthetic';active = 'Situation';
  closeInspector(false);
  render();
  $('status').textContent = 'SYNTHETIC Harbor Lantern · dated fixture only. No live verification or background feed.';
  $('case-controls').open = false;
}
$('case').addEventListener('change',event => load(event.target.files[0]));
$('baseline').addEventListener('change',event => load(event.target.files[0],true));
$('sample').addEventListener('click',loadSample);
$('clear').addEventListener('click',() => {
  current = null;baseline = null;sourceMode = '';active = 'Situation';
  $('case').value = '';$('baseline').value = '';
  closeInspector(false);render();$('status').textContent = 'Private case data cleared from memory.';
  $('case-controls').open = false;
});
$('skin').addEventListener('change',event => document.body.dataset.skin = event.target.value);
document.addEventListener('keydown',event => { if (event.key === 'Escape' && !$('inspector').hidden) closeInspector(true); });
render();



