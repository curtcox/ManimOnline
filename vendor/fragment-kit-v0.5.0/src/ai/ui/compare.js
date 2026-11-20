import { element, createDialog, download } from '../../ui/dialog.js';
import { compareChanges } from '../change/compare.js';
import { runEval } from '../eval/runner.js';
import { createReport } from '../eval/report.js';
import { parseSuite, validateReferences } from '../eval/suite.js';
import { loadReport } from '../eval/load.js';
import { parseReport } from '../eval/report.js';
import { metrics } from '../eval/metrics.js';
import { changePrompt } from '../prompts.js';
export function createCompareModels({ ai, type, suite: input, container, storage, onPublish, getSnapshot, getFingerprint, onApply, urlState, document = globalThis.document }) {
  const siteSuite = parseSuite(input, type), dialog = createDialog('Compare models', { id: 'ai-compare', document }); dialog.body.classList.add('fk-ai-compare');
  let suite=siteSuite, savedCases=[];
  const choices = element('div', null, {}, document), repeats = element('input', null, { type: 'number', min: 1, max: 100, value: 1, 'aria-label': 'Comparison repeats' }, document);
  const budget = element('input', null, { type: 'number', min: 0, step: '.01', value: 0, 'aria-label': 'Comparison spending cap' }, document);
  const explanation = element('p', 'Results stay on this device. Select 2–4 models; review destinations and the estimate before running.', {}, document);
  const consent = element('input', null, { type: 'checkbox', 'aria-label': 'Allow comparison requests' }, document), consentLabel = element('label', ' Allow these requests and destinations', {}, document); consentLabel.prepend(consent);
  const run = element('button', 'Run comparison', { type: 'button' }, document), stop = element('button', 'Stop comparison', { type: 'button' }, document), reveal = element('button', 'Reveal model names', { type: 'button' }, document), save = element('button', 'Export report', { type: 'button' }, document);
  const status = element('p', '', { role: 'status' }, document), results = element('div', null, {}, document);
  const includeCases=element('input',null,{type:'checkbox','aria-label':'Include my saved cases'},document), includeLabel=element('label',' Include my saved cases in this comparison',{},document), caseList=element('div',null,{},document);
  includeLabel.prepend(includeCases);
  try { const raw=storage?.getItem('ai:cases');if(raw)savedCases=parseSuite(raw,type).cases.map(c=>({...c,private:true})); }
  catch { status.textContent='Saved cases could not be read. They have not been included.'; }
  function renderCases(){
    caseList.replaceChildren();
    for(const c of savedCases){const row=element('p',c.request??c.id,{},document),remove=element('button','Remove saved case',{type:'button'},document);remove.onclick=()=>{try{const next=savedCases.filter(value=>value.id!==c.id);persistCases(next);renderCases();void updateCases();}catch(e){status.textContent=e.message;}};row.append(remove);caseList.append(row);}
  }
  function persistCases(next){
    if(!storage)throw new Error('Local storage is unavailable.');
    const data={...siteSuite,cases:next};if(next.length)parseSuite(data,type);
    if(next.length)storage.setItem('ai:cases',JSON.stringify(data));else storage.removeItem('ai:cases');savedCases=next;
  }
  async function updateCases(){try{suite=parseSuite({...siteSuite,cases:[...siteSuite.cases,...(includeCases.checked?savedCases:[])]},type);await estimate();}catch(e){includeCases.checked=false;suite=siteSuite;status.textContent=e.message;}}
  includeCases.onchange=updateCases;renderCases();
  let models = [], latest, controller, revealed = false, revision = 0;
  const selected = () => [...choices.querySelectorAll('input:checked')].map(i => i.value);
  async function estimate() {
    const current = ++revision; consent.checked = false; const refs = selected(); let cost = 0;
    try {
      for (const c of suite.cases) {
        const messages = c.kind === 'change' ? (await changePrompt({ type, snapshot: c.base, request: c.request })).messages : [{ role: 'user', content: JSON.stringify({ state: c.state, questions: { answer: c.question } }) }];
        for (const model of refs) cost += ai.estimate({ model, capability: c.kind === 'change' ? 'generate' : 'decide', messages, maxTokens: 2048 }) * Number(repeats.value);
      }
      if (current === revision) explanation.textContent = `${refs.length * suite.cases.length * Number(repeats.value)} calls · estimated maximum $${cost.toFixed(6)} · destinations: ${[...new Set(models.filter(m => refs.includes(m.ref)).map(m => m.destination))].join(', ')}. Results stay on this device.`;
    } catch { if (current === revision) explanation.textContent = 'A selected model has an unknown price. Add a priced model before automated evaluation.'; }
  }
  async function refresh() {
    models = (await ai.models()).filter(m => !m.ref.startsWith('paste:'));
    choices.replaceChildren(); for (const m of models) { const label = element('label', ` ${m.name ?? m.ref} → ${m.destination}`, {}, document), input = element('input', null, { type: 'checkbox', value: m.ref }, document); input.onchange = estimate; label.prepend(input); choices.append(label, element('br', '', {}, document)); }
  }
  function render() {
    results.replaceChildren(); if (!latest) return;
    const table = element('table', null, {}, document), head = element('tr', null, {}, document);
    for (const name of ['Model', 'Success (N)', '95% interval', 'Cost / success', 'Time']) head.append(element('th', name, {}, document)); table.append(head);
    latest.metrics.rows.forEach((r, i) => {
      const row = element('tr', null, {}, document);
      for (const value of [revealed ? r.model : `Model ${String.fromCharCode(65 + i)}`, `${r.successes}/${r.n}`, `${(r.interval.low * 100).toFixed(0)}–${(r.interval.high * 100).toFixed(0)}%`, r.costPerSuccess == null ? 'unknown' : '$' + r.costPerSuccess.toFixed(6), (r.totalMs / 1000).toFixed(2) + 's']) row.append(element('td', value, {}, document));
      table.append(row);
    });
    results.append(table, element('p', latest.metrics.conclusion, {}, document)); save.disabled = false; reveal.disabled = false;
  }
  run.onclick = async () => {
    const refs = selected(); if (refs.length < 2 || refs.length > 4 || !consent.checked) { status.textContent = 'Select 2–4 models and allow the displayed destinations first.'; return; }
    controller?.abort(); controller = new AbortController(); run.disabled = true; revealed = false;
    for (const m of models.filter(m => refs.includes(m.ref))) ai.consent(m.destination);
    try { latest = await runEval({ ai, type, suite, models: refs, repeats: Number(repeats.value), budget: Number(budget.value), storage, signal: controller.signal, onProgress: p => { status.textContent = `${p.completed} results recorded.`; } }); render(); status.textContent = latest.stopped ? `Stopped: ${latest.stopped}. Completed results are kept.` : 'Comparison complete. Models are hidden until you reveal them.'; }
    catch (e) { status.textContent = e.message; } finally { run.disabled = false; }
  };
  stop.onclick = () => controller?.abort(); reveal.onclick = () => { revealed = true; render(); };
  save.disabled = reveal.disabled = true; save.onclick = () => download(new Blob([JSON.stringify(latest.format === 'fragment-kit-eval-report' ? latest : createReport(latest), null, 2)], { type: 'application/json' }), 'ai-evaluation.json');
  dialog.dialog.addEventListener('close', () => controller?.abort()); repeats.oninput = estimate;
  dialog.body.append(explanation, choices, repeats, budget, consentLabel, run, stop, reveal, save, status, results);
  dialog.body.append(element('p','Saved cases contain your document and request. They stay on this device, use exact document matching, and are excluded from report export.',{},document),includeLabel,caseList);
  if (getSnapshot && getFingerprint && onApply) {
    const request = element('textarea', null, { 'aria-label': 'My comparison request', placeholder: 'Describe a change to compare on your own document' }, document);
    const compareRequest = element('button', 'Compare my request', { type: 'button' }, document);
    const warning = element('p', 'This sends your current document to each selected destination. Proposals and your preference stay on this device.', {}, document);
    compareRequest.onclick = async () => {
      if (!consent.checked) { status.textContent = 'Allow the selected destinations first.'; return; }
      const refs=selected(); controller?.abort(); controller=new AbortController(); results.replaceChildren();
      const base=structuredClone(getSnapshot()), caseRequest=request.value;
      for (const m of models.filter(m=>refs.includes(m.ref))) ai.consent(m.destination);
      try {
        const comparison=await compareChanges({ai,type,request:request.value,models:refs,budget:Number(budget.value),getSnapshot,getFingerprint,onApply,urlState,signal:controller.signal});
        for (const entry of comparison.entries) {
          const section=element('section',null,{},document), heading=element('h3',`Model ${entry.label}`,{},document), text=element('pre',entry.proposal?.diff??entry.error,{},document), accept=element('button',`Accept ${entry.label}`,{type:'button'},document), reveal=element('button',`Reveal ${entry.label}`,{type:'button'},document);
          text.style.whiteSpace='pre-wrap'; text.style.overflowWrap='anywhere'; reveal.onclick=()=>{heading.textContent=entry.model;};
          accept.disabled=!entry.proposal; accept.onclick=()=>{try{entry.accept();storage?.setItem(`ai:vote:${Date.now()}`,JSON.stringify({model:entry.model,accepted:true}));status.textContent='Selected proposal accepted. Preference saved locally.';for(const button of results.querySelectorAll('button'))button.disabled=true;}catch(e){status.textContent=e.message;}};
          const saveCase=element('button',`Save ${entry.label} as a local case`,{type:'button','data-ai-save-case':''},document);saveCase.disabled=!entry.proposal;
          saveCase.onclick=async()=>{try{
            const good=structuredClone(entry.proposal.document), c={id:'my-'+crypto.randomUUID(),kind:'change',private:true,base,request:caseRequest,checks:Object.entries(good).map(([key,value])=>({type:'fieldEquals',path:'/'+key.replace(/~/g,'~0').replace(/\//g,'~1'),value})),reference:{good,bad:base}};
            const checked=parseSuite({...siteSuite,cases:[c]},type);await validateReferences(checked,type);persistCases([...savedCases,...checked.cases]);renderCases();await updateCases();saveCase.disabled=true;status.textContent='Case saved on this device. Its document and request are private.';
          }catch(e){status.textContent=e.message;}};
          section.append(heading,text,accept,reveal,saveCase);results.append(section);
        }
        status.textContent='Blind proposals ready. Review each change before accepting.';
      } catch(e){status.textContent=e.message;}
    };
    dialog.body.append(warning,request,compareRequest);
  }
  const reportCID = element('input', null, { 'aria-label': 'Evaluation report CID', placeholder: '256t report CID or saved link' }, document);
  const importReport = element('button', 'Open report', { type: 'button' }, document);
  importReport.onclick = async () => { try { const report = await loadReport(reportCID.value); latest = { ...report, metrics: metrics(report.results) }; revealed = true; render(); status.textContent = 'This report is self-reported. Its saved contents are verified; its measurements are not independently verified. Its suite and conditions may differ from local results.'; } catch (e) { status.textContent = e.message; } };
  dialog.body.append(reportCID, importReport);
  if (onPublish) { const publish = element('button', 'Publish report', { type: 'button' }, document); publish.onclick = () => { if (latest) onPublish(createReport(latest)); }; dialog.body.append(publish); }
  const button = element('button', 'Compare models', { type: 'button', id: 'ai-compare-open' }, document); button.onclick = () => { void refresh(); dialog.open(); }; container?.append(button);
  return { ...dialog, button, refresh };
}
