'use strict';
const $ = id => document.getElementById(id);
const token = document.querySelector('meta[name="benchmate-session"]').content;
const nodes = ['IN', 'OUT', 'REF', 'N1', 'N2', 'UNKNOWN'];
let current = null, library = [], busy = false, snapshot = null, plotId = null, playing = false, timer = null;
const el = (tag, text, cls) => { const n=document.createElement(tag); if(text!==undefined)n.textContent=text; if(cls)n.className=cls; return n; };
function button(text, handler, cls='text-button') { const n=el('button',text,cls);n.type='button';n.addEventListener('click',handler);return n; }
function notice(message) { $('notice').textContent=message; $('notice').hidden=!message; }
async function request(path, body) {
  const controller=new AbortController(), timeout=setTimeout(()=>controller.abort(),12000);
  try {
    const response=await fetch(path,{signal:controller.signal,...(body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json','X-BenchMate-Session':token},body:JSON.stringify(body)})});
    const result=await response.json(); if(!response.ok)throw new Error(result.error||'The local request could not be completed.');return result;
  } catch(error) { if(error.name==='AbortError')throw new Error('The request timed out. Reload the saved case before retrying; no automatic retry was made.');throw error; }
  finally {clearTimeout(timeout);}
}
function locks() {
  document.querySelectorAll('button').forEach(n=>n.disabled=busy||n.dataset.permanent==='true');
  $('review-fields').disabled=busy||!!current?.manifest.experiment_link;
  $('case-picker').disabled=busy; $('cursor').disabled=busy;
  $('back').disabled=busy||!snapshot||snapshot.cursor===0;
  $('next').disabled=busy||!snapshot||snapshot.cursor===snapshot.last_sequence;
  $('play').disabled=busy||!snapshot;
  $('play').textContent=playing?'Pause replay':'Play replay';
}
async function action(fn) {
  if(busy)return false;
  busy=true;notice('');document.body.setAttribute('aria-busy','true');locks();
  try {await fn();return true;} catch(error){pause();notice(error.message);return false;}
  finally {busy=false;document.body.removeAttribute('aria-busy');locks();}
}
function picklist() {
  $('case-picker').replaceChildren(new Option('Start a question',''));
  library.forEach(item=>$('case-picker').add(new Option(item.question.slice(0,65),item.case_id)));
  $('case-picker').value=current?.manifest.case_id||'';
}
async function refreshLibrary(){library=(await request('/api/state')).cases;picklist();}
function field(labelText,input){const label=el('label',labelText);label.append(input);return label;}
function components(candidate){
  $('components').replaceChildren();
  candidate.components.forEach((item,index)=>{
    const box=el('div',undefined,'component'),grid=el('div',undefined,'component-grid');
    const value=el('input');Object.assign(value,{id:`value-${index}`,type:'number',step:'any',min:'0',placeholder:'Unknown'});
    const scale=item.kind==='R'?1000:item.kind==='C'?1e-6:1;
    value.value=item.value_si===null?'':Number((item.value_si/scale).toPrecision(12));
    grid.append(field(item.kind==='R'?'Value (kΩ)':item.kind==='C'?'Value (µF)':'Value',value));
    for(const key of ['a','b']){const input=el('select');input.id=`${key}-${index}`;nodes.forEach(n=>input.add(new Option(n,n)));input.value=item[key];grid.append(field(key==='a'?'From':'To',input));}
    box.append(el('p',item.name+' · '+(item.kind==='R'?'Resistor':item.kind==='C'?'Capacitor':'Diode'),'component-title'),grid);$('components').append(box);
  });
}
function candidateFromForm(){
  const candidate=structuredClone(current.manifest.intended_design.draft_candidate);
  candidate.components.forEach((item,index)=>{
    const raw=$(`value-${index}`).value;item.value_si=raw===''?null:Number(raw)*(item.kind==='R'?1000:item.kind==='C'?1e-6:1);
    item.a=$(`a-${index}`).value;item.b=$(`b-${index}`).value;
    if(item.value_si!==null&&(!Number.isFinite(item.value_si)||item.value_si<=0))throw new Error('Use a positive value, or leave it blank if unknown.');
  });
  const unknown=candidate.components.some(x=>x.value_si===null||[x.a,x.b].includes('UNKNOWN'));
  candidate.status=unknown?'incomplete':'needs_review';candidate.ambiguities=unknown?['Operator left a value or connection unresolved.']:[];
  return candidate;
}
function provenance(result){
  const m=result.manifest,d=m.intended_design;
  $('provenance').replaceChildren();
  const entries={'Question':'Current local entry; not sent to Spark or used in the archived experiment.',
    'Schematic reading':'Oct 31 · synthetic schematic · recorded Muse Spark output',
    'Physical experiment':m.experiment_link?'Oct 30 · protocol supplied the nominal design · matching design only':'Not linked',
    'English text':'Translated or summarized for this screen. Original Korean text is available per event.',
    'Physical record SHA-256':m.experiment_link?.record_sha256||'Not linked',
    'Vision record SHA-256':d.vision_record_sha256,'Case revision':`${m.revision} · ${result.manifest_sha256}`};
  for(const [key,value]of Object.entries(entries))$('provenance').append(el('dt',key),el('dd',value));
  $('manifest').textContent=JSON.stringify(result,null,2);$('export').href=`/api/cases/${m.case_id}/export`;
  $('original-viewer').hidden=!m.experiment_link;$('original-viewer').href=`/api/cases/${m.case_id}/replay`;
}
async function renderCase(result,cursor=0){
  pause();current=result;snapshot=null;plotId=null;
  const m=result.manifest,linked=!!m.experiment_link;
  $('question-panel').hidden=true;$('case-panel').hidden=false;
  $('saved-question').textContent=m.question.text;
  $('scope-note').textContent=m.scope==='recorded_walkthrough'?'Exploring the recorded D01 example.':'A different circuit needs its own measurements. This record cannot diagnose it.';
  components(m.intended_design.draft_candidate);
  $('gate').textContent=linked?'You confirmed this design. The matching record is ready.':m.revision===1?'Check the values and connections, then confirm this design.':result.replay_eligibility.message;
  $('confirm-design').textContent=linked?'Design confirmed':'Confirm design & explore record';
  $('record-panel').hidden=!linked;
  $('design-origin').textContent='Read from this schematic by Muse Spark on Oct 31. The Oct 30 run was given the same design, 10 kΩ and 1 µF, in its protocol.';
  if(!result.replay_eligibility.allowed&&m.revision>1)$('design-origin').textContent+=' Your current review differs or remains unresolved; the replay is blocked.';
  provenance(result);picklist();clearEvidence();
  history.replaceState(null,'',`?case=${m.case_id}`);
  if(linked)await loadCursor(cursor);
  locks();
}
function clearEvidence(){
  $('messages').replaceChildren();$('answer').hidden=true;$('followups').hidden=true;
  $('event-list').replaceChildren();$('event-original').hidden=true;
  $('hypotheses').replaceChildren();['Design unchanged','A · Resistance changed','B · Capacitance changed'].forEach(label=>{
    const row=el('li');row.append(el('span',label),el('span','○ Unresolved','state'));$('hypotheses').append(row);
  });
  $('chart').replaceChildren(el('p','Step through the recorded run. Measurements and comparisons appear as they become available.','empty'));
  $('plot-title').textContent='Waiting for a measurement';$('plot-select').hidden=true;$('legend').hidden=true;$('plot-caption').textContent='';$('score-links').replaceChildren();$('plot-details').hidden=true;
}
function pause(){playing=false;if(timer)clearTimeout(timer);timer=null;$('play').textContent='Play replay';}
async function loadCursor(cursor,scroll=false){
  snapshot=await request(`/api/cases/${current.manifest.case_id}/timeline?cursor=${cursor}`);
  plotId=snapshot.plots.at(-1)?.id||null;renderSnapshot();
  history.replaceState(null,'',`?case=${current.manifest.case_id}&event=${snapshot.cursor}`);
  if(scroll){const target=snapshot.answer?$('answer'):$('messages').lastElementChild;target?.scrollIntoView({block:'start',behavior:'auto'});}
}
function sourceButtons(refs,plot){
  const box=el('div',undefined,'source-buttons');
  if(plot)box.append(button('Open waveform ↗',()=>openPlot(plot)));
  refs.forEach(seq=>box.append(button(`Event ${seq}`,()=>action(()=>showEvent(seq)))));return box;
}
function originalDetails(original){const d=el('details');d.append(el('summary','Read original'),el('pre',typeof original==='string'?original:JSON.stringify(original,null,2)));return d;}
function modelCards(models,frozen=false){
  const box=el('div',undefined,'model-cards');
  for(const [key,title]of [['r_changed','A · Resistance changed'],['c_changed','B · Capacitance changed']]){
    const m=models[key],card=el('div',undefined,'model-card');card.append(el('h3',title));
    if(frozen)card.append(el('p',`Gain ${m.gain.toFixed(3)} · τ ${(m.tau_s*1000).toFixed(2)} ms`),el('p','Fixed before loaded capture','subtle'));
    else card.append(el('p',`R ${(m.R_ohm/1000).toFixed(2)} kΩ · C ${(m.C_f*1e6).toFixed(2)} µF`));
    box.append(card);
  }return box;
}
function messageView(m){
  const section=el('section',undefined,'message'+(m.emphasis?' choice':''));section.id=m.id;
  const actor=el('p',m.actor,'actor');actor.append(el('span',m.source==='screen_translation'?'Recorded Oct 30 · Translated for this screen':m.actor==='Operator'?'Recorded Oct 30':'Summary of the recorded run'));
  section.append(actor);
  const heading=el('h2');heading.append(m.emphasis?el('span',m.title,'tape'):document.createTextNode(m.title));section.append(heading);
  const body=el(m.source==='screen_translation'?'blockquote':'p',m.text);
  if(m.request){
    const request=el('div',undefined,'request');request.append(body,el('p',m.operator_confirmed?'✓ Operator completion recorded':'○ Waiting for the recorded operator confirmation','completion'),el('p','Historical instruction — no wiring action is requested now.','subtle'));section.append(request);
  }else section.append(body);
  const metrics=el('div',undefined,'metric-links');
  if(m.metrics?.tau_ms!==undefined)metrics.append(button(`${m.metrics.tau_ms.toFixed(1)} ms · measured τ ↗`,()=>openPlot(m.plot),'metric-button'));
  if([94,133].includes(m.sequence)){
    const recordedPlot=snapshot.plots.find(p=>p.id===m.plot);
    for(const key of (m.sequence===94?['r_changed','c_changed']:['c_changed'])){
      const score=recordedPlot.scores[key],label=key==='r_changed'?'A':'B';
      metrics.append(button(`${label} · ${score.RMS_mV.toFixed(m.sequence===94?1:2)} mV RMS ↗`,()=>openPlot(m.plot),'metric-button'));
    }
  }
  if(metrics.children.length)section.append(metrics);
  if(m.models)section.append(modelCards(m.models));if(m.frozen_models)section.append(modelCards(m.frozen_models,true));
  if(m.original)section.append(originalDetails(m.original));section.append(sourceButtons(m.refs,m.plot));return section;
}
function renderSnapshot(){
  const s=snapshot;$('cursor').value=s.cursor;$('position').textContent=`Event ${s.cursor} / ${s.last_sequence}`;
  $('messages').replaceChildren(...s.messages.map(messageView));
  $('step-status').textContent=s.messages.at(-1)?.title||'Replay at the beginning. No measurement yet.';
  $('hypotheses').replaceChildren(...s.hypotheses.map(h=>{const row=el('li',undefined,h.status);const status={unresolved:'○ Unresolved',supported:'● Supported',rejected:'× Rejected'}[h.status];row.append(el('span',h.label),el('span',status,'state'));return row;}));
  $('answer').hidden=!s.answer;$('followups').hidden=!s.answer;$('followup-answer').hidden=true;
  if(s.answer){
    const a=s.answer,heading=el('h2');heading.append(el('span',a.title,'tape'));
    const dl=el('dl');for(const [label,text]of [['Measured',a.observed],['Assumed',a.assumption],['Still unknown',a.unknown]])dl.append(el('dt',label),el('dd',text));
    const repair=button('Restore the design and re-test',()=>{},'');repair.disabled=true;repair.dataset.permanent='true';
    $('answer').replaceChildren(el('p','BenchMate · Answer from this run','actor'),heading,dl,sourceButtons(a.refs),originalDetails(a.original),repair,el('p','Needs the live bench. This replay has no repair.','subtle repair-note'));
    $('followup-buttons').replaceChildren(...s.followups.map(f=>button(f.question,()=>{
      $('followup-answer').hidden=false;$('followup-answer').replaceChildren(el('p','Answered from this run’s record · Prepared question','subtle'),el('h3',f.question),el('p',f.text),sourceButtons(f.refs,f.plot));
      if(f.plot)openPlot(f.plot,false);
    },'')));
  }
  $('event-list').replaceChildren(el('p','Sources available at this replay position','subtle'));
  const list=el('div',undefined,'event-buttons');s.evidence.forEach(e=>list.append(button(`${e.sequence} · ${e.kind.replaceAll('_',' ')}`,()=>action(()=>showEvent(e.sequence)))));$('event-list').append(list);
  $('event-original').hidden=true;$('event-original').textContent='';
  $('plot-select').replaceChildren(...s.plots.map(p=>new Option(p.title,p.id)));$('plot-select').hidden=!s.plots.length;
  renderPlot();locks();
}
async function showEvent(sequence){
  const event=await request(`/api/cases/${current.manifest.case_id}/event?cursor=${snapshot.cursor}&sequence=${sequence}`);
  $('evidence').open=true;$('event-original').hidden=false;$('event-original').textContent=JSON.stringify(event,null,2);$('event-original').scrollIntoView({block:'center'});$('event-original').focus({preventScroll:true});
}
function openPlot(id,scroll=true){plotId=id;renderPlot();if(scroll){$('bench-panel').scrollIntoView({block:'start',behavior:'auto'});$('plot-select').focus({preventScroll:true});}}
const svgNS='http://www.w3.org/2000/svg';
function svg(tag,attrs,text){const n=document.createElementNS(svgNS,tag);Object.entries(attrs).forEach(([k,v])=>n.setAttribute(k,String(v)));if(text!==undefined)n.textContent=text;return n;}
function chart(p){
  const w=520,h=320,pad={l:59,r:18,t:27,b:44},root=svg('svg',{viewBox:`0 0 ${w} ${h}`,role:'img','aria-labelledby':'wave-title wave-desc'});
  root.append(svg('title',{id:'wave-title'},p.title),svg('desc',{id:'wave-desc'},'All 512 recorded samples. Output change relative to a separate HOLD baseline. The model curves, when available, use the measured input. Exact RMS and regional results are below.'));
  const curves=Object.entries(p.predictions).filter(([k])=>k!=='nominal_rc');
  const values=[...p.observed_v,...curves.flatMap(([,a])=>a)];let lo=Math.min(...values),hi=Math.max(...values),dy=Math.max(hi-lo,.01);lo-=dy*.12;hi+=dy*.12;
  const t0=p.time_s[0],t1=p.time_s.at(-1),x=t=>pad.l+(t-t0)/(t1-t0)*(w-pad.l-pad.r),y=v=>h-pad.b-(v-lo)/(hi-lo)*(h-pad.t-pad.b);
  for(let i=0;i<=4;i++){
    const v=lo+(hi-lo)*i/4,ty=y(v),t=t0+(t1-t0)*i/4,tx=x(t);
    root.append(svg('line',{x1:pad.l,y1:ty,x2:w-pad.r,y2:ty,stroke:'#e2e5df'}),svg('text',{x:pad.l-8,y:ty+4,'text-anchor':'end',fill:'#59615b','font-size':11},v.toFixed(2)),svg('text',{x:tx,y:h-22,'text-anchor':'middle',fill:'#59615b','font-size':11},t.toFixed(2)));
  }
  root.append(svg('text',{x:pad.l,y:16,fill:'#59615b','font-size':11},'ΔOUT (V)'),svg('text',{x:w-pad.r,y:h-5,'text-anchor':'end',fill:'#59615b','font-size':11},'Time (s)'));
  function trace(array,color,dash){const path=array.map((v,i)=>`${i?'L':'M'}${x(p.time_s[i]).toFixed(2)} ${y(v).toFixed(2)}`).join(' ');root.append(svg('path',{d:path,fill:'none',stroke:color,'stroke-width':2,'stroke-dasharray':dash,'vector-effect':'non-scaling-stroke'}));}
  trace(p.observed_v,'#b8332e','');for(const [key,array]of curves)trace(array,key==='r_changed'?'#747b77':'#245bcc',key==='r_changed'?'2 5':'7 5');return root;
}
function renderPlot(){
  const p=snapshot?.plots.find(p=>p.id===plotId);
  $('legend').hidden=!p;$('plot-details').hidden=!p;
  if(!p){$('plot-title').textContent='Waiting for a measurement';$('chart').replaceChildren(el('p','No waveform has arrived at this point in the record.','empty'));$('plot-caption').textContent='';$('score-links').replaceChildren();return;}
  $('plot-select').value=p.id;$('plot-title').textContent=p.title;$('chart').replaceChildren(chart(p));
  const conditional=Object.keys(p.predictions).length>0;
  $('legend').querySelectorAll('.r-model,.c-model').forEach(n=>n.hidden=!conditional);
  $('plot-caption').textContent=conditional?'Models fixed before capture; curves conditioned on measured IN. 512 recorded samples; independent HOLD origins. Overall and regional RMS must pass.':'512 recorded samples; OUT relative to its separate HOLD baseline. No prediction curve is reconstructed here.';
  $('score-links').replaceChildren();
  for(const [key,label]of [['nominal_rc','Design'],['r_changed','A'],['c_changed','B']])if(p.scores[key]){
    const score=p.scores[key];$('score-links').append(button(`${label}: ${score.RMS_mV.toFixed(2)} mV RMS · ${score.passed?'pass':'fail'}`,()=>{$('plot-details').open=true;$('plot-details').scrollIntoView({block:'nearest'});}));
  }
  $('plot-metadata').textContent=JSON.stringify({baseline:p.baseline,scores:p.scores},null,2);
}
function reset(){pause();current=null;snapshot=null;plotId=null;$('question-panel').hidden=false;$('case-panel').hidden=true;history.replaceState(null,'','/');picklist();notice('');locks();$('question').focus();}
function adjacent(direction){const steps=snapshot.steps;return direction>0?(steps.find(n=>n>snapshot.cursor)??snapshot.last_sequence):([...steps].reverse().find(n=>n<snapshot.cursor)??0);}
function schedule(){if(!playing)return;timer=setTimeout(async()=>{if(!playing)return;const ok=await action(()=>loadCursor(adjacent(1),true));if(!ok||snapshot.cursor===snapshot.last_sequence){pause();locks();}else schedule();},3500);}
$('question-form').addEventListener('submit',e=>{e.preventDefault();action(async()=>{await renderCase(await request('/api/cases',{question:$('question').value,scope:$('scope').value}));await refreshLibrary();$('design-panel').scrollIntoView({block:'start'});});});
$('review-form').addEventListener('submit',e=>{e.preventDefault();action(async()=>{const result=await request(`/api/cases/${current.manifest.case_id}/confirm`,{revision:current.manifest.revision,candidate:candidateFromForm()});await renderCase(result);await refreshLibrary();if(result.manifest.experiment_link)$('record-panel').scrollIntoView({block:'start'});});});
$('review-form').addEventListener('input',()=>{$('gate').textContent='Confirm these values and connections to explore the matching record.';});
$('back').addEventListener('click',()=>{pause();action(()=>loadCursor(adjacent(-1),true));});
$('next').addEventListener('click',()=>{pause();action(()=>loadCursor(adjacent(1),true));});
$('play').addEventListener('click',()=>{if(playing){pause();locks();return;}playing=true;locks();if(snapshot.cursor===snapshot.last_sequence)action(()=>loadCursor(0)).then(ok=>{if(ok)schedule();});else schedule();});
$('cursor').addEventListener('change',e=>{pause();action(()=>loadCursor(Number(e.target.value)));});
$('plot-select').addEventListener('change',e=>{plotId=e.target.value;renderPlot();});
$('new-case').addEventListener('click',reset);
$('case-picker').addEventListener('change',e=>{pause();const id=e.target.value;if(!id)reset();else action(async()=>renderCase(await request(`/api/cases/${id}`)));});
document.addEventListener('visibilitychange',()=>{if(document.hidden){pause();locks();}});
action(async()=>{await refreshLibrary();const query=new URLSearchParams(location.search),id=query.get('case');if(id){const raw=query.get('event')||'0',cursor=/^\d{1,3}$/.test(raw)&&Number(raw)<=139?Number(raw):0;await renderCase(await request(`/api/cases/${encodeURIComponent(id)}`),cursor);}});
