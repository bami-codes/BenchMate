// Isolated local Chrome only. No API or board access.
import {writeFile,mkdir} from 'node:fs/promises';
const target=process.argv[2],output=process.argv[3];
if(!target?.startsWith('file:')||!output)throw Error('Offline target and output directory required');
const tabs=await(await fetch('http://127.0.0.1:9338/json/list')).json();
const socket=new WebSocket(tabs.find(t=>t.type==='page').webSocketDebuggerUrl);
await new Promise(resolve=>socket.addEventListener('open',resolve,{once:true}));
let id=0,assertions=0;const pending=new Map(),waiters=new Map(),errors=[];
socket.addEventListener('message',e=>{const d=JSON.parse(e.data);if(waiters.has(d.method)){waiters.get(d.method)(d);waiters.delete(d.method);}if(d.method==='Runtime.exceptionThrown')errors.push(d.params.exceptionDetails.text);if(d.id){const p=pending.get(d.id);pending.delete(d.id);d.error?p.reject(Error(d.error.message)):p.resolve(d.result);}});
function cdp(method,params={}){return new Promise((resolve,reject)=>{const key=++id;pending.set(key,{resolve,reject});socket.send(JSON.stringify({id:key,method,params}));});}
function event(method){return new Promise(resolve=>waiters.set(method,resolve));}
async function evaluate(expression){const r=await cdp('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result.value;}
function assert(value,message){assertions++;if(!value)throw Error(message);}
await mkdir(output,{recursive:true});await cdp('Page.enable');await cdp('Runtime.enable');
await cdp('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'reduce'}]});
const layouts=[];
for(const [width,height,name]of [[1440,900,'desktop'],[1280,900,'laptop'],[390,844,'mobile']]){
  await cdp('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:width<500});
  const loaded=event('Page.loadEventFired');await cdp('Page.navigate',{url:target});await loaded;
  await evaluate('document.fonts.ready');
  assert(await evaluate('!!window.BenchMateUI'),'UI did not initialize');
  const layout=await evaluate(`({width:innerWidth,overflow:document.documentElement.scrollWidth>innerWidth,headline:document.getElementById('headline').textContent,panels:[...document.querySelectorAll('.figure-panel,.report-panel,.timeline-panel,.mounting-panel')].map(e=>({name:e.className,top:e.getBoundingClientRect().top,bottom:e.getBoundingClientRect().bottom}))})`);
  assert(!layout.overflow,'Horizontal overflow');assert(layout.headline==='Spark at the workbench','Wrong renderer');
  if(width>800)assert(layout.panels.every(p=>p.bottom<=900),'Main panels exceed desktop viewport: '+JSON.stringify(layout));
  const metrics=await cdp('Page.getLayoutMetrics');const shot=await cdp('Page.captureScreenshot',{format:'png',captureBeyondViewport:true,clip:{x:0,y:0,width,height:Math.ceil(metrics.cssContentSize.height),scale:1}});
  await writeFile(output+'/'+name+'.png',Buffer.from(shot.data,'base64'));layouts.push({name,...layout});
}
await cdp('Emulation.setDeviceMetricsOverride',{width:1440,height:900,deviceScaleFactor:1,mobile:false});
const indices=await evaluate(`(()=>{const e=initialRecord.events;return {count:e.length,training:e.findIndex(x=>x.kind==='unloaded_training_completed'),plan:e.findIndex(x=>x.kind==='physical_acquisition_plan_frozen'&&x.payload.phase==='reserved_sine'),observation:e.findIndex(x=>x.kind==='physical_observation'&&x.payload.phase==='reserved_sine'),check:e.findIndex(x=>x.kind==='physical_verification'),loaded:e.findIndex(x=>x.kind==='physical_measurement_selected'&&x.payload.phase==='attach_output_load_step')};})()`);
await evaluate('BenchMateUI.select(0)');
assert(await evaluate("document.getElementById('source').textContent==='Source pending'&&!document.querySelector('#chart path[data-series]')&&!document.getElementById('status').textContent.includes('Verified')"),'Future result leaked at start');
await evaluate(`BenchMateUI.select(${indices.training})`);
assert(await evaluate("!!document.querySelector('#chart path[data-series=observed]')&&!document.querySelector('#chart path[data-series=predicted]')&&document.getElementById('explanation').textContent.includes('indistinguishable')"),'Training stage or fit provenance wrong');
await evaluate(`BenchMateUI.select(${indices.plan})`);
assert(await evaluate("!document.querySelector('#chart path[data-series]')&&document.getElementById('comparison-note').textContent.includes('new measured IN')"),'Conditional future curves leaked');
assert(await evaluate(`actorFor(state.events[${indices.plan}]).name==='Engine'`),'Frozen model parameters attributed to the wrong actor');
await evaluate(`BenchMateUI.select(${indices.observation})`);
assert(await evaluate("!!document.querySelector('#chart path[data-series=observed]')&&!document.querySelector('#chart path[data-series=predicted]')"),'Comparison appears before its event');
await evaluate(`BenchMateUI.select(${indices.count-1})`);
assert(await evaluate("document.getElementById('source').textContent.includes('Physical observations')&&document.getElementById('transport').textContent==='Replay'"),'Physical origin/replay confused');
assert(await evaluate("!!document.querySelector('#chart path[data-series=observed]')&&!!document.querySelector('#chart path[data-series=baseline]')&&!!document.querySelector('#chart path[data-series=predicted]')"),'Physical overlays missing');
assert(await evaluate("document.querySelector('[data-model=nominal_rc]').dataset.passed==='false'&&document.querySelector('[data-model=nominal_rc]').textContent.includes('8.54 / 11.65')&&document.querySelector('[data-model=c_changed]').dataset.passed==='true'"),'Regional fail or passing candidate wrong');
assert(await evaluate("document.getElementById('comparison-note').textContent.includes('HOLD origins')&&document.getElementById('comparison-note').textContent.includes('worst-region')"),'Incremental voltage or score basis not visible');
await evaluate(`document.getElementById('condition').value=${indices.loaded};document.getElementById('condition').dispatchEvent(new Event('change'))`);
assert(await evaluate("document.querySelector('[data-model=c_changed]').textContent.includes('3.00 / 4.12')"),'Condition selection did not switch exact scores');
await evaluate("document.querySelector('[data-trace=drive]').click()");
assert(await evaluate("!!document.querySelector('#chart path[data-series=drive]')&&document.getElementById('drive-label').textContent==='Measured IN'"),'Measured input toggle failed');
await evaluate(`BenchMateUI.select(${indices.count-1});document.getElementById('expand-report').click()`);
assert(await evaluate("document.querySelector('details').open&&document.getElementById('original-report').textContent.includes('current_explanation')"),'Original report inaccessible');
await evaluate("document.getElementById('expand-report').click();document.getElementById('cursor').focus()");
await cdp('Input.dispatchKeyEvent',{type:'keyDown',key:'ArrowLeft',code:'ArrowLeft',windowsVirtualKeyCode:37});await cdp('Input.dispatchKeyEvent',{type:'keyUp',key:'ArrowLeft',code:'ArrowLeft',windowsVirtualKeyCode:37});
assert(await evaluate(`BenchMateUI.getState().cursor===${indices.count-2}`),'Keyboard timeline failed');
await evaluate("document.getElementById('play').click()");
assert(await evaluate("BenchMateUI.getState().cursor===0&&document.getElementById('play').textContent.includes('Pause')"),'Replay start failed');
await new Promise(resolve=>setTimeout(resolve,1100));
assert(await evaluate('BenchMateUI.getState().cursor===state.milestones.find(i=>i>0)'),'Physical replay does not advance by key actions');
await evaluate("document.getElementById('play').click()");
await evaluate(`BenchMateUI.select(${indices.count-1})`);
await evaluate("connectionError('QA interrupted log');render()");
assert(await evaluate("!document.getElementById('connection-alert').hidden"),'Connection failure hidden by physical renderer');
await evaluate('BenchMateUI.ingest(JSON.parse(document.getElementById("record").textContent))');
assert(await evaluate("document.getElementById('connection-alert').hidden"),'Valid record update did not restore state');
assert(errors.length===0,'Browser exceptions: '+errors.join(', '));
await writeFile(output+'/browser-qa.json',JSON.stringify({target,layouts,assertions,passed:true,errors},null,2)+'\n');
console.log(JSON.stringify({layouts,assertions,passed:true,errors}));socket.close();
