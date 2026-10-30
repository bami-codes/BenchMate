/* Read-only presentation of the recorded physical RC schema. No fitting or I/O. */
const physicalRCLabels={
  physical_measurement_selected:'Measurement selected',operator_action_requested:'Manual wiring requested',
  operator_wiring_confirmation:'Wiring confirmed by operator',physical_acquisition_plan_frozen:'Model parameters frozen',
  physical_observation:'Physical waveform acquired',unloaded_training_completed:'Time constant fitted',
  physical_model_comparison:'Loaded alternatives compared',physical_verification:'Reserved waveform checked'
};
const isPhysicalRC=events=>events[0]?.payload.mode==='live_spark_new_physical_RC_measurements';
const physicalModelName=key=>({nominal_rc:'Nominal RC',r_changed:'R change',c_changed:'C change'})[key]||key;
function physicalRCView(events,cursor,selection=null){
  const visible=events.slice(0,cursor+1),conditions=[];
  const find=phase=>conditions.findLast(c=>c.phase===phase);
  let training=null,verification=null,report=null,terminal=null,provider=null,load=null;
  for(const event of visible){
    const p=event.payload;
    if(event.kind==='provider_configuration')provider=p;
    if(event.kind==='tool_result'&&Number.isFinite(p.result?.load_ohm))load=p.result.load_ohm;
    if(event.kind==='physical_measurement_selected')conditions.push({id:event.sequence,phase:p.phase,selection:event,settings:p.settings,fixture:p.fixture});
    if(event.kind==='physical_acquisition_plan_frozen'&&find(p.phase))find(p.phase).plan=event;
    if(event.kind==='physical_observation'&&find(p.phase)&&p.source==='physical'&&p.all_guards_passed===true)find(p.phase).observation=event;
    if(event.kind==='unloaded_training_completed')training=event;
    if(event.kind==='physical_model_comparison'&&find(p.phase))find(p.phase).comparison=event;
    if(event.kind==='physical_verification'){
      verification=event;
      if(find('reserved_sine'))find('reserved_sine').comparison=event;
    }
    if(event.kind==='agent_report')report=event;
    if(['run_completed','run_failed'].includes(event.kind))terminal=event;
  }
  const focus=conditions.find(c=>c.id===selection)||conditions.at(-1)||null,series=[];
  const scores=focus?.comparison?.payload.scores||null;
  if(focus?.observation){
    const p=focus.observation.payload,d=p.data,b=p.baseline;
    const x=d.frame_time_s.map((v,i)=>v+d.output_delay_s[i]);
    series.push({key:'observed',x,y:d.output_v.map(v=>v-b.output_v)});
    series.push({key:'drive',x:d.frame_time_s.map((v,i)=>v+d.input_delay_s[i]),y:d.input_v.map(v=>v-b.input_v)});
    for(const [key,model] of [['baseline','r_changed'],['predicted','c_changed']]){
      const values=scores?.[model]?.prediction?.predicted_output_v;
      if(values?.length===x.length)series.push({key,x,y:values.map(v=>v-b.output_v)});
    }
  }
  const observations=conditions.filter(c=>c.observation),origin=observations.length?'hardware':'unknown';
  const latest=conditions.at(-1),loaded=conditions.find(c=>c.phase==='attach_output_load_step');
  const supported=Object.entries(loaded?.comparison?.payload.scores||{}).filter(([,s])=>s.passed).map(([name])=>name);
  let status='Waiting for Spark to select a measurement';
  if(latest)status=latest.observation?'Physical waveform acquired':latest.plan?'Plan fixed · awaiting measurement':'Measurement selected · awaiting operator/plan';
  if(training&&latest?.phase==='unloaded_step')status=training.payload.training_adequate?'Time constant fitted · R/C unresolved':'Initial response check failed';
  if(loaded?.comparison&&latest?.phase==='attach_output_load_step')status=supported.length===1?'One alternative supported · reserved check pending':'Loaded check remains unresolved';
  if(verification)status=verification.payload.passed?'Reserved check passed · report pending':'Reserved check failed';
  if(report)status=report.payload.verdict==='verified'?'Verified within declared RC alternatives':'Conclusion withheld';
  if(terminal?.kind==='run_failed')status='Session failed';
  return {visible,conditions,focus,series,scores,training,verification,report,terminal,provider,load,
    observations,origin,status,supported,loaded,mode:events[0]?.payload.mode};
}
function physicalRCReading(vm){
  let explanation='Spark can choose from a bounded menu of new physical measurements.';
  if(vm.training)explanation=`The first trace gives a ${(vm.training.payload.tau_s*1000).toFixed(2)} ms time constant. R and C remain indistinguishable without another condition.`;
  if(vm.loaded?.selection&&!vm.loaded.comparison)explanation='Spark chose an output load to separate the R-change and C-change predictions. The operator performs the wiring.';
  if(vm.loaded?.comparison)explanation=vm.supported.length===1?`The added load separates the alternatives. Only ${physicalModelName(vm.supported[0]).toLowerCase()} meets the whole-waveform and every regional check.`:'The loaded measurement does not support a unique declared alternative.';
  if(vm.verification)explanation=vm.verification.payload.passed?'A new, lower-amplitude sine also matches the same frozen model. The reserved output was not used to refit it.':'The frozen model failed the new sine check. The diagnosis remains unconfirmed.';
  if(vm.report?.payload.verdict==='verified')explanation=`${physicalModelName(vm.report.payload.candidate)} explains both the loaded step and the reserved sine within the declared RC alternatives.`;
  if(vm.terminal?.kind==='run_failed')explanation='The physical run stopped. The record retains its earlier observations and the failure; no completion is implied.';
  return {explanation,uncertainty:'Known RC alternatives; provisional channel maps and a 9 mV engineering allowance. No absolute calibration, topology discovery, or repair is claimed.',
    next:vm.report?'The original report records a suggested follow-up. This viewer schedules no experiment.':vm.verification?'Record the supported conclusion and remaining limits.':vm.loaded?.comparison?'Check the unchanged models on the reserved sine.':vm.training?'Use an allowed load to distinguish R change from C change.':'Inspect the allowed experiment and select a measurement.'};
}
function renderPhysicalRC(){
  document.body.classList.add('physical-rc');
  const vm=physicalRCView(state.events,state.cursor,state.condition),focus=vm.focus,live=state.record.transport==='live_log';
  const reading=physicalRCReading(vm),observed=focus?.observation?.payload;
  setText('headline','Spark at the workbench');
  setText('session-description','Choose a discriminating measurement. Test the same model on a new waveform.');
  setText('source',vm.origin==='hardware'?'Physical observations · provisional':'Source pending');
  setText('transport',state.integrityFailed?'Live log · integrity error':live&&state.connection==='disconnected'?'Live log · disconnected':live?(state.following?'Live log':'Live log · reviewing'):'Replay');
  setText('scope','Recorded physical RC experiment · measured-input conditional response.');
  $('connection-alert').hidden=!state.connectionMessage;setText('connection-alert',state.connectionMessage);
  setText('status',vm.status);
  $('status-dot').style.background=vm.terminal?.kind==='run_failed'||vm.verification?.payload.passed===false?'var(--error)':vm.verification?.payload.passed?'var(--success)':'var(--warning)';
  setText('actor',vm.provider?vm.provider.model+' · '+vm.provider.reasoning_effort:'Provider pending');
  const total=vm.terminal?.payload.instrument?.retained_frames;
  setText('count',vm.observations.length+' waveform observations'+(Number.isFinite(total)?' · '+total.toLocaleString('en-US')+' total frames':''));
  setText('duration',elapsed(seconds(state.events[state.cursor]))+' elapsed');
  setText('explanation',reading.explanation);setText('uncertainty',reading.uncertainty);setText('next',reading.next);
  badge($('report-actor'),vm.report?sparkActor(vm.report.sequence):{name:'Engine',kind:'engine'});
  $('report-note').hidden=false;setText('report-note','English reading aid · original model report preserved in Evidence.');
  $('next-status').hidden=true;$('proposal-circuit').hidden=true;
  const select=$('condition');select.replaceChildren();
  for(const c of vm.conditions){
    const option=document.createElement('option');option.value=c.id;
    option.textContent=(c.settings.kind==='sine'?c.settings.frequency_hz+' Hz sine':'Step')+' · ±'+c.settings.amplitude_v+' V · '+(c.fixture==='unloaded'?'unloaded':'output load')+(c.phase==='reserved_sine'?' · reserved':c.phase==='unloaded_step'?' · training':' · discrimination')+(!c.observation?' · pending':'');
    option.selected=c===focus;select.appendChild(option);
  }
  if(!vm.conditions.length){const option=document.createElement('option');option.textContent='Waiting for a selection';select.appendChild(option);}
  select.disabled=vm.conditions.length<2;
  $('linearity-wrap').hidden=true;$('diagnostic-plots').classList.remove('has-linearity');
  renderChart(vm.series,'V',state.presentation==='evidence'?'Time at channel read completion (s)':'Time (s)',focus?.id!==state.lastFocus);state.lastFocus=focus?.id;
  renderResidual(vm.series);
  setText('chart-title','Change from separately measured HOLD origins');
  setText('chart-description','Observed output and recorded R-change/C-change conditional predictions. Separate HOLD origins are subtracted for display; residuals are unchanged. These are not absolute-voltage predictions.');
  setText('plot-title','Compare the frozen alternatives');setText('baseline-label','R change · frozen');setText('prediction-label','C change · frozen');setText('drive-label','Measured IN');
  for(const b of document.querySelectorAll('[data-trace]'))b.disabled=!vm.series.some(s=>s.key===b.dataset.trace);
  document.querySelector('[data-trace=predicted]').title='Recorded conditional curve: model parameters fixed before measurement; measured IN supplies the input afterward.';
  setText('plot-source',focus?.phase==='unloaded_step'?'Training observation':focus?.phase==='reserved_sine'?'Reserved verification':'Loaded discrimination');
  let caption='No waveform has been acquired for this selection.';
  if(focus?.plan&&!observed)caption='Model parameters are fixed. Conditional curves require the new measured IN; no future waveform is shown.';
  if(observed)caption='Changes from separate HOLD origins; no absolute-voltage claim. Model curves appear only when recorded comparisons arrive.';
  if(vm.scores)caption='Changes from separate HOLD origins. Models fixed before capture; curves use measured IN. Scores: whole / worst-region RMS; both must meet 9 mV.';
  if(focus?.phase==='unloaded_step'&&vm.training)caption=`Training only · tau ${(vm.training.payload.tau_s*1000).toFixed(3)} ms; fit RMS ${vm.training.payload.training_RMS_mV.toFixed(3)} mV. No reconstructed fit curve is added.`;
  setText('comparison-note',caption);
  const proof=$('verification');proof.replaceChildren();proof.classList.toggle('failed',vm.scores?Object.values(vm.scores).every(s=>!s.passed):false);
  if(vm.scores){
    proof.classList.add('physical-scores');
    for(const [model,s]of Object.entries(vm.scores)){
      const item=document.createElement('span');item.dataset.model=model;item.dataset.passed=String(s.passed);
      const worst=Math.max(...s.regions.map(r=>r.RMS_mV));
      item.textContent=`${physicalModelName(model)}: ${s.RMS_mV.toFixed(2)} / ${worst.toFixed(2)} mV · ${s.passed?'PASS':'FAIL'}`;
      item.title=`Whole RMS ${s.RMS_mV.toFixed(3)} mV; worst regional RMS ${worst.toFixed(3)} mV. Both must meet 9 mV.`;proof.appendChild(item);
    }
  }else{proof.classList.remove('physical-scores');proof.textContent=focus?.phase==='unloaded_step'?'The first trace fits tau; it cannot identify R and C separately.':'Awaiting the recorded comparison.';}
  const mount=focus?{...focus.settings,load_ohm:focus.fixture==='output_load'?vm.load:null,shunt_ohm:0}:null;
  wiring(mount,true);setText('mount-title','Recorded connections');
  setText('instruction',focus?(focus.fixture==='output_load'?`Output-load fixture${vm.load?' · '+(vm.load/1000)+' kΩ OUT to REF':''}.`:'Unloaded fixture.'): 'No physical measurement selected at this point.');
  setText('mount-note','Read-only replay/log view. These are recorded connections, not a request to rewire the current board.');
  const stages=$('story-stages');stages.hidden=false;stages.replaceChildren();
  const rows=[['Measure tau',vm.training,'Tau fitted'],['Choose a load',vm.loaded?.selection,'Load selected'],['Freeze reserved models',vm.conditions.find(c=>c.phase==='reserved_sine')?.plan,'Models fixed'],['Check a new waveform',vm.verification,vm.verification?.payload.passed?'Reserved check passed':'Reserved check failed']];
  const current=rows.findLastIndex(r=>r[1]);
  rows.forEach(([pending,event,done],i)=>{const b=document.createElement('button');b.className='story-stage'+(event?' reached':'')+(i===current?' current':'');b.textContent=event?done:pending;b.disabled=!event;b.dataset.stage=i;if(i===current)b.setAttribute('aria-current','step');b.onclick=()=>selectPhysicalStage(event.sequence);stages.appendChild(b);});
  renderTimeline(vm);
  setText('evidence-note','Recorded model parameters, comparisons and acquisition origins.');
  setText('evidence',JSON.stringify({selected_action:focus?.selection?.payload,plan:focus?.plan?.payload,
    observation_origin:observed?{source:observed.source,boot_id:observed.boot_id,baseline:observed.baseline,all_guards_passed:observed.all_guards_passed}:null,
    checks:vm.scores?Object.fromEntries(Object.entries(vm.scores).map(([k,v])=>[k,Object.fromEntries(Object.entries(v).filter(([name])=>name!=='prediction'))])):null},null,2));
  setText('original-report',vm.report?JSON.stringify(vm.report.payload,null,2):'No report recorded at this point.');
  setText('next-check-evidence','The physical RC report contains a future suggestion, not an executable action. This viewer makes no provider or hardware calls.');
  setText('linearity-evidence','No amplitude-scaling diagnostic belongs to this physical RC run.');
  setText('comparison-provenance',JSON.stringify({source_sha256:state.record.source_sha256,
    plan_event:focus?.plan?.sequence,observation_event:focus?.observation?.sequence,comparison_event:focus?.comparison?.sequence,
    curves:'Exact recorded predictions; no fitting or curve reconstruction by the viewer.',
    display:'Separate pre-stimulus HOLD origins subtracted from each voltage channel. Residual differences are unchanged.',
    prediction_scope:'Parameters fixed before acquisition; voltage curves conditional on subsequently measured IN.',
    nominal_model:'Recorded scores are shown alongside R-change and C-change; its curve remains in raw Evidence.'},null,2));
  setText('raw',JSON.stringify(state.events[state.cursor],null,2));
  $('expand-report').disabled=!vm.report;setText('expand-report',!vm.report?'Report not recorded yet':document.querySelector('.evidence-drawer').open?'Hide original report':'Read original report');
  $('cursor').max=state.events.length-1;$('cursor').value=state.cursor;setText('position',(state.cursor+1)+' / '+state.events.length);
  $('previous').disabled=state.cursor<=0;$('next-event').disabled=state.cursor>=state.events.length-1;$('play').disabled=state.events.length<2;
  $('follow').hidden=!live;$('follow').disabled=state.following;
  setText('integrity',(state.record.integrity==='verified_prefix'?'Hash chain checked through the latest received event.':'Source hash chain verified at export.')+' No external attestation. Record '+state.record.run_id+' · SHA-256 '+(state.record.source_sha256||'pending'));
  renderPhysicalProduct(vm);
}
function selectPhysicalStage(sequence){select(sequence,true);}

function physicalProductStory(vm){
  const nominal=vm.training?.payload.point_models?.nominal_rc||vm.visible.find(e=>e.kind==='tool_result'&&e.payload.result?.nominal_design)?.payload.result.nominal_design;
  const design=nominal?`${nominal.R_ohm/1000} kΩ · ${nominal.C_f*1e6} µF · τ ≈ ${(nominal.R_ohm*nominal.C_f*1000).toFixed(0)} ms`:'Waiting for the recorded design';
  const measured=vm.training?`${(vm.training.payload.tau_s*1000).toFixed(1)} ms`:'Not measured yet';
  const reason=vm.loaded?.selection?.payload.reason||null;
  const translated=reason==='무부하 스텝은 tau=R*C만 식별하여 R 변화와 C 변화를 구분할 수 없으며 반복은 정보가 없으므로, 9.99kohm 부하를 OUT-REF에 연결하면 R 분압으로 정상상태 게인이 달라져 R 변경과 C 변경 대안을 구분할 수 있기 때문. 물리적 재배선은 작업자가 수동으로 수행하며 자동 장착이 아님.';
  const request=vm.visible.find(e=>e.kind==='operator_action_requested')||null;
  const confirmation=vm.visible.find(e=>e.kind==='operator_wiring_confirmation'&&e.payload.fixture==='output_load')||null;
  const complete=Boolean(vm.report?.payload.verdict==='verified'&&vm.verification?.payload.passed);
  let title='Ask the circuit a better question.',explanation='Spark begins by choosing a measurement from the available tools.';
  if(vm.training){title='One trace. Two explanations.';explanation=`The measured time constant is ${(vm.training.payload.tau_s*1000).toFixed(2)} ms. That alone cannot tell resistance change from capacitance change.`;}
  if(reason){title='Change the test. Separate the explanations.';explanation=translated?'An unloaded step identifies only R × C. Repeating it adds no information. A 9.99 kΩ output load changes the divider gain, separating resistance change from capacitance change. The operator performs the wiring.':reason;}
  const failed=vm.terminal?.kind==='run_failed'||vm.verification?.payload.passed===false;
  const cModel=vm.training?.payload.point_models?.c_changed;
  const capacitance=!failed&&complete&&vm.report.payload.candidate==='c_changed'&&nominal&&cModel?`Capacitance ≈ ${(cModel.C_f/nominal.C_f).toFixed(1)}× design (assuming R = ${nominal.R_ohm/1000} kΩ).`:null;
  return {reason,translated,request,confirmation,title,explanation,complete,design,measured,capacitance,
    conclusion:failed?'The experiment stopped without a verified conclusion.':complete?'Capacitance change explains both checks.':vm.loaded?.comparison?'One explanation fits. Test it on a new waveform.':'Choose a test that can distinguish the explanations.',
    label:complete?'Checked on an unused waveform':failed?'Conclusion withheld':'The next decision',
    limits:complete?'Within the declared RC alternatives. Repair was not performed in this run.':'Recorded development experiment. The operator handles physical changes.'};
}

function renderPhysicalProduct(vm){
  const product=state.presentation!=='evidence',story=physicalProductStory(vm);
  $('presentation-switch').hidden=false;$('product-story').hidden=!product;
  $('product-problem').hidden=!product;
  setText('product-design',story.design);setText('product-measured',story.measured);
  setText('product-problem-question','R or C changed? The alternatives tested here.');
  document.body.classList.toggle('product-view',product);
  $('product-tab').setAttribute('aria-pressed',String(product));$('evidence-tab').setAttribute('aria-pressed',String(!product));
  setText('product-title',story.title);setText('product-reason',story.explanation);
  setText('product-reason-note',story.reason?(story.translated?'English translation of Spark’s recorded reason':'Original recorded reason')+' · event '+vm.loaded.selection.sequence:'Reading aid from the events available at this point.');
  $('product-original').hidden=!story.reason;setText('product-original-reason',story.reason);
  setText('product-conclusion-label',story.label);setText('product-conclusion-text',story.conclusion);setText('product-limits',story.limits);
  $('product-capacitance').hidden=!story.capacitance;setText('product-capacitance',story.capacitance);
  const loaded=vm.loaded?.comparison?.payload.scores?.c_changed,verified=vm.verification?.payload.scores?.c_changed;
  setText('product-metrics',story.complete&&loaded&&verified?`Output error: ${loaded.RMS_mV.toFixed(2)} mV with the load · ${verified.RMS_mV.toFixed(2)} mV on the new sine. Whole and regional checks passed.`:'');
  if(!product)return;
  setText('scope','A recorded experiment on a real circuit.');
  setText('source',vm.origin==='hardware'?'Physical experiment · development':'Awaiting measurement');
  setText('plot-title',vm.focus?.phase==='reserved_sine'?'Does it predict a new waveform?':vm.focus?.phase==='attach_output_load_step'?'Which explanation survives the load?':'What does the circuit do?');
  setText('comparison-note',vm.scores?'Model parameters were fixed before capture. These curves use the input measured during that capture. Full checks are in Evidence.':vm.focus?.plan&&!vm.focus.observation?'Parameters fixed. The measured-input comparison will appear after acquisition.':vm.training&&vm.focus?.phase==='unloaded_step'?'The first measurement finds the time constant; it cannot separate R from C.':'Follow the recorded measurements in order.');
  setText('mount-title',story.request?'A request to the operator':'The human stays in the loop');
  setText('instruction',story.confirmation?'Recorded action: the operator connected a 9.99 kΩ load between OUT and REF.':story.request?'“Please connect the output load.”':'Spark can request a wiring change when it would add useful information.');
  setText('mount-note',story.request?'Historical request in this replay. No action on the current board is requested.':'The assistant chooses the test. The operator changes the circuit.');
  setText('trail-note','Measure → distinguish → check');
}
