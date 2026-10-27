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
  timer:null, following:initialRecord.transport==='live_log', condition:null, trace:{observed:true,baseline:true,predicted:true,drive:false},
  chartSeries:[], chartGeometry:null, lastFocus:null, lastCursor:null, milestones:[], connection:initialRecord.transport==='live_log'?'connecting':'offline', connectionMessage:'', integrityFailed:false};
const setText = (id,value) => { $(id).textContent = value == null ? '—' : String(value); };
const last = (list,kinds) => [...list].reverse().find(e => kinds.includes(e.kind));
const hasKorean = value => /[\uac00-\ud7a3]/.test(value || '');
const seconds = event => Math.max(0,(Date.parse(event.timestamp)-Date.parse(state.events[0]?.timestamp))/1000);
const elapsed = value => Number.isFinite(value) ? value.toFixed(1)+'s' : '—';
function node(parent,tag,attrs={},content){const el=document.createElementNS(NS,tag);for(const [k,v]of Object.entries(attrs))el.setAttribute(k,String(v));if(content!==undefined)el.textContent=String(content);parent.appendChild(el);return el;}
function sameSettings(a,b){return ['kind','shunt_ohm','load_ohm','amplitude_v','frequency_hz','duration_s','sample_period_s','step_at_s','ref_v'].every(k=>(a?.[k]??null)===(b?.[k]??null));}
function sparkActor(sequence){
  const config=last(state.events.filter(e=>e.sequence<=sequence),['provider_configuration'])?.payload;
  const effort=config?.reasoning_effort,label=effort==='medium'?'standard':effort==='provider_default'?'default':effort||'unspecified';
  return {name:'Spark · '+label,kind:'spark',title:'Recorded API reasoning effort: '+(effort||'not recorded')};
}
function actorFor(event){
  if(event.kind==='tool_call'||event.kind==='netlist_proposed')return sparkActor(event.sequence);
  if(event.kind==='agent_report'){
    const provider=state.events.some(e=>e.sequence<=event.sequence&&e.kind==='provider_configuration');
    return provider?sparkActor(event.sequence):{name:'Engine',kind:'engine'};
  }
  if(event.kind==='repair_applied')return {name:event.payload.execution==='simulated'?'Simulator':'Operator',kind:'operator'};
  if(event.kind==='instrument_request'){const call=last(state.events.filter(e=>e.sequence<event.sequence),['tool_call']);const model=call?.payload.name==='measure';return model?sparkActor(event.sequence):{name:'Engine',kind:'engine'};}
  if(event.kind.includes('acquisition')||event.kind==='raw_capture')return {name:event.payload.source==='synthetic'?'Simulator':['hardware','hardware_uncalibrated'].includes(event.payload.source)?'Instrument':'Unknown',kind:'engine'};
  return {name:'Engine',kind:'engine'};
}
function badge(el,actor){el.textContent=actor.name;el.className='actor-badge '+actor.kind;el.title=actor.title||'';}
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
  if(!terminal&&mode.includes('discovery')){
    const stage=last(visible,['initial_family_assessment','netlist_proposed','proposal_fit','proposal_rejected','prediction_committed','verification_acquisition','verification']);
    if(stage)status=({initial_family_assessment:stage.payload.status,netlist_proposed:'Testing a proposed structure',proposal_fit:stage.payload.training_passed?'Training fit passed · verification pending':'Training fit failed',proposal_rejected:'Proposal rejected',prediction_committed:'Predictions locked · awaiting observations',verification_acquisition:'Checking reserved observations',verification:stage.payload.passed?'Prediction verified · report pending':'Prediction did not match'})[stage.kind];
  }
  const focus=last(visible,['acquisition','verification_acquisition','repair_verification_acquisition','prediction_committed','repair_prediction_committed','raw_capture']);
  const used=visible.filter(e=>['acquisition','verification_acquisition','repair_verification_acquisition','raw_capture'].includes(e.kind)).reduce((n,e)=>n+(e.payload.physical_acquisitions||1),0);
  return {visible,terminal,result,report,diagnosis,verification,focus,status,used,isHardware,origin,mounting,
    provider:last(visible,['provider_configuration'])?.payload,mode};
}
function comparisonFor(event,key){
  if(!event)return null;
  if(event.payload[key])return {data:['training_predictions','comparison_conditions'].includes(key)?{conditions:event.payload[key]}:event.payload[key],reconstructed:false,event};
  const entry=state.record.comparison?.entries?.find(e=>e.event_sequence===event.sequence&&e.event_sha256===event.sha256);
  return entry?{data:entry.comparison,reconstructed:true,event}:null;
}
function comparisons(vm){
  const proposed=last(vm.visible,['netlist_proposed']),fitted=last(vm.visible,['proposal_fit']);
  return {rc:comparisonFor(last(vm.visible,['initial_family_assessment']),'training_comparison'),
    spark:(!proposed||fitted?.sequence>proposed.sequence)?comparisonFor(fitted,'training_predictions'):null};
}
function expandedLinear(vm){return comparisonFor(last(vm.visible,['initial_family_assessment']),'training_comparison')?.data.comparison_scope==='declared_linear_families_v2';}
function conditionName(settings){
  if(!settings)return 'Raw capture';
  return (settings.kind==='sine'?settings.frequency_hz+' Hz sine':settings.kind==='dc_pair'?'DC pair':'Step')+' · ±'+settings.amplitude_v+' V · '+(settings.load_ohm?settings.load_ohm/1000+' kΩ':'unloaded');
}
function bestTraining(vm,models){
  const captures=vm.visible.filter(e=>e.kind==='acquisition'&&e.payload.data?.out_v);
  const scored=captures.map(event=>{
    const rc=models.rc?.data.conditions.find(c=>sameSettings(c.settings,event.payload.settings));
    const spark=models.spark?.data.conditions.find(c=>sameSettings(c.settings,event.payload.settings));
    const target=spark?.out_v||event.payload.data.out_v;
    const score=rc&&rc.out_v.length===target.length?Math.sqrt(rc.out_v.reduce((v,y,i)=>v+(y-target[i])**2,0)/target.length):-1;
    return {event,score};
  }).sort((a,b)=>b.score-a.score);
  return scored[0]?.score>=0?scored[0].event:null;
}
function plotFor(vm){
  const models=comparisons(vm),all=vm.visible.filter(e=>['acquisition','verification_acquisition','repair_verification_acquisition','raw_capture','prediction_committed','repair_prediction_committed'].includes(e.kind));
  const options=all.filter(e=>!e.kind.includes('prediction_committed')||!all.some(o=>o.sequence>e.sequence&&o.kind.includes('acquisition')&&sameSettings(o.payload.settings,e.payload.settings)));
  let focus=options.find(e=>e.sequence===state.condition)||vm.focus;
  if(state.condition===null&&vm.mode.includes('discovery')&&models.rc&&(vm.terminal||!last(vm.visible,['prediction_committed'])))focus=bestTraining(vm,models)||focus;
  const p=focus?.payload,settings=p?.settings;let series=[],predictionEvent=null,unit='V';
  if(focus?.kind==='raw_capture'){
    unit='ADC counts';if(p.rows)series=[{key:'observed',x:p.rows.map(r=>(r[0]+r[7])/1e6),y:p.rows.map(r=>r[3])}];
    else if(p.samples)series=[{key:'observed',x:p.samples.map(r=>r.t_us[1]/1e6),y:p.samples.map(r=>r.raw[1])}];
  }else if(focus?.kind.includes('prediction_committed')){
    const d=p.prediction?.mean||p.prediction;series=[{key:'predicted',x:d?.time_s||d?.drive_v,y:d?.out_v}];predictionEvent=focus;
  }else if(p?.data){
    const d=p.data,x=d.time_s||d.drive_v;series=[{key:'observed',x,y:d.out_v},{key:'drive',x,y:d.drive_v}];
    const kind=focus.kind==='repair_verification_acquisition'?'repair_prediction_committed':'prediction_committed';
    predictionEvent=[...vm.visible].reverse().find(e=>e.sequence<focus.sequence&&e.kind===kind&&sameSettings(e.payload.settings,settings));
    if(predictionEvent){const pred=predictionEvent.payload.prediction.mean||predictionEvent.payload.prediction;series.push({key:'predicted',x:pred.time_s||x,y:pred.out_v});}
    if(focus.kind==='acquisition')for(const [key,model]of [['baseline',models.rc],['predicted',models.spark]]){
      const c=model?.data.conditions.find(c=>sameSettings(c.settings,settings));
      if(c)series.push({key,x:c.time_s,y:c.out_v});
    }
  }
  const baseline=predictionEvent?comparisonFor(predictionEvent,'baseline_comparison'):null;
  if(baseline){const d=baseline.data.prediction;series.push({key:'baseline',x:d.time_s,y:d.out_v});}
  const verification=vm.verification?.kind==='verification'?comparisonFor(vm.verification,'comparison_conditions'):null;
  const metric=predictionEvent?verification?.data.conditions.find(c=>sameSettings(c.settings,settings)):null;
  const training=focus?.kind==='acquisition',reconstructed=training&&[models.rc,models.spark].some(m=>m?.reconstructed);
  return {focus,settings,series,predictionEvent,unit,training,reconstructed,models,options,baseline,verification,metric,expanded:expandedLinear(vm)};
}
function proposalDescription(elements){
  if(!Array.isArray(elements)||elements.length!==2)return null;
  const r=elements.find(e=>e.kind==='R'&&[e.a,e.b].sort().join()===['IN','OUT'].sort().join());
  const diode=elements.find(e=>e.kind==='D'&&[e.a,e.b].sort().join()===['OUT','REF'].sort().join());
  return r&&diode?{diode,side:diode.a==='OUT'?'top':'bottom'}:null;
}
function readingAid(vm,report){
  const proposed=last(vm.visible,['netlist_proposed']),fit=last(vm.visible,['proposal_fit']);
  const structure=proposalDescription(proposed?.payload.elements);
  if(!structure)return {...report,adapted:false};
  const passed=fit?.sequence>proposed.sequence&&fit.payload.training_passed;
  const explanation=passed?`A diode between OUT and REF explains the flattened ${structure.side} of the wave.`:`The proposal adds a diode between OUT and REF to clip the ${structure.side} of the wave.`;
  return {...report,explanation,uncertainty:vm.origin==='synthetic'?'Synthetic data only. Real components and other operating conditions remain unverified.':report.uncertainty,actor:actorFor(proposed),adapted:true};
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
  let explanation=vm.diagnosis?.status==='all_candidates_inadequate'?`The tested ${expandedLinear(vm)?'linear':'RC'} families do not explain these observations. A different structure is needed.`:vm.diagnosis?.status==='unresolved'?'The available observations support more than one explanation. Another measurement is needed.':'Review the observation before selecting the next experiment.';
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
  node(root,'title',{id:'chart-title'},'Prediction and observation');node(root,'desc',{id:'chart-description'},'Orange is observed output. Gray dashed is the selected linear model, frozen on training data. Blue dashed is the simulated Spark structure or a precommitted prediction, as labelled. All use the same axes.');
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
  const colors={observed:'#bb4c27',baseline:'#7a827e',predicted:'#315e91',drive:'#7a827e'};
  // Prediction drawn last: tiny differences remain visible instead of hiding it.
  for(const s of [...valid].sort((a,b)=>(a.key==='predicted')-(b.key==='predicted'))){
    if(!state.trace[s.key])continue;let d='';const step=Math.max(1,Math.floor(s.x.length/1500));
    for(let i=0;i<s.x.length;i+=step)d+=(d?'L':'M')+X(s.x[i]).toFixed(2)+','+Y(s.y[i]).toFixed(2);
    node(root,'path',{d,fill:'none',stroke:colors[s.key],'stroke-width':s.key==='observed'?2.5:1.8,'stroke-dasharray':['predicted','baseline'].includes(s.key)?(s.key==='baseline'?'3 4':'7 5'):'none','data-series':s.key,class:animate&&s.key==='observed'?'trace-arrival':''});
  }
}
function renderNext(vm, fallback){
  const recommendation=vm.report?.payload.next_measurement;
  const checked=recommendation?.checked_by==='engine'&&['menu_checked','unavailable'].includes(recommendation.status);
  const hasReport=Boolean(vm.report);
  setText('next',checked?recommendation.instruction:hasReport?'This earlier suggestion was not checked against the fixture menu. Review the original in Evidence.':fallback);
  $('next-status').hidden=!hasReport;
  setText('next-status',checked?(recommendation.status==='unavailable'?'Engine · unavailable with this fixture':'Engine · menu checked; future run, D2 pending'):'Legacy suggestion · unvalidated');
}
function renderLinearity(vm,plot){
  const root=$('linearity-chart'),wrap=$('linearity-wrap');root.replaceChildren();
  wrap.hidden=true;$('diagnostic-plots').classList.remove('has-linearity');
  if(!plot.training)return;
  const check=vm.diagnosis?.amplitude_scaling?.checks.find(c=>sameSettings(c.settings_small,plot.settings)||sameSettings(c.settings_large,plot.settings));
  if(!check)return;
  const captures=vm.visible.filter(e=>e.kind==='acquisition'),[i,j]=check.training_capture_indices;
  const small=captures[i]?.payload,large=captures[j]?.payload;
  if(!sameSettings(small?.settings,check.settings_small)||!sameSettings(large?.settings,check.settings_large))return;
  const t=large.data.time_s,ts=small.data.time_s;
  if(!t?.length||t.length!==ts?.length||t.some((x,k)=>Math.abs(x-ts[k])>1e-9))return;
  const centered=c=>{const y=c.data.out_v.map((v,k)=>v-c.data.ref_v[k]),mean=y.reduce((a,b)=>a+b,0)/y.length;return y.map(v=>v-mean);};
  const a=centered(small).map(v=>v*check.amplitude_ratio),b=centered(large);
  if(a.length!==t.length||b.length!==t.length||![...a,...b,...t].every(Number.isFinite))return;
  const rms=1000*Math.sqrt(a.reduce((sum,v,k)=>sum+(b[k]-v)**2,0)/a.length);
  if(Math.abs(rms-check.channels.out_v.dc_removed_rms_mv)>1e-6)return;
  wrap.hidden=false;$('diagnostic-plots').classList.add('has-linearity');
  const width=root.clientWidth,height=root.clientHeight||84,left=32,right=12,top=9,bottom=18;
  const limit=Math.max(.01,...a.map(Math.abs),...b.map(Math.abs))*1.08;
  const X=x=>left+(x-t[0])/(t.at(-1)-t[0]||1)*(width-left-right),Y=y=>top+(1-y/limit)*(height-top-bottom)/2;
  root.setAttribute('viewBox',`0 0 ${width} ${height}`);
  node(root,'title',{id:'linearity-chart-title'},'Small-signal output scaled against large-signal output');
  node(root,'desc',{id:'linearity-chart-description'},`DC means removed. Gray dashed is the ${check.settings_small.amplitude_v} V output multiplied by ${check.amplitude_ratio}. Orange is the ${check.settings_large.amplitude_v} V output. Difference ${rms.toFixed(2)} mV RMS. Training evidence only, not independent verification.`);
  for(const y of [-1,0,1].map(v=>v*limit/1.08)){node(root,'line',{x1:left,x2:width-right,y1:Y(y),y2:Y(y),stroke:'#dce3dc'});node(root,'text',{x:left-5,y:Y(y)+3,'text-anchor':'end',fill:'#55635e','font-size':9},y.toFixed(1));}
  for(const [x,label]of [[t[0],'0'],[t.at(-1),t.at(-1).toFixed(1)+' s']])node(root,'text',{x:X(x),y:height-2,'text-anchor':x===t[0]?'start':'end',fill:'#55635e','font-size':9},label);
  for(const [key,y,color,dash]of [['scaled-small',a,'#7a827e','4 3'],['large',b,'#ca4c31','none']])node(root,'path',{d:t.map((x,k)=>(k?'L':'M')+X(x).toFixed(2)+','+Y(y[k]).toFixed(2)).join(''),fill:'none',stroke:color,'stroke-width':1.6,'stroke-dasharray':dash,'data-series':key});
  root.dataset.rmsMv=rms;root.dataset.inputStatus=check.status;
  setText('scaled-label',`${check.settings_small.amplitude_v} V output ×${check.amplitude_ratio}`);
  setText('large-label',`${check.settings_large.amplitude_v} V output`);
  setText('linearity-score',rms.toFixed(2)+' mV RMS');
  setText('linearity-title',check.status==='input_scaling_mismatch'?'Input scaling differs':check.status==='scaling_consistent'?'Output scales with input':'Output stops scaling');
}
function renderResidual(series){
  const root=$('residual'),observed=series.find(s=>s.key==='observed'),models=series.filter(s=>['baseline','predicted'].includes(s.key)&&state.trace[s.key]&&s.y?.length===observed?.y?.length&&s.x.every((x,i)=>Math.abs(x-observed.x[i])<1e-9));
  const active=Boolean(observed&&models.length&&state.chartGeometry);
  $('residual-wrap').hidden=!active;root.replaceChildren();if(!active)return;
  const width=root.clientWidth,height=60,left=state.chartGeometry.left,right=state.chartGeometry.right;
  const xs=observed.x,xmin=Math.min(...xs),xmax=Math.max(...xs),g={width,left,right,X:x=>left+(x-xmin)/(xmax-xmin||1)*(width-left-right)};
  root.setAttribute('viewBox',`0 0 ${width} ${height}`);
  const rows=models.map(s=>({...s,residual:s.y.map((y,i)=>1000*(observed.y[i]-y))}));
  const limit=Math.max(1,...rows.flatMap(s=>s.residual.map(Math.abs))),Y=v=>39-17*v/limit;
  node(root,'title',{},'Observed minus model. Both residuals use the same millivolt scale.');
  node(root,'text',{x:g.left,y:12,fill:'#55635e','font-size':10},'Observed − model · mV');
  node(root,'text',{x:width-g.right,y:12,'text-anchor':'end',fill:'#55635e','font-size':10},'±'+limit.toFixed(limit<10?1:0)+' mV');
  node(root,'line',{x1:g.left,x2:width-g.right,y1:Y(0),y2:Y(0),stroke:'#dce3dc'});
  for(const s of rows){const d=s.x.map((x,i)=>(i?'L':'M')+g.X(x).toFixed(2)+','+Y(s.residual[i]).toFixed(2)).join('');node(root,'path',{d,fill:'none',stroke:s.key==='baseline'?'#7a827e':'#315e91','stroke-width':1.4,'data-residual':s.key});}
}
function circuitSymbol(root,element,x,y,angle){
  const g=node(root,'g',{transform:`translate(${x} ${y}) rotate(${angle})`,stroke:'#315e91','stroke-width':1.6,fill:'#f7f8f5','data-component':element.name,'data-anode':element.kind==='D'?element.a:'','data-cathode':element.kind==='D'?element.b:''});
  if(element.kind==='R')node(g,'rect',{x:-12,y:-5,width:24,height:10,rx:1});
  else if(element.kind==='C'){node(g,'rect',{x:-12,y:-8,width:24,height:16,stroke:'none'});node(g,'path',{d:'M-4-8v16M4-8v16M-12 0h8M4 0h8',fill:'none'});}
  else if(element.kind==='D'){node(g,'rect',{x:-12,y:-9,width:24,height:18,stroke:'none'});node(g,'path',{d:'M-12 0h3M-9-7v14L5 0ZM7-8v16M7 0h5',fill:'none'});}
}
function renderCircuit(vm){
  const root=$('proposal-circuit'),proposal=last(vm.visible,['netlist_proposed']),elements=proposal?.payload.elements;
  root.replaceChildren();const hidden=!Array.isArray(elements)||!elements.length;root.toggleAttribute('hidden',hidden);if(hidden)return;
  const shape=proposalDescription(elements),line=(x1,y1,x2,y2)=>node(root,'line',{x1,y1,x2,y2,stroke:'#687d70','stroke-width':1.5});
  if(shape){
    root.setAttribute('viewBox','0 0 340 116');node(root,'title',{},`Recorded proposal: resistor from IN to OUT; diode anode ${shape.diode.a}, cathode ${shape.diode.b}.`);
    line(28,28,294,28);line(294,28,294,94);line(28,94,310,94);
    circuitSymbol(root,elements.find(e=>e.kind==='R'),141,28,0);circuitSymbol(root,shape.diode,294,62,shape.diode.a==='OUT'?90:-90);
    for(const [x,y,label]of [[28,28,'IN'],[294,28,'OUT'],[28,94,'REF']]){node(root,'circle',{cx:x,cy:y,r:3,fill:'#1f6954'});node(root,'text',{x,y:y===28?14:110,'text-anchor':'middle',fill:'#55635e','font-size':10},label);}
    node(root,'text',{x:141,y:49,'text-anchor':'middle',fill:'#315e91','font-size':11},elements.find(e=>e.kind==='R').name);node(root,'text',{x:269,y:66,'text-anchor':'end',fill:'#315e91','font-size':11},shape.diode.name);
  }else{
    root.setAttribute('viewBox',`0 0 340 ${Math.max(116,elements.length*28+12)}`);node(root,'title',{},'Recorded netlist connections; matching node names are electrically connected.');
    elements.forEach((e,i)=>{const y=22+i*28;line(70,y,270,y);circuitSymbol(root,e,170,y,0);node(root,'text',{x:30,y:y+4,fill:'#55635e','font-size':11},e.a);node(root,'text',{x:290,y:y+4,fill:'#55635e','font-size':11},e.b);node(root,'text',{x:125,y:y-6,fill:'#315e91','font-size':10},e.name);});
  }
}
function renderStages(vm){
  const root=$('story-stages'),focused=root.contains(document.activeElement)?document.activeElement.dataset.stage:null;
  root.hidden=!vm.mode.includes('discovery');root.replaceChildren();if(root.hidden)return;
  const assessment=last(vm.visible,['initial_family_assessment']),proposal=last(vm.visible,['netlist_proposed']),prediction=last(vm.visible,['prediction_committed']),verification=vm.verification;
  const familyLabel=expandedLinear(vm)?'Linear':'RC';
  const stages=[['Initial check',assessment,assessment?.payload.status==='all_candidates_inadequate'?familyLabel+' models fail':familyLabel+' models checked'],['Propose structure',proposal,'Structure proposed'],['Lock predictions',prediction,'Predictions locked'],['Check predictions',verification,verification?.payload.passed?'Verification passed':'Verification failed']];
  const active=stages.findLastIndex(s=>Boolean(s[1]));
  stages.forEach(([pending,event,done],i)=>{const b=document.createElement('button');b.dataset.stage=i;b.disabled=!event;b.className='story-stage'+(event?' reached':'')+(i===active?' current':'');b.textContent=event?done:pending;b.setAttribute('aria-label',(event?'Go to: ':'Pending: ')+b.textContent);if(i===active)b.setAttribute('aria-current','step');b.onclick=()=>select(event.sequence,true);root.appendChild(b);});
  if(focused!==null)root.querySelector(`[data-stage="${focused}"]`)?.focus({preventScroll:true});
}
function wiring(settings,hardware){
  const root=$('wiring');root.replaceChildren();
  node(root,'title',{},'Drive to input through the jumper or shunt; output load returns to REF.');
  if(!settings){node(root,'text',{x:170,y:60,'text-anchor':'middle',fill:'#55635e','font-size':12},'Connection instructions appear with a measurement.');setText('instruction','No measurement requested yet.');return;}
  const line=(x1,y1,x2,y2)=>node(root,'line',{x1,y1,x2,y2,stroke:'#687d70','stroke-width':1.5});
  line(18,40,320,40);line(18,85,320,85);
  for(const [x,label]of [[18,'DRIVE'],[140,'IN'],[270,'OUT']]){node(root,'circle',{cx:x,cy:40,r:3,fill:'#1f6954'});node(root,'text',{x,y:19,'text-anchor':x===18?'start':'middle',fill:'#1c2b27','font-size':10},label);}
  node(root,'rect',{x:58,y:30,width:67,height:20,rx:2,fill:'#f3f6ef',stroke:'#91a494'});
  node(root,'text',{x:91,y:43,'text-anchor':'middle',fill:'#1c2b27','font-size':9},settings.shunt_ohm?'1 kΩ shunt':'0 Ω jumper');
  node(root,'rect',{x:165,y:26,width:67,height:29,rx:3,fill:'#183d35'});node(root,'text',{x:199,y:45,'text-anchor':'middle',fill:'#fff','font-size':10},'Circuit');line(199,55,199,85);
  node(root,'text',{x:18,y:103,fill:'#55635e','font-size':10},'REF');
  if(settings.load_ohm){line(290,40,290,85);node(root,'rect',{x:268,y:60,width:45,height:21,rx:2,fill:'#fff5e6',stroke:'#b9945b'});node(root,'text',{x:290,y:74,'text-anchor':'middle',fill:'#795018','font-size':10},settings.load_ohm/1000+' kΩ');}
  setText('instruction',(settings.shunt_ohm?'Replace the DRIVE–IN jumper with a 1 kΩ shunt.':'Keep the 0 Ω jumper between DRIVE and IN.')+' '+(settings.load_ohm?`Connect ${settings.load_ohm/1000} kΩ from OUT to REF.`:'Leave OUT–REF unloaded.'));
  setText('mount-note',hardware?'Logical connections only. Verify the physical fixture before driving it.':'Simulated mounting · logical nodes, not a breadboard layout.');
  badge($('mount-actor'),{name:hardware?'Operator':'Operator · simulated',kind:'operator'});
}
function renderTimeline(vm){
  const root=$('timeline'),previousScroll=root.scrollTop,focused=root.contains(document.activeElement)?document.activeElement.closest('button')?.dataset.index:null;root.replaceChildren();
  state.milestones=state.events.map((e,i)=>labels[e.kind]?i:-1).filter(i=>i>=0);
  const known=state.milestones.filter(i=>i<=state.cursor),current=known.at(-1);
  for(const i of known){const e=state.events[i],li=document.createElement('li'),button=document.createElement('button');
    button.className='event'+(i===current?' active':'');button.dataset.index=i;
    if(i===current)button.setAttribute('aria-current','step');
    const time=document.createElement('span');time.className='time';time.textContent=elapsed(seconds(e));
    const actor=document.createElement('span');badge(actor,actorFor(e));
    const label=document.createElement('span');label.className='event-label';label.textContent=labels[e.kind];
    button.append(time,actor,label);const arrow=document.createElementNS(NS,'svg');arrow.setAttribute('viewBox','0 0 20 20');arrow.setAttribute('aria-hidden','true');node(arrow,'path',{d:'M5 10h9m-4-4 4 4-4 4'});button.appendChild(arrow);
    button.onclick=()=>select(i,true);li.appendChild(button);root.appendChild(li);
  }
  // Fit a whole number of recent rows, including wrapped mobile labels. The
  // latest known action stays current even at an unlabelled API/tool event.
  const style=getComputedStyle(root),limit=parseFloat(style.maxHeight),padding=parseFloat(style.paddingTop)+parseFloat(style.paddingBottom);
  let height=padding;
  for(const row of [...root.children].reverse()){const h=row.getBoundingClientRect().height;if(height>padding&&height+h>limit)break;height+=h;}
  root.style.height=Math.ceil(height)+'px';
  const resized=state.timelineWidth!==root.clientWidth;
  root.scrollTop=state.lastCursor!==state.cursor||resized?root.scrollHeight-root.clientHeight:previousScroll;
  state.timelineWidth=root.clientWidth;
  state.lastCursor=state.cursor;
  if(focused!==null)root.querySelector(`[data-index="${focused}"]`)?.focus({preventScroll:true});
}
function render(){
  if(!state.events.length){setText('status','Waiting for the first event');return;}
  const vm=reduce(state.events,state.cursor),plot=plotFor(vm),{focus,settings,series,predictionEvent,unit}=plot;
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
  const report=readingAid(vm,brief(vm));setText('explanation',report.explanation);setText('uncertainty',report.uncertainty);renderNext(vm,report.next);badge($('report-actor'),report.actor);
  $('report-note').hidden=!report.adapted;setText('report-note','Plain-language reading aid · '+(vm.report?'original report':'recorded proposal')+' in Evidence.');renderCircuit(vm);
  const condition=$('condition');condition.replaceChildren();
  for(const event of plot.options){const option=document.createElement('option');option.value=event.sequence;option.textContent=conditionName(event.payload.settings)+(event.kind==='acquisition'?' · training':event.kind.includes('prediction_committed')?' · prediction':' · verification');option.selected=event.sequence===focus?.sequence;condition.appendChild(option);}
  if(!plot.options.length){const option=document.createElement('option');option.textContent='Waiting for a capture';condition.appendChild(option);}condition.disabled=plot.options.length<2;
  renderLinearity(vm,plot);
  renderChart(series,unit,settings?.kind==='dc_pair'?'Drive level (V)':'Time (s)',focus?.sequence!==state.lastFocus&&Boolean(predictionEvent));state.lastFocus=focus?.sequence;
  renderResidual(series);
  setText('plot-title',plot.training&&series.some(s=>s.key==='baseline')?'Compare explanations':'Prediction & observation');
  setText('prediction-label',plot.training?'Spark structure · fit':'Committed prediction');
  setText('baseline-label',plot.expanded?(plot.training?'Best tested linear model':'Frozen linear prediction'):(plot.training?'Best RC fit':'Frozen RC prediction'));
  document.querySelector('[data-trace=predicted]').title=plot.training?"Engine simulation of Spark's structure, fitted to training observations.":'Numerical prediction recorded before the matching verification observation.';
  for(const button of document.querySelectorAll('[data-trace]'))button.disabled=!series.some(s=>s.key===button.dataset.trace);
  setText('plot-source',focus?.kind.includes('prediction_committed')?'Prediction only':predictionEvent?'Reserved verification':'Training comparison');
  const baselineName=plot.expanded?'Linear':'RC';
  const outcomes={proposal_only_passes:baselineName+' fails; proposal passes',both_pass:'Both pass · weak discrimination',neither_passes:'Neither model passes',baseline_only_passes:'Only '+baselineName+' passes'};
  const metric=plot.metric;
  setText('comparison-note',metric?(plot.baseline.reconstructed?baselineName+' reconstructed · ':'')+`OUT RMS: ${baselineName} ${metric.baseline.out_rms_mv.toFixed(2)} mV / Spark ${metric.proposal.out_rms_mv.toFixed(2)} mV · `+outcomes[metric.discrimination]:plot.baseline?.reconstructed?baselineName+' reconstructed from frozen training fit; Spark prediction recorded before observation.':plot.baseline?'Both models frozen on training data; predictions recorded before observations.':plot.reconstructed?'Reconstructed training fits · computed after this run; not precommitted predictions.':plot.training&&series.some(s=>s.key==='baseline'||s.key==='predicted')?'Training fits · engine simulations; independent verification is a separate check.':predictionEvent?'Prediction recorded before the matching verification observation.':'Observed waveform · no model comparison recorded yet.');
  const scaling=vm.diagnosis?.amplitude_scaling;
  const scalingCheck=scaling?.checks.find(c=>sameSettings(c.settings_small,settings)||sameSettings(c.settings_large,settings));
  if(plot.training&&scalingCheck&&!plot.reconstructed){
    const text=scalingCheck.status==='output_scaling_mismatch'?`output fails to scale (${scalingCheck.channels.out_v.dc_removed_rms_mv.toFixed(2)} mV RMS)`:scalingCheck.status==='input_scaling_mismatch'?'input scaling differs; output alone is inconclusive':'input and output scaling are consistent';
    setText('comparison-note','Training amplitude check · '+text+' · DC means removed; calibrated fixture required.');
  }
  setText('linearity-evidence',scaling?JSON.stringify(scaling,null,2):'No amplitude-scaling diagnostic was recorded at this point.');
  const check=vm.verification?.payload;
  const proof=$('verification');proof.replaceChildren();proof.classList.toggle('failed',check?.passed===false);
  if(check){const icon=document.createElementNS(NS,'svg');icon.setAttribute('viewBox','0 0 20 20');icon.setAttribute('aria-hidden','true');node(icon,'path',{d:check.passed?'m4 10 4 4 8-9':'m5 5 10 10M15 5 5 15'});proof.append(icon);}
  const note=check?(check.passed?'Reserved checks passed':'Reserved checks failed')+(plot.training?' · showing training data':' · no refit on verification data'):predictionEvent?(focus.kind.includes('prediction_committed')?'Prediction locked. The verification observation has not arrived.':'Prediction was committed before this observation.'):'Training data informs the hypothesis; it does not confirm it.';
  proof.append(document.createTextNode(note));
  const requested=vm.mounting?.kind==='instrument_request',mountSettings=requested?vm.mounting.payload.settings:settings;
  wiring(mountSettings,vm.isHardware);
  setText('mount-title',requested?'Requested connections':'Shown connections');
  if(!requested&&focus&&focus!==vm.focus)setText('mount-note','Shown condition · no new mounting requested. Logical nodes only.');
  if(vm.mounting?.kind==='instrument_request'&&!mountSettings){setText('instruction','This earlier request has no structured connection settings. Inspect the original request below.');setText('mount-note','Previous connections are not presented as the new request.');}
  renderStages(vm);renderTimeline(vm);
  const evidence=last(vm.visible,['proposal_fit','netlist_proposed','repair_requested','repair_applied','instrument_request']);
  setText('evidence-note',evidence?labels[evidence.kind]:'No proposal or requested action at this point.');
  setText('evidence',evidence?.payload.rendered_fitted_proposal?[evidence.payload.rendered_fitted_proposal,evidence.payload.rendered_fitted_diode||'',JSON.stringify({training_passed:evidence.payload.training_passed,topology_preserved:evidence.payload.generated_topology_sha256===evidence.payload.fitted_topology_sha256},null,2)].join('\n'):evidence?JSON.stringify(evidence.payload,null,2):'—');
  setText('raw',JSON.stringify(state.events[state.cursor],null,2));
  const reportCall=vm.report?[...vm.visible].reverse().find(e=>e.kind==='tool_call'&&e.sequence<vm.report.sequence&&e.payload.name==='finish_report'):null;
  let originalReport=reportCall?.payload.arguments||vm.report?.payload;
  if(typeof originalReport==='string'){try{originalReport=JSON.parse(originalReport);}catch{/* Preserve an unparseable historical argument verbatim. */}}
  setText('original-report',vm.report?JSON.stringify(originalReport,null,2):'No report recorded at this point.');
  setText('next-check-evidence',vm.report?.payload.next_measurement?JSON.stringify(vm.report.payload.next_measurement,null,2):'No fixture-menu check was recorded. Free-text suggestions are not shown as executable instructions.');
  $('expand-report').disabled=!vm.report;
  setText('expand-report',!vm.report?'Report not recorded yet':document.querySelector('.evidence-drawer').open?'Hide original report':'Read original report');
  setText('comparison-provenance',JSON.stringify({note:$('comparison-note').textContent,selection:'Default training view maximizes RMS separation between the available linear baseline and proposed fit; before a proposal, baseline versus observation. Verification observations never select or fit a training model.',initial:plot.models.rc?{event_sequence:plot.models.rc.event.sequence,reconstructed:plot.models.rc.reconstructed,family:plot.models.rc.data.family,candidate_families:plot.models.rc.data.candidate_families,parameters:plot.models.rc.data.parameters}:null,proposal:plot.models.spark?{event_sequence:plot.models.spark.event.sequence,reconstructed:plot.models.spark.reconstructed}:null,verification_baseline:plot.baseline?{event_sequence:plot.baseline.event.sequence,reconstructed:plot.baseline.reconstructed,originally_committed:!plot.baseline.reconstructed,separation:plot.baseline.data.separation}:null,verification_comparison:plot.verification?{reconstructed:plot.verification.reconstructed,...plot.verification.data}:null,source_sha256:state.record.source_sha256},null,2));
  $('cursor').max=state.events.length-1;$('cursor').value=state.cursor;setText('position',(state.cursor+1)+' / '+state.events.length);
  $('previous').disabled=state.cursor<=0;$('next-event').disabled=state.cursor>=state.events.length-1;$('play').disabled=state.events.length<2;
  $('follow').hidden=!live;$('follow').disabled=state.following;
  setText('integrity',(state.record.integrity==='verified_prefix'?'Hash chain checked through the latest received event.':'Source hash chain verified at export.')+' No external attestation. Record '+state.record.run_id+' · SHA-256 '+(state.record.source_sha256||'pending'));
}
function stop(){if(state.timer)clearInterval(state.timer);state.timer=null;$('play').querySelector('span').textContent='Replay run';$('play').setAttribute('aria-label','Replay recorded events');}
function select(index,announce=false){stop();state.following=false;state.condition=null;state.cursor=Math.max(0,Math.min(index,state.events.length-1));render();if(announce)setText('announcement',(labels[state.events[state.cursor].kind]||'Event')+'. '+$('status').textContent);}
function milestone(direction){const available=state.milestones.filter(i=>direction<0?i<state.cursor:i>state.cursor);select(direction<0?available.at(-1)??0:available[0]??state.events.length-1,true);}
$('previous').onclick=()=>milestone(-1);$('next-event').onclick=()=>milestone(1);$('cursor').oninput=e=>select(Number(e.target.value));
$('condition').onchange=e=>{state.condition=Number(e.target.value);render();};
$('expand-report').onclick=()=>{const drawer=document.querySelector('.evidence-drawer');drawer.open=!drawer.open;if(drawer.open){$('original-report').setAttribute('tabindex','-1');$('original-report').focus();}};
document.querySelector('.evidence-drawer').ontoggle=e=>{$('expand-report').setAttribute('aria-expanded',String(e.target.open));setText('expand-report',$('expand-report').disabled?'Report not recorded yet':e.target.open?'Hide original report':'Read original report');};
$('play').onclick=()=>{if(state.timer){stop();return;}state.following=false;state.condition=null;state.cursor=0;render();$('play').querySelector('span').textContent='Pause';$('play').setAttribute('aria-label','Pause replay');state.timer=setInterval(()=>{if(state.cursor>=state.events.length-1){stop();return;}state.cursor++;render();},950);};
$('follow').onclick=()=>{stop();state.condition=null;state.following=true;state.cursor=state.events.length-1;render();};
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
