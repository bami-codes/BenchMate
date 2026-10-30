// QA uses a separately launched, isolated Chrome, never a user browser profile.
// node scripts/check_viewer.mjs file:///absolute/report.html [output-directory]
import {writeFile,mkdir} from 'node:fs/promises';
const target=process.argv[2],output=process.argv[3]||'.impeccable/review';
if(!target?.startsWith('file:')&&!target?.startsWith('http://127.0.0.1:'))throw Error('Use an offline report or loopback viewer');
const tabs=await(await fetch('http://127.0.0.1:9337/json/list')).json();
const socket=new WebSocket(tabs.find(t=>t.type==='page').webSocketDebuggerUrl);
await new Promise(resolve=>socket.addEventListener('open',resolve,{once:true}));
let id=0;const pending=new Map(),errors=[],eventWaiters=new Map();
socket.addEventListener('message',event=>{const data=JSON.parse(event.data);if(eventWaiters.has(data.method)){eventWaiters.get(data.method)(data);eventWaiters.delete(data.method);}if(data.method==='Runtime.exceptionThrown')errors.push(data.params.exceptionDetails.text);if(data.id){const item=pending.get(data.id);pending.delete(data.id);data.error?item.reject(Error(data.error.message)):item.resolve(data.result);}});
function cdp(method,params={}){return new Promise((resolve,reject)=>{const key=++id;pending.set(key,{resolve,reject});socket.send(JSON.stringify({id:key,method,params}));});}
function waitEvent(method){return new Promise(resolve=>eventWaiters.set(method,resolve));}
async function evaluate(expression){const r=await cdp('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result.value;}
function assert(condition,message){if(!condition)throw Error(message);}
await cdp('Page.enable');await cdp('Runtime.enable');
await cdp('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'reduce'}]});
await mkdir(output,{recursive:true});const results=[];
for(const [width,height,name]of [[1440,900,'desktop'],[1280,900,'laptop'],[390,844,'mobile']]){
 await cdp('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:width<500});
 const loaded=waitEvent('Page.loadEventFired');await cdp('Page.navigate',{url:target});await loaded;
 for(let n=0;n<40;n++){if(await evaluate("document.readyState==='complete'&&!!window.BenchMateUI"))break;await new Promise(r=>setTimeout(r,100));}
 await evaluate('document.fonts.ready');
 assert(await evaluate('!!window.BenchMateUI'),'UI not ready');
 const layout=await evaluate(`({width:innerWidth,overflow:document.documentElement.scrollWidth>innerWidth,language:document.documentElement.lang,panels:[...document.querySelectorAll('.figure-panel,.report-panel,.timeline-panel,.mounting-panel')].map(e=>({name:e.className,top:e.getBoundingClientRect().top,bottom:e.getBoundingClientRect().bottom}))})`);
 assert(layout.width===width,'Wrong viewport width');assert(!layout.overflow,'Horizontal overflow');assert(layout.language==='en','Interface language');
 const bounds=await cdp('Page.getLayoutMetrics');
 const shot=await cdp('Page.captureScreenshot',{format:'png',captureBeyondViewport:true,clip:{x:0,y:0,width,height:Math.ceil(bounds.cssContentSize.height),scale:1}});
 await writeFile(output+'/'+name+'.png',Buffer.from(shot.data,'base64'));results.push({name,...layout});
 if(width>800)assert(layout.panels.every(p=>p.bottom<=900),'Five required panels do not fit desktop viewport: '+JSON.stringify(layout));
 else assert(layout.panels.find(p=>p.name.includes('timeline')).top<layout.panels.find(p=>p.name.includes('mounting')).top,'Mobile story order');
}
await cdp('Emulation.setDeviceMetricsOverride',{width:1440,height:900,deviceScaleFactor:1,mobile:false});
const count=await evaluate('BenchMateUI.getState().eventCount');
await evaluate('BenchMateUI.select(0)');assert(await evaluate("document.getElementById('source').textContent==='Source pending'"),'Undeclared source assumed');assert(await evaluate("!document.getElementById('status').textContent.includes('verified')"),'Future verdict leaked');
const prediction=await evaluate("JSON.parse(document.getElementById('record').textContent).events.findIndex(e=>e.kind==='prediction_committed')");
if(prediction>=0){
 await evaluate(`BenchMateUI.select(${prediction})`);
 assert(await evaluate("!document.querySelector('#chart path[data-series=observed]')&&document.querySelector('#chart path[data-series=predicted]')!==null"),'Prediction-before-observation missing');
 await evaluate('scrollTo(0,0)');await writeFile(output+'/prediction-only.png',Buffer.from((await cdp('Page.captureScreenshot',{format:'png'})).data,'base64'));
}
await evaluate(`BenchMateUI.select(${count-1})`);
assert(await evaluate("!!document.querySelector('#chart path[data-series=observed]')&&!!document.querySelector('#chart path[data-series=predicted]')"),'Overlay missing');
const discovery=await evaluate("initialRecord.events[0].payload.mode.includes('discovery')");
const stages=discovery?await evaluate("(()=>{const e=initialRecord.events,find=k=>e.findIndex(x=>x.kind===k);return {assessment:find('initial_family_assessment'),proposal:find('netlist_proposed'),fit:find('proposal_fit'),check:find('verification'),observation:e.findLastIndex(x=>x.kind==='verification_acquisition'),expanded:e[find('initial_family_assessment')].payload.training_comparison?.comparison_scope==='declared_linear_families_v2'}})()"):null;
if(discovery){
 assert(await evaluate("document.getElementById('condition').selectedOptions[0].textContent.includes('±1 V · unloaded')"),'Informative training condition not selected');
 assert(await evaluate("!!document.querySelector('#chart path[data-series=baseline]')&&document.querySelectorAll('#residual path').length===2"),'Three-model comparison or residuals missing');
 assert(await evaluate("document.querySelector('[data-cathode=REF]')&&document.getElementById('report-actor').textContent==='Spark · max'"),'Netlist or effort badge missing');
 assert(await evaluate("document.querySelectorAll('#story-stages button.reached').length===4"),'Milestones missing');
 const reportCheck=await evaluate(`(()=>{const events=JSON.parse(document.getElementById('record').textContent).events,r=events.find(e=>e.kind==='agent_report')?.payload,n=r?.next_measurement;return {checked:n?.checked_by==='engine',expected:n?.instruction,text:document.getElementById('next').textContent,status:document.getElementById('next-status').textContent}})()`);
 assert(reportCheck.checked?reportCheck.text===reportCheck.expected:reportCheck.status.includes('unvalidated'),'Unvalidated model text presented as executable instruction');
 const hasScaling=await evaluate("JSON.parse(document.getElementById('record').textContent).events.some(e=>e.payload.amplitude_scaling?.checks.length)");
 if(hasScaling){
  assert(await evaluate("!document.getElementById('linearity-wrap').hidden&&document.querySelectorAll('#linearity-chart path[data-series]').length===2&&Math.abs(Number(document.getElementById('linearity-chart').dataset.rmsMv)-JSON.parse(document.getElementById('record').textContent).events.find(e=>e.payload.amplitude_scaling?.checks.length).payload.amplitude_scaling.checks[0].channels.out_v.dc_removed_rms_mv)<1e-6"),'Training scaling curves do not match the recorded diagnostic');
  await evaluate('BenchMateUI.select(0)');
  assert(await evaluate("document.getElementById('linearity-wrap').hidden"),'Scaling evidence leaked before the assessment');
  await evaluate(`BenchMateUI.select(${count-1})`);
 }

 await evaluate(`document.getElementById('condition').value=${stages.observation};document.getElementById('condition').dispatchEvent(new Event('change'))`);
 assert(await evaluate("document.getElementById('plot-source').textContent==='Reserved verification'&&!!document.querySelector('#chart path[data-series=baseline]')&&['Frozen RC prediction','Frozen linear prediction'].includes(document.getElementById('baseline-label').textContent)"),'Frozen RC verification prediction missing or mislabeled');
 assert(await evaluate("document.querySelectorAll('#residual path').length===2&&/(RC|Linear) fails; proposal passes/.test(document.getElementById('comparison-note').textContent)"),'Verification comparison missing');
 await evaluate('scrollTo(0,0)');await writeFile(output+'/verification.png',Buffer.from((await cdp('Page.captureScreenshot',{format:'png'})).data,'base64'));
 for(const width of [1440,390]){
  await cdp('Emulation.setDeviceMetricsOverride',{width,height:900,deviceScaleFactor:1,mobile:width<500});
  for(const index of [8,stages.fit,stages.check,count-1]){
   await evaluate(`BenchMateUI.select(${index})`);
   const trail=await evaluate(`(()=>{const root=document.getElementById('timeline'),bounds=root.getBoundingClientRect(),rows=[...root.querySelectorAll('button')].map(e=>({top:e.getBoundingClientRect().top,bottom:e.getBoundingClientRect().bottom,current:e.hasAttribute('aria-current')})),shown=rows.filter(r=>r.bottom>bounds.top+5.5&&r.top<bounds.bottom-5.5);return {pending:root.textContent.includes('Pending'),currentVisible:shown.some(r=>r.current),partial:shown.some(r=>r.top<bounds.top-1||r.bottom>bounds.bottom+1),width:${width},index:${index}}})()`);
   assert(!trail.pending&&trail.currentVisible&&!trail.partial,'Timeline latest whole rows: '+JSON.stringify(trail));
  }
 }
 await cdp('Emulation.setDeviceMetricsOverride',{width:1440,height:900,deviceScaleFactor:1,mobile:false});
 await evaluate(`BenchMateUI.select(${prediction})`);
 assert(await evaluate("!!document.querySelector('#chart path[data-series=baseline]')&&!document.querySelector('#chart path[data-series=observed]')&&!document.getElementById('comparison-note').textContent.includes('fails; proposal')"),'Verification outcome leaked before observation');
 assert(await evaluate("document.getElementById('linearity-wrap').hidden"),'Training inset mixed into reserved verification');
 assert(await evaluate("document.getElementById('expand-report').disabled&&document.getElementById('expand-report').textContent==='Report not recorded yet'"),'Pending report state unclear');
 await evaluate(`BenchMateUI.select(${stages.assessment})`);
 assert(await evaluate("!!document.querySelector('#chart path[data-series=baseline]')&&!document.querySelector('#chart path[data-series=predicted]')&&document.getElementById('proposal-circuit').hasAttribute('hidden')"),'Initial comparison leaked later proposal');
 if(stages.expanded)assert(await evaluate("document.getElementById('baseline-label').textContent==='Best tested linear model'&&document.getElementById('comparison-note').textContent.includes('Training amplitude check')&&document.getElementById('linearity-evidence').textContent.includes('training_diagnostic')"),'Expanded baseline or scaling diagnostic missing');
 await evaluate('scrollTo(0,0)');await writeFile(output+'/initial-models.png',Buffer.from((await cdp('Page.captureScreenshot',{format:'png'})).data,'base64'));
 await evaluate(`BenchMateUI.select(${stages.proposal})`);assert(await evaluate("!document.getElementById('proposal-circuit').hasAttribute('hidden')&&!document.querySelector('#chart path[data-series=predicted]')"),'Proposal-before-fit semantics');
 await evaluate(`BenchMateUI.select(${stages.fit})`);
 assert(await evaluate("document.getElementById('status').textContent==='Training fit passed · verification pending'&&!!document.querySelector('#chart path[data-series=predicted]')"),'Training status or fit curve missing');
 await evaluate('scrollTo(0,0)');await writeFile(output+'/training-fit.png',Buffer.from((await cdp('Page.captureScreenshot',{format:'png'})).data,'base64'));
 assert(await evaluate("(()=>{const saved=state.events;state.events=[{sequence:0,kind:'provider_configuration',payload:{reasoning_effort:'medium'}}];const actor=sparkActor(1);state.events=saved;return actor.name==='Spark · standard'&&actor.title.includes('medium');})()"),'Standard badge is not grounded in recorded effort');
 assert(await evaluate("proposalDescription([{kind:'R',a:'OUT',b:'IN'},{kind:'D',a:'REF',b:'OUT'}]).side==='bottom'"),'Reversed diode interpreted as upper clamp');
 await evaluate('BenchMateUI.select(0)');assert(await evaluate("!document.getElementById('story-stages').textContent.includes('passed')&&!document.querySelector('#chart path[data-series=baseline]')"),'Future milestone or curve leaked');
 await evaluate(`BenchMateUI.select(${count-1})`);
}
await evaluate("document.querySelector('[data-trace=drive]').click()");assert(await evaluate("!!document.querySelector('#chart path[data-series=drive]')"),'Trace control failed');
await evaluate("document.querySelector('[data-trace=drive]').click();document.getElementById('expand-report').click()");
assert(await evaluate("document.getElementById('expand-report').getAttribute('aria-expanded')==='true'"),'Report expansion failed');
await evaluate("document.getElementById('expand-report').click();document.querySelector('.evidence-drawer > summary').click()");
assert(await evaluate("document.querySelector('.evidence-drawer').open"),'Evidence disclosure failed');
await evaluate("document.querySelector('.evidence-drawer > summary').click();document.getElementById('cursor').focus()");
await cdp('Input.dispatchKeyEvent',{type:'keyDown',key:'ArrowLeft',code:'ArrowLeft',windowsVirtualKeyCode:37});await cdp('Input.dispatchKeyEvent',{type:'keyUp',key:'ArrowLeft',code:'ArrowLeft',windowsVirtualKeyCode:37});
assert(await evaluate(`BenchMateUI.getState().cursor===${count-2}`),'Keyboard slider failed');
await evaluate("document.getElementById('play').click()");
assert(await evaluate("document.getElementById('play').textContent.includes('Pause')&&BenchMateUI.getState().cursor===0"),'Replay start failed');
await evaluate("document.getElementById('play').click()");assert(await evaluate("document.getElementById('play').textContent.includes('Replay')"),'Replay pause failed');
await evaluate(`BenchMateUI.select(${count-1})`);
// Review fixes: condition identity, origin, focus, and persistent error states.
assert(await evaluate("!sameSettings({kind:'step',ref_v:1.6},{kind:'step',ref_v:1.2})"),'REF mismatch matched');
assert(await evaluate("BenchMateUI.reduce([{kind:'run_started',payload:{mode:'unknown'}},{kind:'acquisition',payload:{source:'unrecognized'}}],1).origin==='unknown'"),'Unknown origin misclassified');
await evaluate("document.querySelector('#timeline li:last-child button').focus();document.activeElement.click()");
assert(await evaluate("document.activeElement.matches('#timeline button')"),'Timeline selection lost focus');
await cdp('Input.dispatchKeyEvent',{type:'keyDown',key:'Enter',code:'Enter',windowsVirtualKeyCode:13});await cdp('Input.dispatchKeyEvent',{type:'keyUp',key:'Enter',code:'Enter',windowsVirtualKeyCode:13});
assert(await evaluate("document.activeElement.matches('#timeline button')"),'Repeated keyboard activation lost focus');
await cdp('Input.dispatchKeyEvent',{type:'keyDown',key:'Tab',code:'Tab',windowsVirtualKeyCode:9});await cdp('Input.dispatchKeyEvent',{type:'keyUp',key:'Tab',code:'Tab',windowsVirtualKeyCode:9});
assert(await evaluate("document.activeElement.matches('summary')"),'Tab navigation from the last timeline event failed');
await evaluate(`BenchMateUI.select(${count-1})`);
assert(await evaluate("Number(getComputedStyle(document.querySelector('[data-trace=drive]')).opacity)===1"),'Inactive actionable text dimmed');
await evaluate("connectionError('QA: interrupted connection');render()");assert(await evaluate("!document.getElementById('connection-alert').hidden"),'Connection error lost on render');
await evaluate("BenchMateUI.ingest(JSON.parse(document.getElementById('record').textContent))");assert(await evaluate("document.getElementById('connection-alert').hidden"),'Valid update did not restore connection');
await evaluate("const bad=JSON.parse(document.getElementById('record').textContent);bad.events[0].sha256='bad';BenchMateUI.ingest(bad);BenchMateUI.select(0)");
assert(await evaluate("BenchMateUI.getState().integrityFailed&&!document.getElementById('connection-alert').hidden"),'Integrity failure not persistent');
assert(await evaluate("BenchMateUI.ingest(JSON.parse(document.getElementById('record').textContent))===false"),'Integrity failure resumed without reload');
assert(errors.length===0,'Browser JS errors: '+errors.join(', '));
await writeFile(output+'/browser-qa.json',JSON.stringify({target,results,interactions:'passed',errors},null,2)+'\n');
console.log(JSON.stringify({viewports:results,interactions:'passed',errors},null,2));socket.close();
