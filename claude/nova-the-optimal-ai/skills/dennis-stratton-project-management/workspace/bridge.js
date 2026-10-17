(function(){
"use strict";var tokenKey="project-bridge-token:"+location.origin+location.pathname,token=location.hash.slice(1);try{if(token)sessionStorage.setItem(tokenKey,token);else token=sessionStorage.getItem(tokenKey)||""}catch(_){}var S={projects:[],views:{},store:"",storeSource:""},station=null,project=null,sourceId=null,client="tab-main",quitting=false,leaseTimer=null,saveTimer=null,viewTail=Promise.resolve();history.replaceState(null,"",location.pathname);
var $=function(id){return document.getElementById(id)}, enc=encodeURIComponent, txt=function(e,v){if(e)e.textContent=v==null?"":String(v)}, show=function(e,v){if(e)e.hidden=!v};
async function api(path,method,body){var r=await fetch(path,{method:method||"GET",headers:{"X-Companion-Token":token,"Content-Type":"application/json"},body:body?JSON.stringify(body):undefined,cache:"no-store"});var d=await r.json();if(!r.ok)throw Error(d.error||"Local request failed.");return d}
function setStatus(m){txt($("status"),m)}
function allNodes(p){return (p.hierarchy||[]).concat(p.work_packages||[])}
function name(n){return n.label||n.outcome||n.id}
function selectedProjectId(p){return p.project&&p.project.id}
function defaultProjectId(projects){var available=projects.filter(function(p){return String((p.project||{}).status||"").toLowerCase()!=="closed"}),active=available.filter(function(p){return String((p.project||{}).status||"").toLowerCase()==="active"}),rows=(active.length?active:available.length?available:projects).slice();rows.sort(function(a,b){return (Date.parse((b.project||{}).updated_at||"")||0)-(Date.parse((a.project||{}).updated_at||"")||0)});return rows.length?selectedProjectId(rows[0]):null}
function renderProjects(){
 var root=$("projects");root.replaceChildren();var q=$("search").value.toLowerCase(),rows=S.projects.filter(function(p){var n=p.project||{};return (n.name+" "+n.outcome+" "+n.owner).toLowerCase().includes(q)});
 rows.forEach(function(p){var n=p.project||{},b=document.createElement("button");b.type="button";b.className="projectCard";b.dataset.id=n.id;var strong=document.createElement("strong");strong.textContent=n.name||n.id;var span=document.createElement("span");span.textContent=n.outcome||"Outcome not stated";var small=document.createElement("small");small.textContent=n.status||"Status not stated";b.append(strong,span,small);b.onclick=function(){openProject(n.id)};root.append(b)});
 txt($("projectCount"),S.projects.length+" projects");show($("emptyPortfolio"),S.projects.length===0);var source=S.storeSource==="nova-path-selectors"?"Nova project registry":S.storeSource==="saved-folder-selection"?"Saved folder choice":S.storeSource==="explicit-folder-selection"?"Selected project folder":"Selected project folder";txt($("storeLabel"),S.store?"Current source · "+source+"\n"+S.store:"");txt($("activeStore"),S.store?"SOURCE · "+source+" · "+S.store:"Source unavailable");
}
async function openProject(id,writeAfterOpen){
 try{
  var d=await api("/api/project?id="+enc(id));project=d.project;var view=S.views[id]||{};
  station=view.station_id||project.current.active_commitment_id||null;sourceId=view.source_id||null;
  if(view.skin){$("skin").value=view.skin;document.documentElement.dataset.theme=view.skin}
  renderProject();show($("welcome"),false);show($("portfolio"),false);show($("projectView"),true);
  if(sourceId){var source=(project.evidence||[]).find(function(x){return x.id===sourceId});if(source)await openSource(project,source,true);else sourceId=null}
  await document.fonts.ready;await new Promise(function(resolve){requestAnimationFrame(function(){window.scrollTo(0,Number(view.scroll_y)||0);resolve()})});
  if(writeAfterOpen!==false)await persistViewNow();var opened=project.project||{};setStatus("Opened "+String(opened.status||"status not recorded").toLowerCase()+" project · "+(opened.name||opened.id)+".")
 }catch(e){setStatus(e.message)}
}
function renderProject(){
 var p=project.project||{},c=project.current||{};txt($("projectName"),p.name||p.id);txt($("purposeConnection"),c.purpose_connection||"Purpose connection is not stated in the current record.");txt($("nextAction"),c.next_action||"No next action is recorded.");txt($("nextDecision"),c.next_decision||"No next decision is recorded.");txt($("projectIdentity"),p.id);txt($("projectOutcome"),p.outcome);txt($("projectStatus"),p.status);txt($("owner"),"Owner: "+(p.owner||"not stated"));txt($("sourceTime"),"Updated: "+(p.updated_at||"not stated"));txt($("asOf"),"Record as of "+(c.as_of||"date not stated"));
 var route=$("route");route.replaceChildren();var hier=project.hierarchy||[],work=project.work_packages||[],all=allNodes(project);
 function kids(id){return hier.filter(function(x){return x.parent_id===id}).concat(work.filter(function(x){return x.parent_id===id}))}
 function node(x,depth){var b=document.createElement("button");b.className="routeNode depth-"+Math.min(depth,5)+(station===x.id?" selected":"");b.type="button";b.dataset.route=x.id;var small=document.createElement("small");small.textContent=(x.kind||"commitment")+" · "+x.id;var strong=document.createElement("strong");strong.textContent=name(x);var span=document.createElement("span");span.textContent=(x.status||"not stated")+" · "+(x.purpose||x.next_action||"Purpose not stated");b.append(small,strong,span);b.onclick=function(){station=x.id;renderProject();saveView()};route.append(b);kids(x.id).forEach(function(child){node(child,depth+1)})}
 hier.filter(function(x){return !x.parent_id||!hier.some(function(y){return y.id===x.parent_id})}).forEach(function(x){node(x,0)});
 work.filter(function(x){return !all.some(function(y){return y.id===x.parent_id})}).forEach(function(x){node(x,0)});
 var chosen=all.find(function(x){return x.id===station})||all.find(function(x){return x.id===project.current.active_commitment_id})||all[0];station=chosen?chosen.id:null;
 var box=$("inspectorBody");box.replaceChildren();if(!chosen){box.textContent="No commitment is available in this record.";return}
 var criteria=(project.exit_criteria||[]).filter(function(x){return x.owner_id===chosen.id||(chosen.acceptance_criteria_ids||[]).includes(x.id)});
 var evIds=new Set(criteria.flatMap(function(x){return x.evidence_ids||[]})), evidence=(project.evidence||[]).filter(function(x){return evIds.has(x.id)});
 function heading(t){var h=document.createElement("h3");h.textContent=t;box.append(h)}
 function para(t){var e=document.createElement("p");e.textContent=t||"Not stated in this source.";box.append(e)}
 txt($("inspectorTitle"),name(chosen));var label=document.createElement("small");label.className="eyebrow";label.textContent="SELECTED COMMITMENT · "+(chosen.status||"status unknown");box.append(label);
 var h=document.createElement("h2");h.textContent=name(chosen);box.append(h);
 heading("What this enables");para(chosen.purpose||chosen.outcome);
 heading("Next practical move");para(chosen.next_action||project.current.next_action);
 heading("Place in the route");para((project.current.path||[]).join(" › "));
 heading("Declared dependencies");var deps=chosen.dependency_ids||[];if(!deps.length)para("No dependencies are declared.");deps.forEach(function(d){var dep=all.find(function(x){return x.id===d}),b=document.createElement("button");b.type="button";b.className="textLink";b.textContent=(dep?name(dep):d)+" · "+(dep?dep.status:"reference not found");b.onclick=function(){station=d;renderProject();saveView()};box.append(b)});
 heading("Completion evidence");if(!criteria.length)para("No acceptance criteria are linked.");criteria.forEach(function(c){para(c.status+" · "+c.description)});evidence.forEach(function(e){var b=document.createElement("button");b.type="button";b.className="sourceButton";b.textContent="Read source: "+e.id+" — "+(e.claim||e.level||"Evidence");b.onclick=function(){openSource(project,e)};box.append(b)});
 renderWarnings();

}
async function openSource(p,e,restoring){
 try{
  var d=await api("/api/source?project="+enc(p.project.id)+"&evidence="+enc(e.id));
  sourceId=e.id;$("sourcePanel").hidden=false;txt($("sourceTitle"),e.claim||e.id);
  txt($("sourceMeta"),(e.level||"Evidence")+" · "+(e.observed_at||"date not stated")+" · "+(d.locator||e.locator||"No source locator"));
  var c=$("sourceContent");c.replaceChildren();
  if(d.kind==="text"){c.textContent=d.text||""}
  else if(d.kind==="original"){
   var note=document.createElement("p");note.textContent="This is the exact supplied original. Project Bridge does not extract or alter its contents.";c.append(note);
   var a=document.createElement("a");a.href="#";a.textContent="Download exact original";a.className="sourceButton";a.download=d.name||"source-original";a.addEventListener("click",async function(ev){ev.preventDefault();try{var r=await fetch("/api/source-download?project="+enc(p.project.id)+"&evidence="+enc(e.id),{headers:{"X-Companion-Token":token},cache:"no-store"});if(!r.ok)throw Error("The original could not be downloaded. Refresh the project and try again.");var blob=await r.blob(),url=URL.createObjectURL(blob),dl=document.createElement("a");dl.href=url;dl.download=d.name||"source-original";document.body.append(dl);dl.click();dl.remove();setTimeout(function(){URL.revokeObjectURL(url)},1500)}catch(err){setStatus(err.message)}});c.append(a)
  } else if(d.kind==="missing"){
   c.append(document.createTextNode(d.reason||"This source file is missing from its recorded location."));
   var actions=document.createElement("div");actions.className="source-actions";
   var refreshButton=document.createElement("button");refreshButton.type="button";refreshButton.textContent="Refresh project";refreshButton.onclick=refresh;actions.append(refreshButton);
   var reconnect=document.createElement("button");reconnect.type="button";reconnect.textContent="Reconnect project folder";reconnect.onclick=$("chooseStore").onclick;actions.append(reconnect);c.append(actions)
  } else {c.textContent=d.reason||"This locator is descriptive; there is no readable local original at that location."}
  if(!restoring){saveView();$("sourcePanel").scrollIntoView({block:"start",behavior:"instant"})}
 }catch(err){setStatus(err.message)}
}
function captureView(){return {project_id:project?project.project.id:"",station_id:station||"",source_id:sourceId||null,skin:$("skin").value,filter:"all",scroll_y:Math.max(0,Math.round(window.scrollY))}}
function persistViewNow(){
 if(!project)return Promise.resolve(null);
 var payload=captureView();
 viewTail=viewTail.catch(function(){}).then(function(){return api("/api/view","POST",payload)}).then(function(d){S.views[project.project.id]=d.view;renderChanges(d.changes);return d});
 return viewTail
}
function saveView(){if(!project||quitting)return;clearTimeout(saveTimer);saveTimer=setTimeout(function(){persistViewNow().catch(function(e){setStatus("Reading position was not saved: "+e.message)})},350)}
function renderChanges(changes){
 var box=$("changePanel");box.replaceChildren();
 if(!changes||!changes.length){show(box,false);return}
 var h=document.createElement("strong");h.textContent="This project has changed since the earlier comparison.";box.append(h);
 var intro=document.createElement("p");intro.textContent="Earlier and current values from the native record:";box.append(intro);
 function row(label,before,after){if(before===after)return;var r=document.createElement("div");r.className="change-row";var l=document.createElement("strong"),b=document.createElement("span"),a=document.createElement("span");l.textContent=label;b.textContent="Earlier: "+(before==null||before===""?"Not stated":String(before));a.textContent="Current: "+(after==null||after===""?"Not stated":String(after));r.append(l,b,a);box.append(r)}
 changes.forEach(function(item){
  var b=item.before||{},a=item.after||{};
  if(item.area==="Purpose and scope"){b=b.project||{};a=a.project||{};row("Project outcome",b.outcome,a.outcome);row("Project status",b.status,a.status);row("Updated date",b.updated_at,a.updated_at)}
  if(item.area==="Current route and next action"){b=b.current||{};a=a.current||{};row("Purpose connection",b.purpose_connection,a.purpose_connection);row("Next action",b.next_action,a.next_action);row("Next decision",b.next_decision,a.next_decision);row("Record date",b.as_of,a.as_of)}
  if(item.area==="Completion evidence"){b=b.forecast||{};a=a.forecast||{};row("Timing basis",b.basis,a.basis);row("Next forecast update",b.next_update,a.next_update)}
 });
 show(box,true)
}
function renderWarnings(){
 var diag=$("routeWarnings");diag.replaceChildren();var forecast=project.forecast||{};
 if(forecast.lower==null||forecast.upper==null){
  var card=document.createElement("div");card.className="forecast-card";var h=document.createElement("strong");h.textContent="Timing remains unknown";card.append(h);
  [["Basis",forecast.basis],["Confidence",forecast.confidence],["Baseline",forecast.baseline],["Next update",forecast.next_update]].forEach(function(pair){if(pair[1]){var para=document.createElement("p");para.textContent=pair[0]+": "+pair[1];card.append(para)}});
  if(!forecast.basis){var q=document.createElement("p");q.textContent="No timing range is estimated. Unknown does not mean zero duration.";card.append(q)}
  diag.append(card)
 }
 (project.warnings||[]).filter(function(w){return w.code!=="UNKNOWN_FORECAST"}).forEach(function(w){var x=document.createElement("p");x.textContent=(w.code||"Record note")+": "+(w.message||"");diag.append(x)});
 show(diag,diag.childElementCount>0)
}
async function refresh(){try{var d=await api("/api/state");S.projects=d.projects||[];S.store=d.store||"";S.storeSource=d.store_source||"";S.views=(d.view&&d.view.projects)||{};renderProjects();if(project){var id=project.project.id;await openProject(id);setStatus("Refreshed from the current native project record.")}else{show($("welcome"),true);setStatus("Project records refreshed.")}}catch(e){setStatus(e.message)}}
async function demo(){try{var d=await api("/api/demo");project=d.project;station="WP-INSTALL";renderProject();show($("welcome"),false);show($("portfolio"),false);show($("projectView"),true);setStatus("Fictional community exhibition walkthrough. Nothing here is a real commitment.");saveView()}catch(e){setStatus(e.message)}}
function browse(){show($("projectView"),false);show($("welcome"),true);show($("portfolio"),true)}
async function exit(){
 if(quitting)return;quitting=true;clearTimeout(saveTimer);if(leaseTimer)clearInterval(leaseTimer);
 try{await viewTail;if(project)await persistViewNow()}catch(e){setStatus("The reader could not save the last reading position: "+e.message)}
 var stopped=false,lastError=null;
 for(var n=0;n<8;n++){try{await api("/api/exit","POST",{client:client});stopped=true;break}catch(e){lastError=e;if(!String(e.message).includes("reading-position save"))break;await new Promise(function(resolve){setTimeout(resolve,100)})}}
 if(!stopped){quitting=false;leaseTimer=setInterval(function(){api("/api/lease","POST",{client:client}).catch(function(){})},30000);setStatus("The local reader did not confirm Exit. Wait for the reading-position save to finish, then try again. "+(lastError?lastError.message:""));return}
 document.querySelectorAll("button,input,select,a").forEach(function(x){x.disabled=true;x.removeAttribute("href")});
 show($("welcome"),false);show($("portfolio"),false);show($("projectView"),false);show($("closedScreen"),true)
}

$("search").oninput=renderProjects;$("refresh").onclick=refresh;$("exit").onclick=exit;$("chooseStore").onclick=async function(){try{var d=await api("/api/pick-store","POST",{});if(d.selected){await refresh();setStatus("Project folder selected.")}}catch(e){setStatus(e.message)}};
["walkButton","walkWelcome","walkEmpty"].forEach(function(id){$(id).onclick=demo});["browseWelcome","showPortfolio"].forEach(function(id){$(id).onclick=browse});["chooseEmpty","chooseWelcome"].forEach(function(id){$(id).onclick=$("chooseStore").onclick});
$("closeSource").onclick=function(){$("sourcePanel").hidden=true;sourceId=null;saveView();var n=document.querySelector("[data-route=\""+station+"\"]");if(n)n.focus()};
$("skin").onchange=function(){document.documentElement.dataset.theme=this.value;saveView()};
window.addEventListener("scroll",function(){if(project)saveView()},{passive:true});
api("/api/lease","POST",{client:client}).catch(function(){});
leaseTimer=setInterval(function(){if(!quitting)api("/api/lease","POST",{client:client}).catch(function(){setStatus("Local connection lost. Reopen the Project Bridge launcher.")})},30000);
api("/api/state").then(async function(d){S.projects=d.projects||[];S.store=d.store||"";S.storeSource=d.store_source||"";S.views=(d.view&&d.view.projects)||{};renderProjects();var last=d.view&&d.view.last_project;var saved=last&&S.projects.some(function(item){return item.project&&item.project.id===last});var target=saved?last:defaultProjectId(S.projects);if(target){await openProject(target,true);if(!saved){var opened=project.project||{};setStatus("No saved reading position; opened the most recently updated "+String(opened.status||"status not recorded").toLowerCase()+" project: "+(opened.name||opened.id)+".")}}else{show($("welcome"),true);setStatus("No project records are available in "+(d.store||"the selected folder")+".")}}).catch(function(e){setStatus("Project data could not be opened: "+e.message)});

})();







