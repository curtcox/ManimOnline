import { element, createDialog } from '../ui/dialog.js';
import { bytes } from '../core/bytes.js';

export class HashBinPanel {
  constructor({ store, urlState, getSnapshot, getFingerprint = () => JSON.stringify(getSnapshot()), onLoad, onSaved = () => {}, container = document.body }) {
    Object.assign(this, { store, urlState, getSnapshot, getFingerprint, onLoad, onSaved });
    this.revision = 0;
    this.input = element('input', null, { 'aria-label': 'HashBin CID or saved link', placeholder: 'CID or saved link', id: 'hashbin-cid' });
    this.loadButton = element('button', 'Load from HashBin', { type: 'button', id: 'hashbin-load' });
    this.saveButton = element('button', 'Save to HashBin', { type: 'button', id: 'hashbin-save' });
    this.status = element('span', '', { role: 'status', id: 'hashbin-status' });
    container.append(this.input, this.loadButton, this.saveButton, this.status);
    this.ui = createDialog('Save to HashBin', { id: 'hashbin-dialog', onClose: () => { this.dialogRevision++; } });
    this.dialog = this.ui.dialog;
    this.message = element('p', '', { role: 'status', id: 'hashbin-message' });
    this.confirm = element('button', 'Review on HashBin', { type: 'button', id: 'hashbin-confirm' });
    this.ui.body.append(this.message, this.confirm);
    this.loadButton.onclick = () => this.load(this.input.value);
    this.input.onkeydown = event => { if (event.key === 'Enter') this.load(this.input.value); };
    this.saveButton.onclick = () => this.openSave();
    this.confirm.onclick = () => this.commit();
    this.dialogRevision = 0;
  }
  cancelLoad() { this.revision++; if (this.status.textContent === 'Loading from HashBin…') this.status.textContent = ''; }
  async load(input) {
    const revision = ++this.revision, cid = this.store.cid(input);
    this.status.textContent = 'Loading from HashBin…';
    try {
      if (!cid) throw new Error('Enter a valid HashBin CID or saved link.');
      const snapshot = await this.store.load(cid);
      if (revision !== this.revision) return;
      await this.onLoad(snapshot, cid);
      if (revision === this.revision) this.status.textContent = 'Loaded from HashBin.';
    } catch (error) { if (revision === this.revision) this.status.textContent = error.message; }
  }
  async openSave() {
    if (this.saving) return;
    const revision = ++this.dialogRevision;
    this.confirm.disabled = true; this.confirm.textContent = 'Review on HashBin';
    this.message.textContent = 'Preparing save…'; this.ui.open();
    try {
      this.snapshot = structuredClone(this.getSnapshot());
      this.payload = this.store.documents.serialize(this.snapshot);
      this.fingerprint = this.getFingerprint();
      await this.store.init();
      if (revision !== this.dialogRevision) return;
      this.message.textContent = `${bytes(this.payload).length} bytes. HashBin shows the retention, exact price and your balance, and you approve the save on hashbin.org. This editor never holds your HashBin sign-in.`;
      this.confirm.disabled = false;
    } catch (error) { if (revision === this.dialogRevision) this.message.textContent = error.message; }
  }
  async commit() {
    if (this.confirm.disabled || this.saving) return;
    if (this.fingerprint !== this.getFingerprint()) { await this.openSave(); return; }
    this.confirm.disabled = true; this.saving = true;
    try {
      const pending = this.store.publish(this.payload, this.snapshot);
      this.message.textContent = 'Waiting for your approval on HashBin…';
      const result = await pending;
      if (result.redirected) return;
      const href = this.urlState.link(location.href, result.cid);
      if (this.fingerprint === this.getFingerprint()) await this.onSaved(result.cid, this.fingerprint, href);
      this.status.textContent = 'Saved to HashBin.';
      this.message.replaceChildren(element('a', 'Open saved source', { href }));
      this.confirm.textContent = 'Saved';
    } catch (error) { this.message.textContent = error.message; this.confirm.disabled = false; }
    finally { this.saving = false; }
  }
  async published(hash) {
    const revision = ++this.revision;
    const result = await this.store.published(hash);
    if (!result || revision !== this.revision) return;
    if (result.snapshot) await this.onLoad(result.snapshot, result.error ? null : result.cid);
    if (revision !== this.revision) return;
    if (result.error) this.status.textContent = result.error;
    else if (result.cid) await this.onSaved(result.cid, this.getFingerprint(), this.urlState.link(location.href, result.cid));
    return result;
  }
}
