/** HashBin controls: snapshot saves, quote before charging, and stale-load guards. */
class HashBinPanel {
  constructor({ store, getSnapshot, getFingerprint, onLoad, onSaved }) {
    Object.assign(this, { store, getSnapshot, getFingerprint, onLoad, onSaved });
    this.revision = 0;
    this.status = document.getElementById('hashbin-status');
    this.dialog = document.getElementById('hashbin-dialog');
    this.message = document.getElementById('hashbin-message');
    this.confirm = document.getElementById('hashbin-confirm');
    this.disconnect = document.getElementById('hashbin-disconnect');
    document.getElementById('hashbin-load').onclick = () => this.load(document.getElementById('hashbin-cid').value);
    document.getElementById('hashbin-cid').onkeydown = event => { if (event.key === 'Enter') this.load(event.target.value); };
    document.getElementById('hashbin-save').onclick = () => this.openSave();
    document.getElementById('hashbin-close').onclick = () => this.dialog.close();
    this.dialog.addEventListener('close', () => { this.dialogRevision = (this.dialogRevision || 0) + 1; });
    this.confirm.onclick = () => this.commit();
    this.disconnect.onclick = () => {
      this.store.oauth?.clearTokens();
      this.status.textContent = 'Disconnected from HashBin.';
      this.dialog.close();
    };
  }
  cancelLoad() {
    this.revision++;
    if (this.status.textContent === 'Loading from HashBin…') this.status.textContent = '';
  }
  async load(input) {
    const cid = HashBinDocuments.cid(input);
    if (!cid) { this.status.textContent = 'Enter a valid HashBin CID or saved link.'; return; }
    const revision = ++this.revision;
    this.status.textContent = 'Loading from HashBin…';
    try {
      const snapshot = await this.store.load(cid);
      if (revision !== this.revision) return;
      this.onLoad(snapshot, cid);
      this.status.textContent = 'Loaded from HashBin.';
    } catch (error) { if (revision === this.revision) this.status.textContent = error.message; }
  }
  async openSave() {
    if (this.saving) return;
    const revision = this.dialogRevision = (this.dialogRevision || 0) + 1;
    this.confirm.disabled = true;
    this.disconnect.hidden = true;
    this.confirm.textContent = 'Save';
    this.message.textContent = 'Preparing save…';
    this.dialog.showModal();
    try {
      this.snapshot = this.getSnapshot();
      this.payload = HashBinDocuments.serialize(this.snapshot);
      this.fingerprint = this.getFingerprint();
      this.connecting = !(await this.store.connected());
      if (revision !== this.dialogRevision) return;
      if (this.connecting) {
        this.message.textContent = 'Connect your HashBin account to save. Sign-in returns to this editor with your source intact. Saves use your account balance and retention settings.';
        this.confirm.textContent = 'Connect to HashBin';
      } else {
        this.disconnect.hidden = false;
        const quote = await this.store.quote(this.payload);
        if (revision !== this.dialogRevision) return;
        const dollars = n => `$${(n / 100).toFixed(2)}`;
        this.message.textContent = `${quote.size} bytes · Kept for ${quote.months} month(s)\nCost: ${dollars(quote.cost)} · Balance: ${dollars(quote.balance)}`;
        if (quote.cost > quote.balance) throw new Error('Insufficient HashBin balance. Add funds on hashbin.org before saving.');
      }
      this.confirm.disabled = false;
    } catch (error) { if (revision === this.dialogRevision) this.message.textContent = error.message; }
  }
  async commit() {
    if (this.confirm.disabled || this.saving) return;
    this.confirm.disabled = true;
    this.saving = true;
    try {
      if (this.connecting) {
        // Capture edits made while the connect dialog was open.
        const snapshot = this.getSnapshot();
        const url = await this.store.connect(snapshot);
        location.href = url;
        return;
      }
      if (this.fingerprint !== this.getFingerprint()) {
        this.saving = false;
        await this.openSave();
        return;
      }
      this.message.textContent = 'Saving to HashBin…';
      const result = await this.store.save(this.payload);
      const link = HashBinDocuments.link(location.href, result.cid);
      if (this.fingerprint === this.getFingerprint()) this.onSaved(result.cid, this.fingerprint, link);
      this.status.textContent = 'Saved to HashBin.';
      this.message.replaceChildren(document.createTextNode('Saved. '));
      const a = document.createElement('a');
      a.href = link;
      a.textContent = 'Open saved source';
      this.message.append(a);
      this.confirm.textContent = 'Saved';
    } catch (error) {
      this.message.textContent = error.message;
      this.confirm.disabled = false;
    } finally { this.saving = false; }
  }
}
globalThis.HashBinPanel = HashBinPanel;
