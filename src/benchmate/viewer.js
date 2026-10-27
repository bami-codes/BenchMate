/* A single event reducer and renderer for immutable replay and append-only live logs. */
'use strict';
const initialRecord = JSON.parse(document.getElementById('record').textContent);
const $ = id => document.getElementById(id);
const NS = 'http://www.w3.org/2000/svg';
const labels = {
  run_started:'Session started', acquisition:'Observation acquired', diagnosis:'Candidate assessment',
  initial_family_assessment:'Initial models assessed', instrument_request:'Measurement requested',
  netlist_proposed:'New structure proposed', proposal_fit:'Parameters fitted on training data',
  proposal_rejected:'Proposal rejected', prediction_committed:'Prediction committed',
  verification_acquisition:'Unseen observation acquired', verification:'Prediction checked',
  agent_report:'Explanation recorded', repair_requested:'Replacement requested',
  repair_prediction_committed:'Repair prediction committed', repair_applied:'Replacement applied',
  repair_verification_acquisition:'Post-repair observation acquired', repair_verification:'Repair checked',
  run_completed:'Session completed', run_failed:'Session failed', raw_capture:'Raw hardware captured'
};
const statusNames = {
  unresolved:'More evidence needed', verification_required:'Ready to test a prediction',
  verified_within_declared_candidates:'Prediction verified', all_candidates_inadequate:'Initial models do not fit',
  prediction_failed:'Prediction did not match', integration_unresolved:'Numerical evidence unresolved',
  repair_verified:'Repair prediction verified', repair_not_verified:'Repair prediction did not match'
};
const state = {record:initialRecord, events:initialRecord.events || [], cursor:(initialRecord.events?.length || 1)-1,
  timer:null, following:initialRecord.transport==='live_log', trace:{observed:true,predicted:true,drive:false},
  chartSeries:[], chartGeometry:null, lastFocus:null, lastCursor:null, milestones:[], connection:initialRecord.transport==='live_log'?'connecting':'offline', connectionMessage:'', integrityFailed:false};
const setText = (id,value) => { $(id).textContent = value == null ? '—' : String(value); };
const last = (list,kinds) => [...list].reverse().find(e => kinds.includes(e.kind));
const hasKorean = value => /[\uac00-\ud7a3]/.test(value || '');
const seconds = event => Math.max(0,(Date.parse(event.timestamp)-Date.parse(state.events[0]?.timestamp))/1000);
const elapsed = value => Number.isFinite(value) ? value.toFixed(1)+'s' : '—';
function node(parent,tag,attrs={},content){const el=document.createElementNS(NS,tag);for(const [k,v]of Object.entries(attrs))el.setAttribute(k,String(v));if(content!==undefined)el.textContent=String(content);parent.appendChild(el);return el;}
function sameSettings(a,b){return ['kind','shunt_ohm','load_ohm','amplitude_v','frequency_hz','duration_s','sample_period_s','step_at_s','ref_v'].every(k=>(a?.[k]??null)===(b?.[k]??null));}
function actorFor(event){
  if(event.kind==='tool_call'||event.kind==='netlist_proposed')return {name:'Spark',kind:'spark'};
  if(event.kind==='agent_report'){
    const provider=state.events.some(e=>e.sequence<=event.sequence&&e.kind==='provider_configuration');
    return {name:provider?'Spark':'Engine',kind:provider?'spark':'engine'};
  }
  if(event.kind==='repair_applied')return {name:event.payload.execution==='simulated'?'Simulator':'Operator',kind:'operator'};
  if(event.kind==='instrument_request'){const call=last(state.events.filter(e=>e.sequence<event.sequence),['tool_call']);const model=call?.payload.name==='measure';return {name:model?'Spark':'Engine',kind:model?'spark':'engine'};}
  if(event.kind.includes('acquisition')||event.kind==='raw_capture')return {name:event.payload.source==='synthetic'?'Simulator':['hardware','hardware_uncalibrated'].includes(event.payload.source)?'Instrument':'Unknown',kind:'engine'};
  return {name:'Engine',kind:'engine'};
}
function badge(el,actor){el.textContent=actor.name;el.className='actor-badge '+actor.kind;}
function reduce(events,cursor){
  const visible=events.slice(0,cursor+1),terminal=last(visible,['run_completed','run_failed']);
  const result=terminal?.payload || {},report=last(visible,['agent_report']),diagnosis=last(visible,['diagnosis','initial_family_assessment'])?.payload;
  const verification=last(visible,['verification','repair_verification']);
  const mode=events[0]?.payload.mode || '';
  const sources=new Set(visible.filter(e=>['acquisition','verification_acquisition','repair_verification_acquisition','raw_capture'].includes(e.kind)).map(e=>e.payload.source).filter(Boolean));
  const declared=sources.size===1?[...sources][0]:null;
  const origin=sources.size>1?'mixed':declared==='synthetic'?'synthetic':['hardware','hardware_uncalibrated'].includes(declared)?'hardware':'unknown';
  const isHardware=origin==='hardware';
  const mounting=last(visible,['instrument_request','acquisition','verification_acquisition','repair_verification_acquisition','prediction_committed','repair_prediction_committed']);
  let status=terminal?.kind==='run_failed'?'Session failed':result.status||result.final_report?.status||diagnosis?.status||'Waiting for an observation';
  if(terminal?.kind==='run_completed'&&!result.status&&!result.final_report?.status)status=report?.payload.verdict==='verified'?'verified_within_declared_candidates':report?.payload.verdict==='abstained'?'Conclusion withheld':'Session completed';
  if(verification&&!terminal)status=verification.payload.passed?'Prediction matched · report pending':'Prediction did not match';
  const focus=last(visible,['acquisition','verification_acquisition','repair_verification_acquisition','prediction_committed','repair_prediction_committed','raw_capture']);
  const used=visible.filter(e=>['acquisition','verification_acquisition','repair_verification_acquisition','raw_capture'].includes(e.kind)).reduce((n,e)=>n+(e.payload.physical_acquisitions||1),0);
  return {visible,terminal,result,report,diagnosis,verification,focus,status,used,isHardware,origin,mounting,
    provider:last(visible,['provider_configuration'])?.payload,mode};
}
function brief(vm){
  const report=vm.report?.payload;
  if(vm.verification?.kind==='repair_verification')return {
    explanation:vm.verification.payload.passed?'Both post-replacement observations matched the predictions committed before the replacement.':'The post-replacement observations did not match the committed predictions.',
    uncertainty:'This replacement was simulated. Physical repair and calibrated hardware accuracy remain unverified.',
    next:'Repeat the same before-and-after measurements on the calibrated physical circuit.',actor:{name:'Engine',kind:'engine'}};
  if(report&&!hasKorean(JSON.stringify(report)))return {explanation:report.current_explanation,uncertainty:report.unresolved,next:report.next_observation,actor:actorFor(vm.report)};
  const verification=vm.verification?.payload;
  const fitted=last(vm.visible,['proposal_fit']);
  const proposed=last(vm.visible,['netlist_proposed']);
  const requested=last(vm.visible,['instrument_request']);
  let explanation=vm.diagnosis?.status==='all_candidates_inadequate'?'The initial RC families do not explain these observations. A different structure is needed.':vm.diagnosis?.status==='unresolved'?'The available observations support more than one explanation. Another measurement is needed.':'Review the observation before selecting the next experiment.';
  if(proposed)explanation='A new circuit structure has been proposed. Its exact connections are being tested against the training observations.';
  if(fitted)explanation=fitted.payload.training_passed?'The proposed connections explain the training observations. They still need an independent prediction check.':'The proposal did not pass the training checks. It cannot be confirmed.';
  if(verification)explanation=verification.passed?'The new observations matched the predictions committed before acquisition, within the declared development checks.':'The new observations did not match the committed predictions. The explanation remains unconfirmed.';
  if(vm.terminal?.kind==='run_failed')explanation='This run stopped before completing the experiment. The partial evidence is preserved.';
  return {explanation,uncertainty:vm.isHardware?'These are uncalibrated raw counts. Voltage accuracy and hardware diagnosis have not been established.':vm.origin==='synthetic'?'Synthetic observations only. Physical accuracy, untested structures and generalization remain unknown.':'Data origin is not yet established. No physical or synthetic result is assumed.',
    next:requested?.payload.instruction&&!hasKorean(requested.payload.instruction)?requested.payload.instruction:verification?'Validate the fixture and repeat these conditions on hardware after D2 calibration.':fitted?.payload.training_passed?'Commit the prediction, then acquire a reserved condition.':proposed?'Test the generated structure without changing its connections.':'Inspect the observations and choose a measurement that separates the remaining explanations.',
    actor:{name:'Engine summary',kind:'engine'}};
}
function renderChart(series,unit,xLabel,animate){
  const root=$('chart');root.replaceChildren();const width=Math.max(240,root.clientWidth),height=root.clientHeight||270;
  root.setAttribute('viewBox',`0 0 ${width} ${height}`);
  node(root,'title',{id:'chart-title'},'Prediction and observation');node(root,'desc',{id:'chart-description'},'Dashed blue is the precommitted prediction. Orange is the observed output. Both use the same axes.');
  const valid=series.filter(s=>s.x?.length&&s.x.length===s.y?.length&&[...s.x,...s.y].every(Number.isFinite));
  state.chartSeries=valid;
  if(!valid.length){node(root,'text',{x:width/2,y:height/2,'text-anchor':'middle',fill:'#55635e','font-size':13},'No waveform at this point in the run.');state.chartGeometry=null;return;}
  const xs=valid.flatMap(s=>s.x),ys=valid.flatMap(s=>s.y);let xmin=Math.min(...xs),xmax=Math.max(...xs),ymin=Math.min(...ys),ymax=Math.max(...ys);
  if(xmax===xmin)xmax=xmin+1;const pad=Math.max(unit==='V'?.04:1,(ymax-ymin)*.15);ymin-=pad;ymax+=pad;
  const left=47,right=18,top=24,bottom=37,X=v=>left+(width-left-right)*(v-xmin)/(xmax-xmin),Y=v=>height-bottom-(height-top-bottom)*(v-ymin)/(ymax-ymin);
  state.chartGeometry={width,height,left,right,xmin,xmax,X,Y};
  for(let i=0;i<=4;i++){const v=ymin+(ymax-ymin)*i/4;node(root,'line',{x1:left,y1:Y(v),x2:width-right,y2:Y(v),stroke:'#e6ebe4','stroke-width':1});node(root,'text',{x:left-10,y:Y(v)+3,'text-anchor':'end',fill:'#55635e','font-size':10,'font-family':'Plex, sans-serif'},v.toFixed(unit==='V'?2:0));}
  for(let i=0;i<=4;i++){const v=xmin+(xmax-xmin)*i/4;node(root,'text',{x:X(v),y:height-18,'text-anchor':'middle',fill:'#55635e','font-size':10},v.toFixed(xmax<.5?3:1));}
  node(root,'text',{x:left,y:12,fill:'#55635e','font-size':10},unit);node(root,'text',{x:width-right,y:height-2,'text-anchor':'end',fill:'#55635e','font-size':10},xLabel);
  const colors={observed:'#bb4c27',predicted:'#315e91',drive:'#7a827e'};
  // Prediction drawn last: tiny differences remain visible instead of hiding it.
  for(const s of [...valid].sort((a,b)=>(a.key==='predicted')-(b.key==='predicted'))){
    if(!state.trace[s.key])continue;let d='';const step=Math.max(1,Math.floor(s.x.length/1500));
    for(let i=0;i<s.x.length;i+=step)d+=(d?'L':'M')+X(s.x[i]).toFixed(2)+','+Y(s.y[i]).toFixed(2);
    node(root,'path',{d,fill:'none',stroke:colors[s.key],'stroke-width':s.key==='observed'?2.5:1.8,'stroke-dasharray':s.key==='predicted'?'6 5':'none','data-series':s.key,class:animate&&s.key==='observed'?'trace-arrival':''});
  }
}
function wiring(settings,hardware){
  const root=$('wiring');root.replaceChildren();
  node(root,'title',{},'Drive to input through the jumper or shunt; output load returns to REF.');
  if(!settings){node(root,'text',{x:170,y:60,'text-anchor':'middle',fill:'#55635e','font-size':12},'Connection instructions appear with a measurement.');setText('instruction','No measurement requested yet.');return;}
  const line=(x1,y1,x2,y2)=>node(root,'line',{x1,y1,x2,y2,stroke:'#687d70','stroke-width':1.5});
  line(18,40,320,40);line(18,105,320,105);
  for(const [x,label]of [[18,'DRIVE'],[140,'IN'],[270,'OUT']]){node(root,'circle',{cx:x,cy:40,r:3,fill:'#1f6954'});node(root,'text',{x,y:19,'text-anchor':x===18?'start':'middle',fill:'#1c2b27','font-size':10},label);}
  node(root,'rect',{x:58,y:30,width:67,height:20,rx:2,fill:'#f3f6ef',stroke:'#91a494'});
  node(root,'text',{x:91,y:43,'text-anchor':'middle',fill:'#1c2b27','font-size':9},settings.shunt_ohm?'1 kΩ shunt':'0 Ω jumper');
  node(root,'rect',{x:165,y:26,width:67,height:29,rx:3,fill:'#183d35'});node(root,'text',{x:199,y:45,'text-anchor':'middle',fill:'#fff','font-size':10},'Circuit');line(199,55,199,105);
  node(root,'text',{x:18,y:123,fill:'#55635e','font-size':10},'REF');
  if(settings.load_ohm){line(290,40,290,105);node(root,'rect',{x:268,y:62,width:45,height:21,rx:2,fill:'#fff5e6',stroke:'#b9945b'});node(root,'text',{x:290,y:76,'text-anchor':'middle',fill:'#795018','font-size':10},settings.load_ohm/1000+' kΩ');}
  setText('instruction',(settings.shunt_ohm?'Replace the DRIVE–IN jumper with a 1 kΩ shunt.':'Keep the 0 Ω jumper between DRIVE and IN.')+' '+(settings.load_ohm?`Connect ${settings.load_ohm/1000} kΩ from OUT to REF.`:'Leave OUT–REF unloaded.'));
  setText('mount-note',hardware?'Logical connections only. Verify the physical fixture before driving it.':'Simulated mounting · logical nodes, not a breadboard layout.');
  badge($('mount-actor'),{name:hardware?'Operator':'Operator · simulated',kind:'operator'});
}
function renderTimeline(vm){
  const root=$('timeline'),focused=root.contains(document.activeElement)?document.activeElement.closest('button')?.dataset.index:null;root.replaceChildren();
  state.milestones=state.events.map((e,i)=>labels[e.kind]?i:-1).filter(i=>i>=0);
  for(const i of state.milestones){const e=state.events[i],future=i>state.cursor,li=document.createElement('li'),button=document.createElement('button');
    button.className='event'+(i===state.cursor?' active':'')+(future?' future':'');button.dataset.index=i;
    if(i===state.cursor)button.setAttribute('aria-current','step');
    const time=document.createElement('span');time.className='time';time.textContent=future?'—':elapsed(seconds(e));
    const actor=document.createElement('span');badge(actor,future?{name:'Pending',kind:''}:actorFor(e));
    const label=document.createElement('span');label.className='event-label';label.textContent=future?'Later action':labels[e.kind];
    button.append(time,actor,label);const arrow=document.createElementNS(NS,'svg');arrow.setAttribute('viewBox','0 0 20 20');arrow.setAttribute('aria-hidden','true');node(arrow,'path',{d:'M5 10h9m-4-4 4 4-4 4'});button.appendChild(arrow);
    button.onclick=()=>select(i,true);li.appendChild(button);root.appendChild(li);
  }
  if(state.lastCursor!==state.cursor){const active=root.querySelector('[aria-current=step]');if(active)root.scrollTop+=active.getBoundingClientRect().bottom-root.getBoundingClientRect().bottom+10;}
  state.lastCursor=state.cursor;
  if(focused!==null)root.querySelector(`[data-index="${focused}"]`)?.focus({preventScroll:true});
}
function render(){
  if(!state.events.length){setText('status','Waiting for the first event');return;}
  const vm=reduce(state.events,state.cursor),focus=vm.focus,p=focus?.payload,settings=p?.settings;
  const discovery=vm.mode.includes('discovery'),repair=vm.mode.includes('repair');
  setText('headline',vm.isHardware?'Instrument capture':discovery?'Structure discovery':repair?'Repair verification':'Circuit investigation');
  setText('session-description',discovery?'Test a new explanation against evidence it has not seen.':repair?'Predict the effect of a replacement, then check the result.':vm.isHardware?'Inspect raw acquisition before interpreting the circuit.':'Choose the measurement that separates the remaining explanations.');
  setText('source',({hardware:'Hardware · uncalibrated',synthetic:'Synthetic observations',unknown:'Source pending',mixed:'Mixed data sources'})[vm.origin]);
  const live=state.record.transport==='live_log';
  setText('transport',state.integrityFailed?'Live log · integrity error':live&&state.connection==='disconnected'?'Live log · disconnected':live?(state.following?'Live log':'Live log · reviewing'):'Replay');
  $('connection-alert').hidden=!state.connectionMessage;setText('connection-alert',state.connectionMessage);
  setText('scope',vm.isHardware?'Raw counts; calibration and voltage accuracy are pending.':vm.origin==='synthetic'?'Development data · no physical circuit result.':vm.origin==='mixed'?'Inspect each observation for its declared origin.':'Waiting for an observation with a declared origin.');
  setText('status',statusNames[vm.status]||vm.status);
  $('status-dot').style.background=vm.terminal?.kind==='run_failed'||vm.verification?.payload.passed===false?'var(--error)':vm.verification?.payload.passed?'var(--success)':'var(--warning)';
  setText('actor',vm.provider?vm.provider.model+' · '+vm.provider.reasoning_effort:'Numerical engine');setText('count',vm.used+' acquisition'+(vm.used===1?'':'s'));setText('duration',elapsed(seconds(state.events[state.cursor]))+' elapsed');
  const report=brief(vm);setText('explanation',report.explanation);setText('uncertainty',report.uncertainty);setText('next',report.next);badge($('report-actor'),report.actor);
  let series=[],unit='V',predictionEvent=null;
  if(focus?.kind==='raw_capture'){
    unit='ADC counts';if(p.rows)series=[{key:'observed',x:p.rows.map(r=>(r[0]+r[7])/1e6),y:p.rows.map(r=>r[3])}];
    else if(p.samples)series=[{key:'observed',x:p.samples.map(r=>r.t_us[1]/1e6),y:p.samples.map(r=>r.raw[1])}];
  }else if(focus?.kind.includes('prediction_committed')){
    const d=p.prediction?.mean||p.prediction;series=[{key:'predicted',x:d?.time_s||d?.drive_v,y:d?.out_v}];predictionEvent=focus;
  }else if(p?.data){
    const d=p.data,x=d.time_s||d.drive_v;series=[{key:'observed',x,y:d.out_v},{key:'drive',x,y:d.drive_v}];
    const kind=focus.kind==='repair_verification_acquisition'?'repair_prediction_committed':'prediction_committed';
    predictionEvent=[...vm.visible].reverse().find(e=>e.sequence<focus.sequence&&e.kind===kind&&sameSettings(e.payload.settings,settings));
    if(predictionEvent){const predicted=predictionEvent.payload.prediction.mean||predictionEvent.payload.prediction;series.push({key:'predicted',x:predicted.time_s||x,y:predicted.out_v});}
  }
  renderChart(series,unit,settings?.kind==='dc_pair'?'Drive level (V)':'Time (s)',focus?.sequence!==state.lastFocus&&Boolean(predictionEvent));state.lastFocus=focus?.sequence;
  setText('plot-note',settings?(settings.kind==='sine'?settings.frequency_hz.toPrecision(3)+' Hz sine':settings.kind==='dc_pair'?'DC pair':'Step')+' · ±'+settings.amplitude_v+' V'+(settings.load_ohm?' · '+settings.load_ohm/1000+' kΩ':' · unloaded'):'Waiting for a capture');
  setText('plot-source',focus?.kind.includes('prediction_committed')?'Prediction only':predictionEvent?'Reserved verification condition':'Training observation');
  const check=vm.verification?.payload;
  const proof=$('verification');proof.replaceChildren();proof.classList.toggle('failed',check?.passed===false);
  if(check){const icon=document.createElementNS(NS,'svg');icon.setAttribute('viewBox','0 0 20 20');icon.setAttribute('aria-hidden','true');node(icon,'path',{d:check.passed?'m4 10 4 4 8-9':'m5 5 10 10M15 5 5 15'});proof.append(icon);}
  const note=check?(check.passed?'Verification passed':'Verification failed')+' · no refit on verification data':predictionEvent?(focus.kind.includes('prediction_committed')?'Prediction locked. The verification observation has not arrived.':'Prediction was committed before this observation.'):'Training data informs the hypothesis; it does not confirm it.';
  proof.append(document.createTextNode(note));
  const mountSettings=vm.mounting?.payload.settings;
  wiring(mountSettings,vm.isHardware);
  setText('mount-title',vm.mounting?.kind==='instrument_request'?'Requested connections':'Connections for this step');
  if(vm.mounting?.kind==='instrument_request'&&!mountSettings){setText('instruction','This earlier request has no structured connection settings. Inspect the original request below.');setText('mount-note','Previous connections are not presented as the new request.');}
  renderTimeline(vm);
  const evidence=last(vm.visible,['proposal_fit','netlist_proposed','repair_requested','repair_applied','instrument_request']);
  setText('evidence-note',evidence?labels[evidence.kind]:'No proposal or requested action at this point.');
  setText('evidence',evidence?.payload.rendered_fitted_proposal?[evidence.payload.rendered_fitted_proposal,evidence.payload.rendered_fitted_diode||'',JSON.stringify({training_passed:evidence.payload.training_passed,topology_preserved:evidence.payload.generated_topology_sha256===evidence.payload.fitted_topology_sha256},null,2)].join('\n'):evidence?JSON.stringify(evidence.payload,null,2):'—');
  setText('raw',JSON.stringify(state.events[state.cursor],null,2));
  $('cursor').max=state.events.length-1;$('cursor').value=state.cursor;setText('position',(state.cursor+1)+' / '+state.events.length);
  $('previous').disabled=state.cursor<=0;$('next-event').disabled=state.cursor>=state.events.length-1;$('play').disabled=state.events.length<2;
  $('follow').hidden=!live;$('follow').disabled=state.following;
  setText('integrity',(state.record.integrity==='verified_prefix'?'Hash chain checked through the latest received event.':'Source hash chain verified at export.')+' No external attestation. Record '+state.record.run_id+' · SHA-256 '+(state.record.source_sha256||'pending'));
}
function stop(){if(state.timer)clearInterval(state.timer);state.timer=null;$('play').querySelector('span').textContent='Replay run';$('play').setAttribute('aria-label','Replay recorded events');}
function select(index,announce=false){stop();state.following=false;state.cursor=Math.max(0,Math.min(index,state.events.length-1));render();if(announce)setText('announcement',(labels[state.events[state.cursor].kind]||'Event')+'. '+$('status').textContent);}
function milestone(direction){const available=state.milestones.filter(i=>direction<0?i<state.cursor:i>state.cursor);select(direction<0?available.at(-1)??0:available[0]??state.events.length-1,true);}
$('previous').onclick=()=>milestone(-1);$('next-event').onclick=()=>milestone(1);$('cursor').oninput=e=>select(Number(e.target.value));
$('expand-report').onclick=()=>{const open=$('expand-report').getAttribute('aria-expanded')!=='true';$('expand-report').setAttribute('aria-expanded',String(open));document.querySelector('.report-panel').classList.toggle('expanded',open);setText('expand-report',open?'Collapse report':'Read full report');};
$('play').onclick=()=>{if(state.timer){stop();return;}state.following=false;state.cursor=0;render();$('play').querySelector('span').textContent='Pause';$('play').setAttribute('aria-label','Pause replay');state.timer=setInterval(()=>{if(state.cursor>=state.events.length-1){stop();return;}state.cursor++;render();const current=$('timeline').querySelector('[aria-current=step]');if(current)current.scrollIntoView({block:'nearest',behavior:'instant'});},950);};
$('follow').onclick=()=>{stop();state.following=true;state.cursor=state.events.length-1;render();};
for(const button of document.querySelectorAll('[data-trace]'))button.onclick=()=>{const key=button.dataset.trace;state.trace[key]=!state.trace[key];button.setAttribute('aria-pressed',state.trace[key]);render();};
$('chart').onpointermove=e=>{const g=state.chartGeometry;if(!g)return;const rect=$('chart').getBoundingClientRect(),px=e.clientX-rect.left;if(px<g.left||px>g.width-g.right){$('plot-readout').hidden=true;return;}const x=g.xmin+(px-g.left)/(g.width-g.left-g.right)*(g.xmax-g.xmin),readings=[];for(const s of state.chartSeries.filter(s=>state.trace[s.key])){let closest=0;for(let i=1;i<s.x.length;i++)if(Math.abs(s.x[i]-x)<Math.abs(s.x[closest]-x))closest=i;readings.push(s.key+': '+s.y[closest].toFixed(3));}setText('plot-readout','x '+x.toFixed(3)+' · '+readings.join(' / '));$('plot-readout').hidden=!readings.length;};
$('chart').onpointerleave=()=>{$('plot-readout').hidden=true;};
$('download').onclick=()=>{const blob=new Blob([state.events.map(e=>JSON.stringify(e)).join('\n')+'\n'],{type:'application/x-ndjson'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=state.record.run_id+'-events.jsonl';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
// Transport adapters only feed events; all modes use reduce() and render().
function ingest(record){
  if(state.integrityFailed)return false;
  if(!Array.isArray(record.events)||!record.events.length)return false;
  const old=state.events;
  for(let i=0;i<old.length;i++)if(!record.events[i]||record.events[i].sha256!==old[i].sha256){connectionError('The run changed unexpectedly. Live updates stopped; inspect the source JSONL.',true);return false;}
  state.record={...state.record,...record};state.events=record.events;state.connection='connected';state.connectionMessage='';
  if(state.following)state.cursor=state.events.length-1;render();return true;
}
function connectionError(message,integrity=false){
  state.integrityFailed ||= integrity;state.connection='disconnected';state.connectionMessage=message;render();
}
window.BenchMateUI={ingest,select,reduce,getState:()=>({cursor:state.cursor,eventCount:state.events.length,following:state.following,transport:state.record.transport||'replay',connection:state.connection,integrityFailed:state.integrityFailed})};
if(state.record.transport==='live_log'){
  const stream=new EventSource('/events');
  stream.onmessage=e=>{try{if(!ingest(JSON.parse(e.data))&&state.integrityFailed)stream.close();}catch{connectionError('The incoming record could not be read. Waiting to reconnect.');}};
  stream.onerror=()=>{if(!state.integrityFailed)connectionError('Log connection interrupted. Displaying the last verified events; reconnecting automatically.');};
  stream.addEventListener('integrity_error',()=>{stream.close();connectionError('Record integrity failed. Live updates stopped; inspect the source JSONL.',true);});
}
window.addEventListener('resize',()=>render());render();
