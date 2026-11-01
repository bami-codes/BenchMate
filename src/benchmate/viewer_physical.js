/* Read-only presentation of the recorded physical RC schema. No fitting or I/O. */
const physicalRCLabels={
  physical_measurement_selected:'Measurement selected',operator_action_requested:'Manual wiring requested',
  operator_wiring_confirmation:'Wiring confirmed by operator',physical_acquisition_plan_frozen:'Model parameters frozen',
  physical_observation:'Physical waveform acquired',unloaded_training_completed:'Time constant fitted',
  physical_model_comparison:'Loaded alternatives compared',physical_verification:'Reserved waveform checked',
  mock_rc_observation:'Mock waveform acquired',repair_prediction_frozen:'Repair prediction frozen',
  repair_prediction_publication:'Repair prediction published',repair_operator_confirmation:'Repair reported by operator',
  repair_prediction_comparison:'Repaired response compared',repair_verification_completed:'Repair checked'
};
const isRepairRun=events=>/_d01_repair_/.test(events[0]?.payload.mode||'');
const isPhysicalRC=events=>events[0]?.payload.mode==='live_spark_new_physical_RC_measurements'||isRepairRun(events);
const isRepairPhase=phase=>/^repair_/.test(phase||'');
const physicalModelName=key=>({nominal_rc:'Nominal RC',r_changed:'R change',c_changed:'C change',restored_nominal:'Repaired',unchanged:'Not repaired'})[key]||key;
const physicalPhaseNames={unloaded_step:'training',attach_output_load_step:'discrimination',reserved_sine:'reserved',repair_step:'after repair',repair_reserved_sine:'after repair · reserved'};
function physicalRCView(events,cursor,selection=null){
  const visible=events.slice(0,cursor+1),conditions=[];
  const find=phase=>conditions.findLast(c=>c.phase===phase);
  // Post-repair checks have no model selection event; their plan or observation opens the condition.
  const ensure=(p,event)=>{if(!find(p.phase)&&isRepairPhase(p.phase))conditions.push({id:event.sequence,phase:p.phase,selection:null,settings:p.settings,fixture:p.fixture||'output_load'});return find(p.phase);};
  let training=null,verification=null,report=null,terminal=null,provider=null,load=null;
  let protocol=null,frozen=null,publication=null,repairRequest=null,repairConfirmation=null,repairVerification=null;
  for(const event of visible){
    const p=event.payload;
    if(event.kind==='provider_configuration')provider=p;
    if(event.kind==='repair_run_protocol')protocol=p;
    if(event.kind==='tool_result'&&Number.isFinite(p.result?.load_ohm))load=p.result.load_ohm;
    if(event.kind==='physical_measurement_selected')conditions.push({id:event.sequence,phase:p.phase,selection:event,settings:p.settings,fixture:p.fixture});
    if(event.kind==='physical_acquisition_plan_frozen'&&ensure(p,event))find(p.phase).plan=event;
    if(['physical_observation','mock_rc_observation'].includes(event.kind)&&p.source===(event.kind==='mock_rc_observation'?'mock':'physical')&&p.all_guards_passed===true&&ensure(p,event))find(p.phase).observation=event;
    if(event.kind==='unloaded_training_completed')training=event;
    if(event.kind==='physical_model_comparison'&&find(p.phase))find(p.phase).comparison=event;
    if(event.kind==='physical_verification'){
      verification=event;
      if(find('reserved_sine'))find('reserved_sine').comparison=event;
    }
    if(event.kind==='repair_prediction_frozen')frozen=event;
    if(event.kind==='repair_prediction_publication')publication=event;
    if(event.kind==='operator_action_requested'&&p.action==='restore_nominal_capacitance')repairRequest=event;
    if(event.kind==='repair_operator_confirmation')repairConfirmation=event;
    if(event.kind==='repair_prediction_comparison'){const c=conditions.findLast(c=>isRepairPhase(c.phase)&&c.observation&&!c.comparison);if(c)c.comparison=event;}
    if(event.kind==='repair_verification_completed')repairVerification=event;
    if(event.kind==='agent_report')report=event;
    if(['run_completed','run_failed'].includes(event.kind))terminal=event;
  }
  const focus=conditions.find(c=>c.id===selection)||conditions.at(-1)||null,series=[];
  const scores=focus?.comparison?.payload.scores||focus?.comparison?.payload.conditional||null;
  if(focus?.observation){
    const p=focus.observation.payload,d=p.data,b=p.baseline;
    const x=d.frame_time_s.map((v,i)=>v+d.output_delay_s[i]);
    series.push({key:'observed',x,y:d.output_v.map(v=>v-b.output_v)});
    series.push({key:'drive',x:d.frame_time_s.map((v,i)=>v+d.input_delay_s[i]),y:d.input_v.map(v=>v-b.input_v)});
    const pair=isRepairPhase(focus.phase)?[['baseline','unchanged'],['predicted','restored_nominal']]:[['baseline','r_changed'],['predicted','c_changed']];
    for(const [key,model] of pair){
      const values=scores?.[model]?.prediction?.predicted_output_v;
      if(values?.length===x.length)series.push({key,x,y:values.map(v=>v-b.output_v)});
    }
  }
  const observations=conditions.filter(c=>c.observation);
  const origin=observations.some(c=>c.observation.payload.source==='physical')?'hardware':observations.length?'mock':'unknown';
  const latest=conditions.at(-1),loaded=conditions.find(c=>c.phase==='attach_output_load_step');
  const repaired=conditions.filter(c=>isRepairPhase(c.phase));
  const supported=Object.entries(loaded?.comparison?.payload.scores||{}).filter(([,s])=>s.passed).map(([name])=>name);
  let status='Waiting for Spark to select a measurement';
  if(latest)status=latest.observation?(origin==='mock'?'Mock waveform acquired':'Physical waveform acquired'):latest.plan?'Plan fixed · awaiting measurement':'Measurement selected · awaiting operator/plan';
  if(training&&latest?.phase==='unloaded_step')status=training.payload.training_adequate?'Time constant fitted · R/C unresolved':'Initial response check failed';
  if(loaded?.comparison&&latest?.phase==='attach_output_load_step')status=supported.length===1?'One alternative supported · reserved check pending':'Loaded check remains unresolved';
  if(verification)status=verification.payload.passed?'Reserved check passed · report pending':'Reserved check failed';
  if(frozen)status='Repair prediction frozen · publication pending';
  if(publication)status=publication.payload.remote?'Repair prediction published · awaiting repair':'Repair prediction saved locally · awaiting repair';
  if(repairRequest)status='Repair requested · awaiting operator';
  if(repairConfirmation)status='Repair reported · new boot required';
  if(repaired.some(c=>c.observation))status=origin==='mock'?'Post-repair mock waveform acquired':'Post-repair waveform acquired';
  if(repairVerification)status=repairVerification.payload.passed?'Repair check passed · report pending':'Repair check failed';
  if(report)status=report.payload.verdict==='repair_verified'?'Repair verified within declared RC alternatives':report.payload.verdict==='verified'?'Verified within declared RC alternatives':'Conclusion withheld';
  if(terminal?.kind==='run_failed')status='Session failed';
  return {visible,conditions,focus,series,scores,training,verification,report,terminal,provider,load,
    observations,origin,status,supported,loaded,mode:events[0]?.payload.mode,repair:isRepairRun(events),
    protocol,scripted:protocol?.provider==='scripted',frozen,publication,repairRequest,repairConfirmation,repairVerification,repaired};
}
function physicalRCReading(vm){
  let explanation='Spark can choose from a bounded menu of new physical measurements.';
  if(vm.training)explanation=`The first trace gives a ${(vm.training.payload.tau_s*1000).toFixed(2)} ms time constant. R and C remain indistinguishable without another condition.`;
  if(vm.loaded?.selection&&!vm.loaded.comparison)explanation='Spark chose an output load to separate the R-change and C-change predictions. The operator performs the wiring.';
  if(vm.loaded?.comparison)explanation=vm.supported.length===1?`The added load separates the alternatives. Only ${physicalModelName(vm.supported[0]).toLowerCase()} meets the whole-waveform and every regional check.`:'The loaded measurement does not support a unique declared alternative.';
  if(vm.verification)explanation=vm.verification.payload.passed?'A new, lower-amplitude sine also matches the same frozen model. The reserved output was not used to refit it.':'The frozen model failed the new sine check. The diagnosis remains unconfirmed.';
  if(vm.frozen)explanation='Before the circuit is touched, the repaired and unrepaired models and their forecasts are frozen.';
  if(vm.publication)explanation=vm.publication.payload.remote?`The frozen prediction was pushed to GitHub${vm.publication.payload.commit?' (commit '+vm.publication.payload.commit.slice(0,7)+')':''} before the operator was asked to repair.`:'The frozen prediction was saved locally. A mock rehearsal does not publish remotely.';
  if(vm.repairConfirmation)explanation='The operator reported the repair. The post-repair checks must come from a new boot.';
  if(vm.repairVerification)explanation=vm.repairVerification.payload.passed?'The repaired model matches both post-repair checks and the unrepaired model fails at least one. Post-repair output was not used to refit anything.':'The post-repair checks did not support the frozen repaired model.';
  if(vm.report?.payload.verdict==='verified')explanation=`${physicalModelName(vm.report.payload.candidate)} explains both the loaded step and the reserved sine within the declared RC alternatives.`;
  if(vm.report?.payload.verdict==='repair_verified')explanation='Diagnosis, repair request and post-repair checks agree within the declared RC alternatives.';
  if(vm.terminal?.kind==='run_failed')explanation=vm.origin==='mock'?'The rehearsal stopped. The record retains its earlier events and the failure; no completion is implied.':'The physical run stopped. The record retains its earlier observations and the failure; no completion is implied.';
  const uncertainty=vm.repair?'Known RC alternatives; provisional channel maps and a 9 mV engineering allowance. No absolute calibration, general fault finding or autonomous repair is claimed.':'Known RC alternatives; provisional channel maps and a 9 mV engineering allowance. No absolute calibration, topology discovery, or repair is claimed.';
  return {explanation,uncertainty:vm.origin==='mock'?'Software rehearsal with a mock bench: no physical evidence. '+uncertainty:uncertainty,
    next:vm.report?'The original report records a suggested follow-up. This viewer schedules no experiment.':vm.repairVerification?'Record the repair result and remaining limits.':vm.repairConfirmation?'Measure the repaired circuit on a new boot with the frozen models.':vm.publication?'The operator restores the designed capacitance.':vm.frozen?'Publish the frozen prediction before asking for the repair.':vm.verification?(vm.repair&&vm.verification.payload.passed?'Spark may request one repair: restore the designed capacitance.':'Record the supported conclusion and remaining limits.'):vm.loaded?.comparison?'Check the unchanged models on the reserved sine.':vm.training?'Use an allowed load to distinguish R change from C change.':'Inspect the allowed experiment and select a measurement.'};
}
function renderPhysicalRC(){
  document.body.classList.add('physical-rc');
  const vm=physicalRCView(state.events,state.cursor,state.condition),focus=vm.focus,live=state.record.transport==='live_log';
  const reading=physicalRCReading(vm),observed=focus?.observation?.payload;
  setText('headline','Spark at the workbench');
  setText('session-description',vm.repair?'Diagnose the fault, predict the repair, then check the repaired circuit.':'Choose a discriminating measurement. Test the same model on a new waveform.');
  setText('source',vm.origin==='hardware'?'Physical observations · provisional':vm.origin==='mock'?'Mock bench · software rehearsal':'Source pending');
  setText('transport',state.integrityFailed?'Live log · integrity error':live&&state.connection==='disconnected'?'Live log · disconnected':live?(state.following?'Live log':'Live log · reviewing'):'Replay');
  setText('scope',vm.repair?(vm.origin==='mock'?'Scripted mock repair rehearsal · no physical evidence.':'Recorded physical D01 repair · measured-input conditional response.'):'Recorded physical RC experiment · measured-input conditional response.');
  $('connection-alert').hidden=!state.connectionMessage;setText('connection-alert',state.connectionMessage);
  setText('status',vm.status);
  const failedCheck=vm.verification?.payload.passed===false||vm.repairVerification?.payload.passed===false,passedCheck=vm.repair?vm.repairVerification?.payload.passed===true:vm.verification?.payload.passed===true;
  $('status-dot').style.background=vm.terminal?.kind==='run_failed'||failedCheck?'var(--error)':passedCheck?'var(--success)':'var(--warning)';
  setText('actor',vm.provider?vm.provider.model+' · '+vm.provider.reasoning_effort:vm.scripted?'Scripted controller · no model':'Provider pending');
  const total=vm.terminal?.payload.instrument?.retained_frames;
  setText('count',vm.observations.length+' waveform observations'+(Number.isFinite(total)?' · '+total.toLocaleString('en-US')+' total frames':''));
  setText('duration',elapsed(seconds(state.events[state.cursor]))+' elapsed');
  setText('explanation',reading.explanation);setText('uncertainty',reading.uncertainty);setText('next',reading.next);
  badge($('report-actor'),vm.report&&!vm.scripted?sparkActor(vm.report.sequence):vm.report?{name:'Scripted',kind:'engine'}:{name:'Engine',kind:'engine'});
  $('report-note').hidden=false;setText('report-note','English reading aid · original model report preserved in Evidence.');
  $('next-status').hidden=true;$('proposal-circuit').hidden=true;
  const select=$('condition');select.replaceChildren();
  for(const c of vm.conditions){
    const option=document.createElement('option');option.value=c.id;
    option.textContent=(c.settings.kind==='sine'?c.settings.frequency_hz+' Hz sine':'Step')+' · ±'+c.settings.amplitude_v+' V · '+(c.fixture==='unloaded'?'unloaded':'output load')+' · '+(physicalPhaseNames[c.phase]||c.phase)+(!c.observation?' · pending':'');
    option.selected=c===focus;select.appendChild(option);
  }
  if(!vm.conditions.length){const option=document.createElement('option');option.textContent='Waiting for a selection';select.appendChild(option);}
  select.disabled=vm.conditions.length<2;
  $('linearity-wrap').hidden=true;$('diagnostic-plots').classList.remove('has-linearity');
  renderChart(vm.series,'V',state.presentation==='evidence'?'Time at channel read completion (s)':'Time (s)',focus?.id!==state.lastFocus);state.lastFocus=focus?.id;
  renderResidual(vm.series);
  setText('chart-title','Change from separately measured HOLD origins');
  const repairFocus=isRepairPhase(focus?.phase);
  setText('chart-description',repairFocus?'Observed output after the repair and the recorded repaired/unrepaired conditional predictions. Separate HOLD origins are subtracted for display; residuals are unchanged. These are not absolute-voltage predictions.':'Observed output and recorded R-change/C-change conditional predictions. Separate HOLD origins are subtracted for display; residuals are unchanged. These are not absolute-voltage predictions.');
  setText('plot-title',repairFocus?'Compare the frozen repair predictions':'Compare the frozen alternatives');setText('baseline-label',repairFocus?'Not repaired · frozen':'R change · frozen');setText('prediction-label',repairFocus?'Repaired · frozen':'C change · frozen');setText('drive-label','Measured IN');
  for(const b of document.querySelectorAll('[data-trace]'))b.disabled=!vm.series.some(s=>s.key===b.dataset.trace);
  document.querySelector('[data-trace=predicted]').title='Recorded conditional curve: model parameters fixed before measurement; measured IN supplies the input afterward.';
  setText('plot-source',focus?.phase==='unloaded_step'?'Training observation':focus?.phase==='reserved_sine'?'Reserved verification':repairFocus?(focus.phase==='repair_reserved_sine'?'Post-repair reserved check':'Post-repair check'):'Loaded discrimination');
  let caption='No waveform has been acquired for this selection.';
  if(focus?.plan&&!observed)caption='Model parameters are fixed. Conditional curves require the new measured IN; no future waveform is shown.';
  if(observed)caption='Changes from separate HOLD origins; no absolute-voltage claim. Model curves appear only when recorded comparisons arrive.';
  if(vm.scores)caption=repairFocus?'Changes from separate HOLD origins. Repair models frozen and published before the repair; curves use measured IN. Scores: whole / worst-region RMS; both must meet 9 mV.':'Changes from separate HOLD origins. Models fixed before capture; curves use measured IN. Scores: whole / worst-region RMS; both must meet 9 mV.';
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
  const rows=vm.repair?[['Measure tau',vm.training,'Tau fitted'],['Choose a load',vm.loaded?.selection,'Load selected'],['Check the diagnosis',vm.verification,vm.verification?.payload.passed?'Diagnosis checked':'Diagnosis check failed'],['Lock the repair prediction',vm.publication,vm.publication?.payload.remote?'Prediction published':'Prediction saved'],['Check the repair',vm.repairVerification,vm.repairVerification?.payload.passed?'Repair verified':'Repair check failed']]
    :[['Measure tau',vm.training,'Tau fitted'],['Choose a load',vm.loaded?.selection,'Load selected'],['Freeze reserved models',vm.conditions.find(c=>c.phase==='reserved_sine')?.plan,'Models fixed'],['Check a new waveform',vm.verification,vm.verification?.payload.passed?'Reserved check passed':'Reserved check failed']];
  stages.style.gridTemplateColumns=`repeat(${rows.length},minmax(0,1fr))`;
  const current=rows.findLastIndex(r=>r[1]);
  rows.forEach(([pending,event,done],i)=>{const b=document.createElement('button');b.className='story-stage'+(event?' reached':'')+(i===current?' current':'');b.textContent=event?done:pending;b.disabled=!event;b.dataset.stage=i;if(i===current)b.setAttribute('aria-current','step');b.onclick=()=>selectPhysicalStage(event.sequence);stages.appendChild(b);});
  renderTimeline(vm);
  setText('evidence-note','Recorded model parameters, comparisons and acquisition origins.');
  setText('evidence',JSON.stringify({selected_action:focus?.selection?.payload,plan:focus?.plan?.payload,
    repair_prediction:vm.frozen?{event:vm.frozen.sequence,sha256:vm.frozen.payload.sha256,action:vm.frozen.payload.action,reason:vm.frozen.payload.reason,publication:vm.publication?.payload||null}:undefined,
    observation_origin:observed?{source:observed.source,boot_id:observed.boot_id,baseline:observed.baseline,all_guards_passed:observed.all_guards_passed}:null,
    checks:vm.scores?Object.fromEntries(Object.entries(vm.scores).map(([k,v])=>[k,Object.fromEntries(Object.entries(v).filter(([name])=>name!=='prediction'))])):null},null,2));
  setText('original-report',vm.report?JSON.stringify(vm.report.payload,null,2):'No report recorded at this point.');
  setText('next-check-evidence',vm.repair?'The repair report contains a future suggestion, not an executable action. This viewer makes no provider or hardware calls.':'The physical RC report contains a future suggestion, not an executable action. This viewer makes no provider or hardware calls.');
  setText('linearity-evidence','No amplitude-scaling diagnostic belongs to this physical RC run.');
  setText('comparison-provenance',JSON.stringify({source_sha256:state.record.source_sha256,
    plan_event:focus?.plan?.sequence,observation_event:focus?.observation?.sequence,comparison_event:focus?.comparison?.sequence,
    curves:'Exact recorded predictions; no fitting or curve reconstruction by the viewer.',
    display:'Separate pre-stimulus HOLD origins subtracted from each voltage channel. Residual differences are unchanged.',
    prediction_scope:repairFocus?'Repaired/unrepaired parameters and command-input forecasts frozen and published before the repair request; voltage curves conditional on subsequently measured IN.':'Parameters fixed before acquisition; voltage curves conditional on subsequently measured IN.',
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

function physicalProductStory(vm,translations={}){
  const nominal=vm.training?.payload.point_models?.nominal_rc||vm.visible.find(e=>e.kind==='tool_result'&&e.payload.result?.nominal_design)?.payload.result.nominal_design;
  const design=nominal?`${nominal.R_ohm/1000} kΩ · ${nominal.C_f*1e6} µF · τ ≈ ${(nominal.R_ohm*nominal.C_f*1000).toFixed(0)} ms`:'Waiting for the recorded design';
  const measured=vm.training?`${(vm.training.payload.tau_s*1000).toFixed(1)} ms`:'Not measured yet';
  const reason=vm.loaded?.selection?.payload.reason||null;
  // Reading aids: one reviewed historical string, or a hash-checked translations.json sidecar entry.
  const known=reason==='무부하 스텝은 tau=R*C만 식별하여 R 변화와 C 변화를 구분할 수 없으며 반복은 정보가 없으므로, 9.99kohm 부하를 OUT-REF에 연결하면 R 분압으로 정상상태 게인이 달라져 R 변경과 C 변경 대안을 구분할 수 있기 때문. 물리적 재배선은 작업자가 수동으로 수행하며 자동 장착이 아님.'?'An unloaded step identifies only R × C. Repeating it adds no information. A 9.99 kΩ output load changes the divider gain, separating resistance change from capacitance change. The operator performs the wiring.':null;
  const english=reason?(translations[String(vm.loaded.selection.sequence)]||known):null,translated=Boolean(english);
  const request=vm.visible.find(e=>e.kind==='operator_action_requested')||null;
  const confirmation=vm.visible.find(e=>e.kind==='operator_wiring_confirmation'&&e.payload.fixture==='output_load')||null;
  const complete=Boolean(vm.report?.payload.verdict==='verified'&&vm.verification?.payload.passed);
  const diagnosed=Boolean(vm.verification?.payload.passed&&vm.supported.length===1&&vm.supported[0]==='c_changed');
  let title='Ask the circuit a better question.',explanation='Spark begins by choosing a measurement from the available tools.',reasonEvent=null;
  if(vm.training){title='One trace. Two explanations.';explanation=`The measured time constant is ${(vm.training.payload.tau_s*1000).toFixed(2)} ms. That alone cannot tell resistance change from capacitance change.`;}
  if(reason){title='Change the test. Separate the explanations.';explanation=english||reason;reasonEvent=vm.loaded.selection.sequence;}
  const failed=vm.terminal?.kind==='run_failed'||vm.verification?.payload.passed===false||vm.repairVerification?.payload.passed===false;
  const cModel=vm.training?.payload.point_models?.c_changed;
  const ratio=nominal&&cModel?`${(cModel.C_f/nominal.C_f).toFixed(1)}× design (assuming R = ${nominal.R_ohm/1000} kΩ)`:null;
  const capacitance=!failed&&complete&&vm.report.payload.candidate==='c_changed'&&ratio?`Capacitance ≈ ${ratio}.`:null;
  const story={reason,translated,request,confirmation,title,explanation,complete,design,measured,capacitance,reasonEvent,reasonOriginal:reason,reasonTranslated:translated,
    conclusion:failed?'The experiment stopped without a verified conclusion.':complete?'Capacitance change explains both checks.':vm.loaded?.comparison?'One explanation fits. Test it on a new waveform.':'Choose a test that can distinguish the explanations.',
    label:complete?'Checked on an unused waveform':failed?'Conclusion withheld':'The next decision',
    limits:complete?'Within the declared RC alternatives. Repair was not performed in this run.':'Recorded development experiment. The operator handles physical changes.',
    metrics:null,forecast:null,lock:null,repairRequest:null,repairConfirmation:null};
  const loadedScore=vm.loaded?.comparison?.payload.scores?.c_changed,verifiedScore=vm.verification?.payload.scores?.c_changed;
  if(complete&&loadedScore&&verifiedScore)story.metrics=`Output error: ${loadedScore.RMS_mV.toFixed(2)} mV with the load · ${verifiedScore.RMS_mV.toFixed(2)} mV on the new sine. Whole and regional checks passed.`;
  if(!vm.repair)return story;
  // Repair runs: diagnosis → request → published prediction → operator repair → post-repair checks.
  story.repairRequest=vm.repairRequest;story.repairConfirmation=vm.repairConfirmation;
  if(diagnosed&&!vm.frozen){
    story.title='Capacitance changed. Now repair it.';
    story.explanation='The diagnosis passed a reserved waveform. Spark may ask for one repair: restore the designed capacitance.';
    story.label='Diagnosis checked on an unused waveform';story.conclusion='Capacitance change explains both diagnostic checks.';
  }
  if(diagnosed&&ratio)story.capacitance=`Diagnosis: capacitance ≈ ${ratio}.`;
  if(vm.frozen){
    const repairReason=vm.frozen.payload.reason||null,repairEnglish=repairReason?translations[String(vm.frozen.sequence)]||null:null;
    story.title='Predict the repair before making it.';
    story.explanation=repairEnglish||repairReason||'Spark requested the designed capacitance be restored.';
    story.reasonEvent=vm.frozen.sequence;story.reasonOriginal=repairReason;story.reasonTranslated=Boolean(repairEnglish);
    story.label='Repair prediction frozen';story.conclusion='Repaired and unrepaired models are fixed before anyone touches the circuit.';
    story.lock={sha256:vm.frozen.payload.sha256,published:Boolean(vm.publication?.payload.published),remote:Boolean(vm.publication?.payload.remote),
      commit:vm.publication?.payload.commit||null,url:vm.publication?.payload.url||null};
  }
  if(vm.repairConfirmation){story.label='Repair reported by the operator';story.conclusion='Measure the repaired circuit on a new boot. No refitting.';}
  const checks=vm.repaired.filter(c=>c.comparison).map(c=>({phase:c.phase,settings:c.settings,scores:c.comparison.payload.conditional}));
  if(vm.repairVerification){
    const passed=vm.repairVerification.payload.passed;
    story.title=passed?(vm.scripted?'The repair matched the frozen prediction.':'The repair did what Spark predicted.'):'The repair did not match the prediction.';
    story.label=passed?'Checked after the repair':'Repair check failed';
    story.conclusion=passed?'Only the repaired model fits the new measurements.':'The post-repair measurements did not support the frozen repaired model.';
    story.complete=passed;
  }
  if(checks.length){
    const fmt=key=>checks.map(c=>{const s=c.scores?.[key];return `${s?.RMS_mV?.toFixed(2)??'—'} mV ${c.settings.kind==='sine'?c.settings.frequency_hz+' Hz sine':'step'}${s?(s.passed?' ✓':' ✗'):''}`;}).join(' · ');
    story.metrics=`Repaired model: ${fmt('restored_nominal')}. Not repaired: ${fmt('unchanged')}. Measured-input comparison; whole and every region within 9 mV.`;
    const forecasts=vm.repaired.filter(c=>c.comparison).map(c=>c.comparison.payload.command_forecast?.restored_nominal).filter(Boolean);
    if(forecasts.length)story.forecast=`Forecast published before the repair (commanded input): ${forecasts.map(f=>f.RMS_mV.toFixed(2)+' mV'+(f.passed?' ✓':' ✗')).join(' · ')}.`+(vm.repairVerification&&vm.repairVerification.payload.passed&&vm.repairVerification.payload.command_forecasts_pass===false?' The measured-input check passed but the earlier forecast missed; both results are kept.':'');
  }
  story.limits=vm.origin==='mock'?(vm.scripted?'Software rehearsal with a mock bench and scripted decisions. Not a physical repair.':'Software rehearsal with a mock bench and recorded Spark decisions. Not a physical repair.'):story.lock?.remote?'Within the declared RC alternatives. The prediction was public before the repair.':'Within the declared RC alternatives. The operator performs the repair.';
  if(failed)story.limits='The record keeps the failure. No repair success is implied.';
  return story;
}

function renderPhysicalProduct(vm){
  const product=state.presentation!=='evidence',story=physicalProductStory(vm,state.record.translations||{});
  $('presentation-switch').hidden=false;$('product-story').hidden=!product;
  $('product-problem').hidden=!product;
  setText('product-design',story.design);setText('product-measured',story.measured);
  setText('product-problem-question',vm.repair?'R or C changed? Then: can the repair be predicted?':'R or C changed? The alternatives tested here.');
  document.body.classList.toggle('product-view',product);
  $('product-tab').setAttribute('aria-pressed',String(product));$('evidence-tab').setAttribute('aria-pressed',String(!product));
  const actor=$('product-actor');if(actor){actor.textContent=vm.scripted?'Scripted decision':'Spark’s decision';actor.className='actor-badge '+(vm.scripted?'engine':'spark');}
  setText('product-title',story.title);setText('product-reason',story.explanation);
  const who=vm.scripted?'scripted':'Spark’s recorded';
  setText('product-reason-note',story.reasonOriginal?(story.reasonTranslated?`English translation of ${who} reason`:`Original ${who} reason`)+' · event '+story.reasonEvent:'Reading aid from the events available at this point.');
  $('product-original').hidden=!(story.reasonOriginal&&story.reasonTranslated);setText('product-original-reason',story.reasonOriginal);
  setText('product-conclusion-label',story.label);setText('product-conclusion-text',story.conclusion);setText('product-limits',story.limits);
  $('product-capacitance').hidden=!story.capacitance;setText('product-capacitance',story.capacitance);
  setText('product-metrics',[story.metrics,story.forecast].filter(Boolean).join(' '));
  const lock=$('product-lock');
  if(lock){
    lock.replaceChildren();lock.hidden=!story.lock;
    if(story.lock){
      const head=document.createElement('strong');head.textContent=story.lock.remote?'Prediction published before the repair':'Prediction frozen before the repair';
      const hash=document.createElement('span');hash.className='mono';hash.textContent=' · SHA-256 '+story.lock.sha256.slice(0,12);
      lock.append(head,hash);
      if(story.lock.commit){
        const link=document.createElement('a');link.href=story.lock.url||('https://github.com/bami-codes/BenchMate/commit/'+story.lock.commit);
        link.textContent=' · commit '+story.lock.commit.slice(0,7);link.target='_blank';link.rel='noopener';lock.appendChild(link);
      }else if(!story.lock.remote){const note=document.createElement('span');note.textContent=' · local only';lock.appendChild(note);}
    }
  }
  if(!product)return;
  setText('scope',vm.origin==='mock'?'A software rehearsal. No real circuit was measured.':'A recorded experiment on a real circuit.');
  setText('source',vm.origin==='hardware'?'Physical experiment · development':vm.origin==='mock'?'Mock bench · rehearsal':'Awaiting measurement');
  const phase=vm.focus?.phase;
  setText('plot-title',phase==='repair_step'?'Did the repair do what was predicted?':phase==='repair_reserved_sine'?'Does the repaired model predict a new waveform?':phase==='reserved_sine'?'Does it predict a new waveform?':phase==='attach_output_load_step'?'Which explanation survives the load?':'What does the circuit do?');
  setText('comparison-note',vm.scores?(isRepairPhase(phase)?`Repair models were ${story.lock?.remote?'frozen and published':'frozen'} before the repair. These curves use the input measured afterward. Full checks are in Evidence.`:'Model parameters were fixed before capture. These curves use the input measured during that capture. Full checks are in Evidence.'):vm.focus?.plan&&!vm.focus.observation?'Parameters fixed. The measured-input comparison will appear after acquisition.':vm.training&&phase==='unloaded_step'?'The first measurement finds the time constant; it cannot separate R from C.':'Follow the recorded measurements in order.');
  const simulated=vm.origin==='mock';
  badge($('mount-actor'),{name:simulated?'Operator · simulated':'Operator',kind:'operator'});
  if(vm.repair&&story.repairRequest){
    setText('mount-title','A repair request to the operator');
    setText('instruction',story.repairConfirmation?(simulated?'Simulated action: the added capacitor was removed in the mock bench.':'Recorded action: the operator removed the added capacitor, leaving the designed one.'):'“Restore the designed capacitance.”');
    setText('mount-note',story.repairConfirmation?'The board restarts before the repaired circuit is measured.':'Asked only after the prediction was frozen. Spark does not see which part or hole this is.');
  }else{
    setText('mount-title',story.request?'A request to the operator':'The human stays in the loop');
    setText('instruction',story.confirmation?'Recorded action: the operator connected a 9.99 kΩ load between OUT and REF.':story.request?(simulated?'Simulated request: connect the output load.':'“Please connect the output load.”'):'Spark can request a wiring change when it would add useful information.');
    setText('mount-note',story.request?'Historical request in this replay. No action on the current board is requested.':'The assistant chooses the test. The operator changes the circuit.');
  }
  setText('trail-note',vm.repair?'Measure → distinguish → repair → check':'Measure → distinguish → check');
}

function repairActor(event){
  if(!isRepairRun(state.events))return null;
  const scripted=state.events.find(e=>e.kind==='repair_run_protocol')?.payload.provider==='scripted';
  if(scripted&&['tool_call','agent_report','physical_measurement_selected'].includes(event.kind))return {name:'Scripted',kind:'engine',title:'Scripted controller in a software rehearsal; no model call'};
  if(event.kind==='mock_rc_observation')return {name:'Mock bench',kind:'engine'};
  if(['operator_action_requested','repair_operator_confirmation'].includes(event.kind))return {name:event.payload.simulated||event.payload.source==='mock'?'Operator · simulated':'Operator',kind:'operator'};
  if(['repair_prediction_frozen','repair_prediction_publication','repair_prediction_comparison','repair_verification_completed'].includes(event.kind))return {name:'Engine',kind:'engine'};
  return null;
}
