const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');
const root = __dirname;
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
const sample = JSON.parse(fs.readFileSync(path.join(root, 'sample.json'), 'utf8'));
const nodes = new Map();
const requests = [];
let exportedBlob, exportedName;
function element(selector) {
  if (!nodes.has(selector)) {
    const obj = {
      innerHTML: '', textContent: '', value: '', className: '', disabled: false, open: false,
      dataset: {}, clicks: 0, click() { this.clicks++; },
      showModal() { this.open = true; }, close() { this.open = false; },
      querySelectorAll(query) {
        if (query !== 'button') return [];
        const attribute = selector === '#nav' ? 'view' : 'patch';
        if (this._childHTML !== this.innerHTML) {
          this._childHTML = this.innerHTML;
          this._children = [...this.innerHTML.matchAll(new RegExp('data-' + attribute + '="([^"]+)"', 'g'))]
            .map(match => ({dataset: {[attribute]: match[1]}}));
        }
        return this._children;
      }
    };
    nodes.set(selector, obj);
  }
  return nodes.get(selector);
}
const ctx = {
  window:{confirm(){return true},addEventListener(){}},
  document: {
    body: {dataset: {skin: 'strata'}}, querySelector: element, querySelectorAll: () => [],
    createElement: () => ({click() { exportedName = this.download; }})
  },
  location: {hash: '', pathname: '/'}, history: {replaceState() {}}, URLSearchParams,
  URL: {createObjectURL(blob) { exportedBlob = blob; return 'blob:working'; }, revokeObjectURL() {}},
  Blob, setTimeout(fn) { fn(); },
  fetch: async (url, options) => {
    requests.push({url, options});
    return {ok: true, json: async () => url === '/api/sample' ? sample :
      url === '/api/validate' ? {valid: true, errors: [], scope: 'native structure'} : {authenticated: true}};
  }
};
vm.createContext(ctx);
vm.runInContext(script, ctx);
const state = expression => vm.runInContext(expression, ctx);
async function main() {
  assert.match(element('#content').innerHTML, /Explore labeled example/);
  element('#open').onclick();
  assert.equal(element('#file').clicks, 1);
  await element('#sample').onclick();
  assert.match(element('#content').innerHTML, /The fictional archive export requires a manual request/);
  assert.match(element('#status').textContent, /Synthetic/);
  assert.ok(state('rawDocument').includes('"ledger_id"'));

  const native = JSON.stringify(sample, null, 2).replace(/}\s*$/, ',\n  "owner_extra": {"counter": 9007199254740993, "ticket": "CUSTODY"}\n}');
  const fileInput = {files: [{name: 'native.json', size: Buffer.byteLength(native), text: async () => native}], value: 'chosen'};
  await element('#file').onchange({target: fileInput});
  assert.equal(fileInput.value, '');
  assert.equal(state('rawDocument'), native);
  assert.match(element('#source').textContent, /native.json/);
  element('#edit').onclick();
  assert.equal(element('#nativejson').value, native);
  assert.equal(element('#editor').open, true);
  const edited = native.replace('Synthetic archive-access answer', 'Edited archive-access answer');
  element('#nativejson').value = edited;
  element('#apply').onclick();
  assert.equal(element('#editor').open, false);
  assert.equal(state('rawDocument'), edited);
  assert.match(element('#content').innerHTML, /Edited archive-access answer/);
  assert.equal(state('workingDirty'), true);
  ctx.window.confirm = () => false;
  await element('#sample').onclick();
  assert.equal(state('rawDocument'), edited, 'Canceled example replacement preserves unsaved text');
  await element('#file').onchange({target: {files: [{name:'replacement.json',size:native.length,text:async()=>native}],value:''}});
  assert.equal(state('rawDocument'), edited, 'Canceled import preserves unsaved text');
  ctx.window.confirm = () => true;

  await element('#validate').onclick();
  const validationRequest = requests.findLast(r => r.url === '/api/validate');
  assert.equal(validationRequest.options.body, edited);
  assert.equal(element('#validation').open, true);
  assert.match(element('#validationbody').textContent, /^PASS/);
  element('#download').onclick();
  assert.equal(await exportedBlob.text(), edited);
  assert.equal(state('workingDirty'), false, 'An explicit download clears the edited flag');
  assert.equal(exportedName, sample.ledger_id + '-working.json');
  assert.match(await exportedBlob.text(), /9007199254740993/);

  const before = state('rawDocument');
  element('#edit').onclick();
  element('#nativejson').value = '{broken';
  element('#apply').onclick();
  assert.equal(element('#editor').open, true);
  assert.equal(state('rawDocument'), before);
  assert.match(element('#editorerror').textContent, /JSON/);
  element('#nativejson').value = '{"format":"wrong"}';
  element('#apply').onclick();
  assert.equal(state('rawDocument'), before);
  assert.match(element('#editorerror').textContent, /Unsupported/);
  element('#editor').close();

  const malformed = edited.replace('"patches": [', '"patches": {"wrong": [').replace(/]\s*,\s*"probes":/,' ]}, "probes":');
  assert.doesNotThrow(() => JSON.parse(malformed));
  await element('#file').onchange({target: {files: [{name: 'bad.json', size: malformed.length, text: async () => malformed}], value: ''}});
  assert.match(element('#content').innerHTML, /Native structure needs repair/);
  assert.match(element('#content').innerHTML, /patches must be an array/);
  assert.equal(state('rawDocument'), malformed);
  await element('#validate').onclick();
  assert.equal(requests.findLast(r => r.url === '/api/validate').options.body, malformed);

  const two = structuredClone(sample);
  two.patches.push({...two.patches[0], id: 'P2', scope: 'Second mechanism'});
  const twoText = JSON.stringify(two);
  await element('#file').onchange({target: {files: [{name: 'two.json', size: twoText.length, text: async () => twoText}], value: ''}});
  element('#patch-find').value = 'P2';
  element('#patch-find').oninput();
  assert.match(element('#patch-list').innerHTML, /P2/);
  assert.doesNotMatch(element('#patch-list').innerHTML, /data-patch="0"/);
  element('#patch-list').querySelectorAll('button')[0].onclick();
  assert.equal(element('#patch-find').value, 'P2');
  assert.match(element('#content').innerHTML, /P2 · exact proposed change/);
  element('#skin').onchange({target: {value: 'switchyard'}});
  assert.equal(ctx.document.body.dataset.skin, 'switchyard');
  element('#nav').querySelectorAll('button').find(b => b.dataset.view === 'signals').onclick();
  assert.match(element('#content').innerHTML, /Possible changes/);
  element('#nav').querySelectorAll('button').find(b => b.dataset.view === 'sources').onclick();
  assert.match(element('#content').innerHTML, /Fictional archive notice/);
  element('#nav').querySelectorAll('button').find(b => b.dataset.view === 'watch').onclick();
  assert.match(element('#content').innerHTML, /When to recheck/);
  console.log('PASS: import/edit/validation/export exact JSON, malformed structure, patch search/selection, navigation, theme, and no mutation on rejected edits.');
}
main().catch(error => {console.error(error); process.exitCode = 1;});
