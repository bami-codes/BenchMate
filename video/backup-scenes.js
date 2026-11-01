// Standalone backup-only scenes. No changes to the original full-edit timeline.
SCENES.backup_intro=(C,D)=>{
 document.body.style.background='#183d35';chapter('BenchMate',true);
 const title=E('div',{style:{position:'absolute',left:'110px',top:'135px',fontSize:'76px',fontWeight:600,color:'#f6faf6'}},stage,'Ask the circuit.');
 const lead=E('div',{style:{position:'absolute',left:'110px',top:'244px',width:'1000px',fontSize:'34px',color:'#b9d6cb',lineHeight:1.4}},stage,'Muse Spark chooses the experiment.<br>The bench checks the explanation.');
 const cards=[['Spark','Chooses measurements and proposes models'],['BenchMate engine','Fits, scores and freezes the prediction'],['Arduino + operator','Records IN/OUT; a person changes wires']].map(([h,b],i)=>{
  const el=E('div',{style:{position:'absolute',left:'110px',top:(390+i*135)+'px',width:'1030px',padding:'22px 28px',background:'#244d43',border:'1px solid #608a7a',borderRadius:'14px',color:'#fff'}},stage,`<div style="font-size:31px;font-weight:600">${h}</div><div style="font-size:25px;color:#b9d6cb;margin-top:7px">${b}</div>`);return el;
 });
 const picture=E('img',{src:D.backup.photo,style:{position:'absolute',left:'1240px',top:'130px',width:'540px',height:'720px',objectFit:'contain',borderRadius:'18px'}},stage);
 const caption=E('div',{style:{position:'absolute',left:'1240px',top:'865px',width:'540px',fontSize:'19px',color:'#a9cdbf',lineHeight:1.4}},stage,'RC test-board reference photo.<br>Not a photo of the two-capacitor fault.');
 return t=>{enter(title,t,.15,.6);enter(lead,t,.6,.5);cards.forEach((el,i)=>enter(el,t,1+i*1.1,.5));picture.style.opacity=caption.style.opacity=tw(t,1,.8);};
};
SCENES.backup_repair=(C,D)=>{
 document.body.style.background='#f7f8f5';chapter('Repair rehearsal');prov('sim','SIMULATED BENCH + OPERATOR · ACTUAL SPARK');
 const r=D.backupRepair,c=C.cues;
 const panel=box(72,140,1120,710);const title=E('div',{style:{position:'absolute',left:'30px',top:'24px',fontSize:'31px',fontWeight:600}},panel,'Would restoring the design fix the response?');
 const leg=E('div',{style:{position:'absolute',left:'30px',top:'84px'}},panel);legendItem(leg,0,0,'#bb4c27','Simulated output');legendItem(leg,290,0,'#315e91','Frozen model using measured input',true);
 const plot=chart(panel,{x:10,y:145,w:1080,h:450,xr:[0,.256],yr:[-.13,.13],ticksX:[0,.05,.1,.15,.2,.25],ticksY:[-.1,0,.1],fmtX:v=>Math.round(v*1000)+' ms',fmtY:v=>v.toFixed(1),xlabel:'time',ylabel:'V'});
 const out=plot.line(r.t,r.observed,{color:'#bb4c27',width:4}),pred=plot.line(r.t,r.predicted,{color:'#315e91',dash:'10 9',width:3.5});
 E('div',{style:{position:'absolute',left:'30px',bottom:'25px',width:'1040px',fontSize:'21px',color:'#55635e',lineHeight:1.4}},panel,'Two separate post-repair checks. The frozen model must pass both; the unchanged model must fail at least one.');
 const req=box(1230,140,618,null,{padding:'25px 28px'});req.innerHTML='<span class="badge spark">Spark’s action</span><div style="font-size:36px;font-weight:600;margin:15px 0">Restore nominal capacitance.</div><div style="font-size:23px;line-height:1.5;color:#55635e">'+r.reason_en+'</div><div style="font-size:18px;color:#6b7873;margin-top:14px">English summary of the recorded Korean request.</div>';
 const score=box(1230,590,618,null,{padding:'24px 28px',borderColor:'#bcd8c8'});score.innerHTML=`<span class="badge pass">Both conditional checks passed</span><div class="mono" style="font-size:27px;line-height:1.7;margin-top:12px">step ${r.restored[0].conditional_rms_mV.toFixed(2)} mV · sine ${r.restored[1].conditional_rms_mV.toFixed(2)} mV</div><div style="font-size:20px;line-height:1.4;color:#55635e;margin-top:10px">Command forecast errors: ${r.restored.map(x=>x.command_rms_mV.toFixed(2)).join(' / ')} mV.<br>Model frozen locally; not pushed during this mock.</div>`;
 return t=>{enter(panel,t,.3,.6);enter(req,t,c.R2.start-.2,.5);plot.reveal(out,tw(t,c.R3.start-.5,1.2,ease));plot.reveal(pred,tw(t,c.R3.start+.8,1.,ease));enter(score,t,c.R3.start+1.7,.6);};
};
SCENES.backup_close=(C,D)=>{
 document.body.style.background='#183d35';const c=C.cues;chapter('Built during the hackathon',true);
 const name=E('div',{style:{position:'absolute',left:'110px',top:'155px',fontSize:'110px',fontWeight:600,color:'#fff'}},stage,'BenchMate');
 const claim=E('div',{style:{position:'absolute',left:'110px',top:'310px',fontSize:'48px',width:'1660px',color:'#cfe3db',lineHeight:1.3}},stage,'Turn a plausible explanation<br>into a tested one.');
 const facts=E('div',{style:{position:'absolute',left:'110px',top:'530px',fontSize:'29px',width:'1640px',lineHeight:1.7,color:'#a9cdbf'}},stage,'Build guide · parts basket ≈ $40, excluding laptop and meter<br>Recorded decisions · raw measurements · every failed attempt<br>Current physical evidence: D01 diagnosis. Physical repair and B5 are next.');
 const url=E('div',{style:{position:'absolute',left:'110px',top:'790px',fontSize:'37px',fontWeight:600,color:'#f5ca4f'}},stage,'bami-codes.github.io/BenchMate');
 E('div',{style:{position:'absolute',left:'110px',top:'872px',fontSize:'21px',color:'#82ac9c'}},stage,'First commit: October 27, 2026 · Runtime: Muse Spark · Coding assistance: Codex & Claude');
 return t=>{enter(name,t,.15,.5);enter(claim,t,.55,.6);enter(facts,t,c.C1.start+.6,.6);enter(url,t,c.C3.start-.4,.5);};
};
