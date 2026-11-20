import { element } from '../../ui/dialog.js';
import { chooseSample } from '../chooser.js';
export function createSampleChooser({ ai, catalog, urlState, container, document = globalThis.document }) {
  const section = element('section', null, { className: 'fk-ai-panel' }, document), request = element('input', null, { 'aria-label': 'What do you want to make?', placeholder: 'What do you want to make?' }, document), picker = element('select', null, { 'aria-label': 'Sample chooser model' }, document);
  picker.append(element('option', 'Text search (no AI)', { value: '' }, document));
  const find = element('button', 'Find a starting point', { type: 'button' }, document), status = element('p', '', { role: 'status' }, document), results = element('div', null, {}, document);
  const consent = element('input', null, { type: 'checkbox', 'aria-label': 'Allow sending sample metadata' }, document);
  const consentLabel = element('label', ' Allow sending card descriptions and my request to the selected destination.', {}, document); consentLabel.prepend(consent);
  const cap = element('input', null, { type: 'number', min: '0', step: '.01', value: '0', 'aria-label': 'Sample request maximum cost (USD)' }, document);
  let models = [], controller;
  picker.onchange = () => { consent.checked = false; };
  async function refresh() { const previous=picker.value; models = ai ? await ai.models({ capability: 'decide' }) : []; while(picker.options.length>1)picker.remove(1); for (const m of models) picker.append(element('option', `${m.name ?? m.ref} → ${m.destination}`, { value: m.ref }, document)); if(models.some(m=>m.ref===previous))picker.value=previous; }
  find.onclick = async () => {
    controller?.abort(); controller = new AbortController(); results.replaceChildren();
    const model = models.find(m => m.ref === picker.value);
    if (model) { if (!consent.checked) { status.textContent = 'Allow sending sample metadata to the selected destination first.'; return; } ai.consent(model.destination); }
    try {
      const ranked = await chooseSample({ ai, catalog, request: request.value, model: picker.value || null, confirmedCost: Number(cap.value), signal: controller.signal });
      for (const result of ranked) {
        const card = catalog.find(c => c.id === result.id), row = element('p', '', {}, document);
        row.append(element('a', card.title, { href: urlState.build(card.document).href }, document), document.createTextNode(` — ${card.description ?? ''}${result.probability == null ? '' : ` (${(result.probability * 100).toFixed(0)}%)`}`)); results.append(row);
      }
      status.textContent = ranked[0]?.source === 'search' ? 'Text search results.' : ranked[0]?.source === 'emulated' ? 'Model suggestions. Confidence is unavailable for this model.' : (ranked[0]?.probability ?? 0) < .6 ? 'None is a clear match.' : 'Suggested starting points. Open one to continue.';
    } catch (e) { status.textContent = e.message; }
  };
  section.append(element('h2', 'Choose a starting point', {}, document), request, picker, consentLabel, cap, find, status, results); container.append(section); void refresh();
  return { section, refresh, destroy() { controller?.abort(); section.remove(); } };
}
