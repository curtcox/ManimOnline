import { createDialog, element } from '../../ui/dialog.js';
import { prepareOpenRouterSignIn } from '../connections/oauth.js';
export function createAiSettings({ ai, container, onChange = () => {}, document = globalThis.document }) {
  const dialog = createDialog('AI settings', { document, id: 'ai-settings' });
  const spending = element('p', '', {}, document);
  const refreshSpending = () => {const used=ai.budget.spent();spending.textContent=`Used or reserved (USD): total ${used.total.toFixed(9)} · day ${used.day.toFixed(9)} · month ${used.month.toFixed(9)}`;};
  const status = element('p', '', { role: 'status' }, document);
  const route = element('select', null, { 'aria-label': 'Provider' }, document);
  for (const value of ['openrouter', 'openai', 'anthropic', 'gemini']) route.append(element('option', value, { value }, document));
  const key = element('input', null, { type: 'password', autocomplete: 'off', 'aria-label': 'API key' }, document);
  const warning = element('p', ai.connection === 'direct' ? 'A key pasted here is available to scripts on this page while it is connected. It is kept only in memory and disappears on reload.' : ai.connection === 'host' ? 'Connect on the separate AI host. This page never receives your key.' : ai.connection === 'gateway' ? 'This site supplies gateway authorization. Your prompts pass through its server.' : 'This deployment offers paste handoff only.', {}, document);
  const connect = element('button', ai.connection === 'host' ? 'Open AI host' : 'Connect key', { type: 'button' }, document);
  connect.onclick = () => { try { const pending = ai.connect(route.value, key.value); pending?.catch(e => { status.textContent = e.message; }); key.value = ''; status.textContent = ai.connection === 'host' ? 'Approve this app on the AI host, then return here.' : 'Connected for this session.'; } catch (e) { key.value = ''; status.textContent = e.message; } };
  const disconnect = element('button', 'Disconnect', { type: 'button' }, document); disconnect.onclick = () => { ai.disconnect(); key.value = ''; status.textContent = 'Disconnected.'; };
  const signin = element('button', 'Sign in with OpenRouter', { type: 'button' }, document); signin.disabled = true;
  let oauth;
  async function prepareSignIn() {
    try { const callback = new URL(document.defaultView.location.href); callback.search = callback.hash = ''; if(callback.pathname.endsWith('/'))callback.pathname+='index.html'; oauth = await prepareOpenRouterSignIn({ callbackURL: callback.href, connect: ai.connect }); signin.disabled = false; } catch { /* Paste keys remain available. */ }
  }
  signin.onclick = () => {
    signin.disabled = true;
    const pending = oauth.start(); // Opens synchronously inside this click.
    pending.then(() => { status.textContent = 'OpenRouter connected for this session.'; }, error => { status.textContent = error.message; }).finally(prepareSignIn);
  };
  const budgetInputs = {};
  const budgetGroup = element('fieldset', null, {}, document); budgetGroup.append(element('legend', 'Spending caps (USD)', {}, document));
  for (const period of ['total', 'day', 'month']) {
    const label = element('label', `${period} `, {}, document), input = element('input', null, { type: 'number', min: '0', step: '0.01', value: ai.budget.caps[period], 'aria-label': `${period} spending cap` }, document);
    label.append(input); budgetGroup.append(label); budgetInputs[period] = input;
  }
  const save = element('button', 'Set spending caps', { type: 'button' }, document);
  save.onclick = () => { try { ai.budget.configure(Object.fromEntries(Object.entries(budgetInputs).map(([p, i]) => [p, Number(i.value)]))); status.textContent = 'Spending caps updated. The local ledger is a guard; provider limits also apply.'; onChange(); } catch (e) { status.textContent = e.message; } };
  budgetGroup.append(save);
  const ref = element('input', null, { placeholder: 'openai:model-name', 'aria-label': 'Model reference' }, document);
  const base = element('input', null, { placeholder: 'http://localhost:11434/v1/', 'aria-label': 'Local model base URL' }, document);
  const add = element('button', 'Add model', { type: 'button' }, document);
  add.onclick = () => { try {
    const provider = ref.value.split(':')[0];
    ai.addModel({ ref: ref.value, capabilities: ['generate', 'decide'], pinned: false, prices: provider === 'local' ? { input: 0, output: 0 } : null, destination: provider === 'local' ? base.value : provider, ...(provider === 'local' ? { baseURL: base.value } : {}) });
    ref.value = ''; status.textContent = 'Model added. Unknown prices need a maximum cost for each call.'; onChange();
  } catch (e) { status.textContent = e.message; } };
  dialog.body.append(warning,spending);
  if (ai.connection === 'direct') { dialog.body.append(route, key, connect, signin, disconnect); void prepareSignIn(); }
  else if (ai.connection === 'host') dialog.body.append(connect, disconnect);
  dialog.body.append(budgetGroup, element('h3', 'Add a model', {}, document), ref, base, element('p', 'Local servers may trigger a browser permission request. Allow access only to a server you control.', {}, document), add, status);
  const modelCID = element('input', null, { 'aria-label': 'Browser model manifest CID', placeholder: '256t manifest CID or saved link' }, document);
  const inspect = element('button', 'Inspect model manifest', { type: 'button' }, document), modelInfo = element('p', '', {}, document);
  const approveModel = element('input', null, { type: 'checkbox', 'aria-label': 'Approve model download' }, document);
  const approveLabel = element('label', ' I approve the size, licence, source, memory and mirrors shown above.', {}, document); approveLabel.prepend(approveModel);
  const downloadModel = element('button', 'Download verified model', { type: 'button' }, document), remove = element('button', 'Delete model data', { type: 'button' }, document);
  let loaded;
  inspect.onclick = async () => { try {
    loaded = await ai.loadModel(modelCID.value); approveModel.checked = false;
    const estimate = await globalThis.navigator?.storage?.estimate?.();
    modelInfo.textContent = `${loaded.manifest.name}: ${loaded.bytes} bytes. Licence ${loaded.manifest.license.id} (${loaded.manifest.license.url}). Source ${loaded.manifest.source}. Memory needed ${loaded.manifest.requires.memoryBytes} bytes. Free storage ${estimate?.quota ? estimate.quota - (estimate.usage ?? 0) : 'unknown'}. Mirrors ${JSON.stringify(loaded.manifest.mirrors)}. A CID proves unchanged bytes; it does not prove model quality or safety.`; onChange();
  } catch (e) { loaded = null; status.textContent = e.message; } };
  downloadModel.onclick = async () => { try {
    if (!loaded) throw new Error('Inspect a model manifest first.');
    const result = await ai.downloadModel(loaded.cid, { consent: approveModel.checked, onProgress: p => { status.textContent = `${p.completed}/${p.total} verified bytes.`; } }); status.textContent = `Model ready: ${result.bytes} bytes.`;
  } catch (e) { status.textContent = e.message; } };
  remove.onclick = async () => { try { if (!loaded) throw new Error('Inspect a model manifest first.'); await ai.removeModel(loaded.cid); loaded = null; status.textContent = 'Model data deleted.'; onChange(); } catch (e) { status.textContent = e.message; } };
  if(ai.browserModelsEnabled)dialog.body.append(element('h3', 'Browser model storage', {}, document), modelCID, inspect, modelInfo, approveLabel, downloadModel, remove);

  const button = element('button', 'AI settings', { type: 'button', id: 'ai-settings-open' }, document); button.onclick = () => {refreshSpending();dialog.open();}; container?.append(button);
  return { ...dialog, button };
}
