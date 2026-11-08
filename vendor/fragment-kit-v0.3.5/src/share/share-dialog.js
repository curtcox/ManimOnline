import { createDialog, element } from '../ui/dialog.js';
import { ShareClient } from './shortener.js';

export function createShareDialog({ urlState, getSnapshot, onSave, client = new ShareClient() }) {
  let snapshot, links, revision = 0;
  const ui = createDialog('Share', { id: 'share-dialog', onClose: () => { revision++; client.cancel(); } });
  const field = element('textarea', null, { readonly: '', 'aria-label': 'Share link', id: 'share-link', rows: 3 });
  const run = element('input', null, { type: 'checkbox', id: 'share-run' }); run.checked = true;
  const label = element('label', 'Run on open'); label.prepend(run);
  const status = element('p', '', { role: 'status' });
  const copy = element('button', 'Copy link', { type: 'button' }), shorten = element('button', 'Shorten link', { type: 'button' });
  const save = element('button', 'Save to HashBin', { type: 'button' }); save.disabled = !onSave;
  const rebuild = () => { revision++; client.cancel(); links = urlState.build(snapshot, { run: run.checked }); field.value = links.href; status.textContent = ''; shorten.disabled = false; };
  run.onchange = rebuild;
  copy.onclick = async () => { try { await navigator.clipboard.writeText(field.value); status.textContent = 'Copied.'; } catch { field.focus(); field.select(); status.textContent = 'Select and copy the link.'; } };
  shorten.onclick = async () => {
    const current = ++revision; shorten.disabled = true; status.textContent = 'Shortening…';
    const result = await client.shorten(links);
    if (current !== revision || !result) return;
    field.value = result.url; status.textContent = result.shortened ? 'Short link ready.' : result.error.message; shorten.disabled = false;
  };
  save.onclick = () => { ui.dialog.close(); onSave(); };
  ui.body.append(field, label, copy, shorten, save, status);
  return { ...ui, open() { snapshot = structuredClone(getSnapshot()); rebuild(); ui.open(); } };
}
