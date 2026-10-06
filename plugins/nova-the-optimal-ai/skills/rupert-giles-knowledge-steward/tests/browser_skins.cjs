// Material assets and label separation are executable integration checks, not visual approval.
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os'),cp=require('node:child_process');
let pw;try{pw=require(process.env.PLAYWRIGHT_MODULE||'playwright')}catch{pw=require('C:/Users/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright')}
(async()=>{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'giles-skins-')),source=path.join(root,'source'),catalog=path.join(root,'catalog.json');fs.mkdirSync(source);fs.writeFileSync(path.join(source,'INDEX.md'),'Actual fixture source.\n');
 const names=['Archive Loom Retained Collection','Our Recipe Collection','Our Wiki','Personal AI Archive','Research Library','Retained Knowledge Packets','RPG Library','Scrapbook'];
 const stores=names.map((name,i)=>({id:'store-'+i,name,location:source,kind:'folder',role:'unresolved',lifecycle:'retained',inspection:'description_reviewed',summary:'Synthetic source fixture.',aliases:[],topics:['shared subject'],use_when:[],entrypoint:'INDEX.md',provenance:'Synthetic fixture',owner:'Test',favorite:false,sections:[]}));
 fs.writeFileSync(catalog,JSON.stringify({schema:'giles-knowledge-catalog/v1',revision:0,stores}));const before=fs.readFileSync(catalog);
 const server=cp.spawn(process.env.PYTHON||'C:/Python314/python.exe',['-B','-X','utf8',path.resolve(__dirname,'../scripts/giles.py'),'--catalog',catalog,'serve','--port','0','--no-browser']);
 let browser,checks=0;
 try{
  const url=await new Promise((resolve,reject)=>{let err='';const timer=setTimeout(()=>reject(Error(err||'Startup timeout')),10000);server.stderr.on('data',d=>err+=d);server.stdout.on('data',d=>{const m=d.toString().match(/http:\/\/127\.0\.0\.1:\d+\//);if(m){clearTimeout(timer);resolve(m[0])}});server.on('error',reject)});
  browser=await pw.chromium.launch({headless:true,executablePath:process.env.CHROMIUM_EXECUTABLE||'C:/Users/user/AppData/Local/ms-playwright/chromium-1187/chrome-win/chrome.exe'});const page=await browser.newPage(),errors=[],requests=[];
  page.on('pageerror',e=>errors.push(String(e)));page.on('console',m=>{if(m.type()==='error')errors.push(m.text())});page.on('request',r=>requests.push(r.url()));
  await page.goto(url);await page.locator('.map-node').first().waitFor();
  const assets=await page.evaluate(async()=>{const result=[];for(const name of ['atlas','blackglass','mirrorloop']){const img=new Image();img.src='/assets/'+name+'-material.png';await img.decode();result.push({name,width:img.naturalWidth,height:img.naturalHeight})}return result});assert.ok(assets.every(a=>a.width>1000&&a.height>500),JSON.stringify(assets));checks++;
  for(const theme of ['atlas','circuit','relay'])for(const width of [390,760,900,1200,1600]){
   await page.setViewportSize({width,height:900});await page.locator('#theme').selectOption(theme);
   const state=await page.evaluate(()=>{const boxes=[...document.querySelectorAll('.map-node')].map(e=>e.getBoundingClientRect());const overlaps=[];for(let i=0;i<boxes.length;i++)for(let j=i+1;j<boxes.length;j++){const a=boxes[i],b=boxes[j];if(a.right>b.left+1&&b.right>a.left+1&&a.bottom>b.top+1&&b.bottom>a.top+1)overlaps.push([i,j])}return {theme:document.documentElement.dataset.theme,overlaps,overflow:document.documentElement.scrollWidth-innerWidth}});
   assert.equal(state.theme,theme);assert.deepEqual(state.overlaps,[],JSON.stringify({theme,width,...state}));assert.equal(state.overflow,0);checks++;
  }
  await page.locator('[data-map-id=store-6]').click();await page.locator('#detail h2').filter({hasText:'RPG Library'}).waitFor();assert.equal(await page.locator('.map-node[aria-pressed=true]').getAttribute('data-map-id'),'store-6');assert.equal(await page.locator('#source-view .sample').textContent(),'Actual fixture source.\n');checks++;
  await page.locator('#theme').selectOption('circuit');await page.reload();await page.locator('.map-node').first().waitFor();assert.equal(await page.locator('#theme').inputValue(),'circuit');assert.equal(await page.locator('html').getAttribute('data-theme'),'circuit');checks++;
  await page.emulateMedia({reducedMotion:'reduce'});assert.equal(await page.locator('.map-node').first().evaluate(e=>getComputedStyle(e).transitionDuration),'0s');checks++;
  assert.deepEqual(fs.readFileSync(catalog),before);assert.equal(fs.readFileSync(path.join(source,'INDEX.md'),'utf8'),'Actual fixture source.\n');assert.deepEqual(errors,[]);assert.ok(requests.every(u=>u.startsWith(url)));checks++;
  console.log(`${checks} material/geometry integration checks passed; images decoded, controls selected real source contents, preferences persisted.`);
 }finally{if(browser)await browser.close();server.kill();await new Promise(r=>server.exitCode!==null||server.signalCode!==null?r():server.once('exit',r));const target=path.resolve(root);assert.ok(path.dirname(target)===path.resolve(os.tmpdir())&&path.basename(target).startsWith('giles-skins-'));fs.rmSync(target,{recursive:true,force:true})}
})().catch(e=>{console.error(e);process.exitCode=1});
