'use strict';
const $ = id => document.getElementById(id);
const token = document.querySelector('meta[name="benchmate-session"]').content;
const nodes = ['IN', 'OUT', 'REF', 'N1', 'N2', 'UNKNOWN'];
let current = null, library = [], busy = false, designDirty = false;
async function request(path, body) {
  const response = await fetch(path, body === undefined ? {} : {method:'POST', headers:{'Content-Type':'application/json', 'X-BenchMate-Session':token}, body:JSON.stringify(body)});
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || 'The local request could not be completed.');
  return result;
}
function notice(message) { $('notice').textContent = message; $('notice').hidden = !message; }
async function action(fn) {
  if (busy) return;
  busy = true; notice(''); document.body.setAttribute('aria-busy', 'true');
  const controls = [...document.querySelectorAll('button, input, select, textarea')];
  const disabled = controls.map(x => x.disabled); controls.forEach(x => x.disabled = true);
  try { await fn(); } catch (error) { notice(error.message + ' Your previous saved revisions are retained. Reload the case before retrying.'); }
  finally { controls.forEach((x,i) => x.disabled = disabled[i]); busy = false; document.body.removeAttribute('aria-busy'); updateLocks(); }
}
function updateLocks() {
  if (!current) return;
  const linked = !!current.manifest.experiment_link;
  $('review-fields').disabled = linked;
  $('link-replay').disabled = linked || designDirty || !current.replay_eligibility.allowed;
}
function picklist() {
  $('case-picker').replaceChildren(new Option('Start a question', ''));
  for (const item of library) $('case-picker').add(new Option(item.question.slice(0,85) + ' · ' + item.status.replaceAll('_', ' '), item.case_id));
  $('case-picker').value = current?.manifest.case_id || '';
}
async function refreshLibrary() { library = (await request('/api/state')).cases; picklist(); }
function field(labelText, input) {
  const label = document.createElement('label'); label.append(document.createTextNode(labelText), input); return label;
}
function components(candidate) {
  $('components').replaceChildren();
  for (const [index, item] of candidate.components.entries()) {
    const box = document.createElement('div'); box.className = 'component';
    const heading = document.createElement('p'); heading.className = 'component-title'; heading.textContent = item.name + ' · ' + (item.kind === 'R' ? 'Resistor' : item.kind === 'C' ? 'Capacitor' : 'Diode');
    const grid = document.createElement('div'); grid.className = 'component-grid';
    const value = document.createElement('input'); value.id = `value-${index}`; value.type = 'number'; value.step = 'any'; value.min = '0'; value.placeholder = 'Unknown';
    const scale = item.kind === 'R' ? 1000 : item.kind === 'C' ? .000001 : 1;
    value.value = item.value_si === null ? '' : Number((item.value_si / scale).toPrecision(12));
    grid.append(field(item.kind === 'R' ? 'Value (kΩ)' : item.kind === 'C' ? 'Value (µF)' : 'Value (unknown)', value));
    for (const key of ['a', 'b']) {
      const select = document.createElement('select'); select.id = `${key}-${index}`;
      for (const node of nodes) select.add(new Option(node === 'UNKNOWN' ? 'Unknown' : node, node));
      select.value = item[key]; grid.append(field(key === 'a' ? 'From' : 'To', select));
    }
    box.append(heading, grid); $('components').append(box);
  }
}
function candidateFromForm() {
  const candidate = structuredClone(current.manifest.intended_design.draft_candidate);
  for (const [index, item] of candidate.components.entries()) {
    const raw = $(`value-${index}`).value;
    item.value_si = raw === '' ? null : Number(raw) * (item.kind === 'R' ? 1000 : item.kind === 'C' ? .000001 : 1);
    item.a = $(`a-${index}`).value; item.b = $(`b-${index}`).value;
    if (item.value_si !== null && (!Number.isFinite(item.value_si) || item.value_si <= 0)) throw new Error('Use a positive component value, or leave it blank if unknown.');
  }
  const unknown = candidate.components.some(x => x.value_si === null || [x.a,x.b].includes('UNKNOWN'));
  candidate.status = unknown ? 'incomplete' : 'needs_review';
  candidate.ambiguities = unknown ? ['Operator left a component value or connection unresolved.'] : [];
  return candidate;
}
function render(result) {
  current = result; designDirty = false;
  const m = result.manifest, d = m.intended_design, linked = m.experiment_link;
  $('question-panel').hidden = true; $('case-panel').hidden = false;
  $('saved-question').textContent = m.question.text;
  $('scope-note').textContent = m.scope === 'recorded_walkthrough' ? 'Exploring the recorded D01 example. This question has not been sent to Spark.' : 'A different circuit. The archived D01 experiment cannot answer this case.';
  $('reading-summary').textContent = 'R1 connects IN to OUT; C1 connects OUT to REF. Confirm the values and connections against the image.';
  components(d.draft_candidate);
  $('review-note').value = d.review_note || ''; $('review-confirm').checked = !!d.review_note;
  $('gate').textContent = linked ? 'Design review saved. The matching historical experiment is linked below.' : result.replay_eligibility.message;
  $('gate').classList.toggle('ready', result.replay_eligibility.allowed);
  $('step1').classList.remove('current'); $('step2').classList.toggle('current', !linked); $('step3').classList.toggle('current', !!linked);
  $('record-panel').hidden = !linked;
  if (linked) {
    const url = `/api/cases/${m.case_id}/replay`;
    if ($('replay').getAttribute('src') !== url) $('replay').src = url;
    $('scene-nav').replaceChildren();
    for (const [index, scene] of linked.scenes.entries()) {
      const button = document.createElement('button'); button.type = 'button'; button.textContent = `${index + 1}. ${scene.label}`;
      button.addEventListener('click', () => {
        const ui = $('replay').contentWindow?.BenchMateUI;
        if (!ui) { notice('The recorded viewer is still loading. Try the scene again in a moment.'); return; }
        ui.select(scene.event_sequence);
        for (const item of $('scene-nav').children) item.classList.toggle('selected', item === button);
        notice('');
      });
      $('scene-nav').append(button);
    }
  } else $('replay').removeAttribute('src');
  $('provenance').replaceChildren();
  const entries = {'Question':'Current local entry · not part of the archived run', 'Design reading':`${d.source_date_kst} · synthetic schematic · recorded Spark output`, 'Physical experiment':linked ? `${linked.source_date_kst} · same nominal design only · Replay` : 'Not linked', 'Assembly photo':'Not linked; no common specimen state established', 'Case revision':`${m.revision} · ${result.manifest_sha256}`};
  for (const [key,value] of Object.entries(entries)) { const dt = document.createElement('dt'), dd = document.createElement('dd'); dt.textContent = key; dd.textContent = value; $('provenance').append(dt,dd); }
  $('manifest').textContent = JSON.stringify(result, null, 2); $('export').href = `/api/cases/${m.case_id}/export`;
  history.replaceState(null, '', `?case=${m.case_id}`); picklist(); updateLocks();
}
function reset() {
  current = null; designDirty = false; $('question-panel').hidden = false; $('case-panel').hidden = true; $('replay').removeAttribute('src');
  $('step1').classList.add('current'); $('step2').classList.remove('current'); $('step3').classList.remove('current');
  history.replaceState(null, '', '/'); picklist(); notice(''); $('question').focus();
}
$('question-form').addEventListener('submit', event => { event.preventDefault(); const question = $('question').value, scope = document.querySelector('[name=scope]:checked').value; action(async () => { render(await request('/api/cases', {question, scope})); await refreshLibrary(); $('design-panel').scrollIntoView({block:'start', behavior:'smooth'}); }); });
$('review-form').addEventListener('input', () => {
  if (!current || current.manifest.experiment_link) return;
  designDirty = true;
  $('gate').textContent = 'You have unsaved review changes. Save this review before opening the recorded experiment.';
  $('gate').classList.remove('ready'); updateLocks();
});
$('review-form').addEventListener('submit', event => { event.preventDefault(); action(async () => { const candidate = candidateFromForm(); render(await request(`/api/cases/${current.manifest.case_id}/review`, {revision:current.manifest.revision, candidate, review_note:$('review-note').value})); await refreshLibrary(); }); });
$('link-replay').addEventListener('click', () => action(async () => { render(await request(`/api/cases/${current.manifest.case_id}/link-replay`, {revision:current.manifest.revision})); await refreshLibrary(); $('record-panel').scrollIntoView({block:'start', behavior:'smooth'}); }));
$('new-case').addEventListener('click', reset);
$('case-picker').addEventListener('change', event => { const id = event.target.value; if (!id) reset(); else action(async () => render(await request(`/api/cases/${id}`))); });
action(async () => { await refreshLibrary(); const id = new URLSearchParams(location.search).get('case'); if (id) render(await request(`/api/cases/${encodeURIComponent(id)}`)); });
