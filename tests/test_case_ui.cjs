// Pure JS regression checks with in-memory stubs, not a browser automation path.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname,'../src/benchmate/case_review/app.js'),'utf8').split('/* ---------- wiring ---------- */')[0];
function env() {
  const nodes = new Map(), saved = new Map(), timers=[];
  const node = id => { if(!nodes.has(id)) nodes.set(id,{replaceChildren(){},classList:{add(){},remove(){}},hidden:false,disabled:false}); return nodes.get(id); };
  const c = vm.createContext({document:{getElementById:node,querySelector(){return {content:'test-token'};}},
    matchMedia(){return {matches:true};}, localStorage:{getItem:k=>saved.get(k)||null,setItem:(k,v)=>saved.set(k,v),removeItem:k=>saved.delete(k)},
    setTimeout:fn=>(timers.push(fn),timers.length),clearTimeout(){},console,crypto:require('node:crypto').webcrypto,
    AbortController,URLSearchParams,structuredClone});
  vm.runInContext(source,c);
  vm.runInContext("current={manifest:{case_id:'case-a',revision:3}}; M.caseId='case-a'; renderMock=()=>{}; renderRunPicker=()=>{}; notice=()=>{};",c);
  return {c,nodes,saved,timers,run:s=>vm.runInContext(s,c)};
}
function defer(){let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});return {promise,resolve,reject};}
test('scope includes every 512-point sample, including the final output delay',()=>{
  const e=env();const value=e.run(`(()=>{const t=Array.from({length:512},(_,i)=>i*.0005+.000105),v=t.map(x=>Math.sin(x));const sc=scaleFor([{t,v}]);return {last:t.at(-1),window:sc.win,points:(pathOf({t,v},sc).match(/[ML]/g)||[]).length};})()`);
  assert.ok(value.window>=value.last);assert.equal(value.points,512);
});
test('regional failure is not described as an RMS allowance failure',()=>{
  const e=env();assert.match(e.run('verdictHTML({passed:false,RMS_mV:8.54})'),/regional check failed/);
});
test('run lookup cannot overwrite a newly selected case',async()=>{
  const e=env(), d=defer();e.c.fake=()=>d.promise;e.run('api=fake');
  const pending=e.run("selectRun('run-a')");
  e.run("current={manifest:{case_id:'case-b'}}; resetMockView();");
  d.resolve({run_id:'run-a',case_id:'case-a'});await pending;
  assert.equal(e.run('M.run'),null);assert.equal(e.saved.has('bm-run-case-b'),false);
});
test('a late poll cannot restore the previous case run',async()=>{
  const e=env(),d=defer();e.c.fake=()=>d.promise;e.run("api=fake; M.run={run_id:'run-a',status:'running'}; schedulePoll();");
  const pending=e.timers[0]();
  e.run("current={manifest:{case_id:'case-b'}}; resetMockView();");
  d.resolve({run_id:'run-a',case_id:'case-a',status:'awaiting_operator'});await pending;
  assert.equal(e.run('M.run'),null);assert.equal(e.run('M.polling'),false);
});
test('confirmation does not POST after navigation invalidates its card',async()=>{
  const e=env(),d=defer(),calls=[];
  e.c.fake=(url,body)=>{calls.push({url,body});return d.promise;};
  const btn={disabled:false};e.c.card={isConnected:true,querySelector:()=>btn};e.c.checks=[{checked:true}];
  e.run("api=fake; M.run={run_id:'run-a',status:'awaiting_operator'}; M.cardFor='request-a';");
  const pending=e.run('confirmRequest(card,checks)');
  e.run("current={manifest:{case_id:'case-b'}}; resetMockView();");
  d.resolve({pending_request:{request_id:'request-a'}});await pending;
  assert.equal(calls.length,1);assert.equal(calls[0].body,undefined);assert.equal(e.run('M.run'),null);
});
test('reloading a lost launch does not issue a new mutation',async()=>{
  const e=env(),calls=[];e.saved.set('bm-launch-case-a',JSON.stringify({launch_id:'missing'}));
  e.c.fake=async(url,body)=>{calls.push({url,body});return [];};e.run('api=fake');await e.run('initMock()');
  assert.equal(calls.length,1);assert.equal(calls[0].body,undefined);assert.ok(e.saved.has('bm-launch-case-a'));
});
test('failed confirmation fetch unlocks the same checked card for explicit retry',async()=>{
  const e=env(),btn={disabled:false};e.c.card={isConnected:true,querySelector:()=>btn};e.c.checks=[{checked:true}];
  e.c.fake=async()=>{throw Error('Offline');};
  e.run("api=fake; M.run={run_id:'run-a',status:'awaiting_operator'}; M.cardFor='request-a';");
  await e.run('confirmRequest(card,checks)');assert.equal(btn.disabled,false);assert.equal(e.run('M.sending'),false);
});
