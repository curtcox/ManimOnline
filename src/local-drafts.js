/* URL documents and local recovery are independent. Never restore a draft implicitly. */
(() => {
class LocalDrafts {
  constructor({ storage, key, serialize = JSON.stringify, parse = JSON.parse }) {
    Object.assign(this, { storage, key, serialize, parse }); this.active = false;
  }
  opened() { this.active = false; }
  history() {
    const values = JSON.parse(this.storage?.getItem(this.key + ':history') || '[]');
    if (!Array.isArray(values) || values.some(value => typeof value !== 'string')) throw Error('Invalid draft history.');
    return values;
  }
  list() {
    const current = this.storage?.getItem(this.key);
    return [...new Set([...(current ? [current] : []), ...this.history()])].flatMap(text => {
      try { const value = this.parse(text); return value ? [value] : []; } catch (_) { return []; }
    });
  }
  save(value, edit = false) {
    if (!this.active && !edit) return;
    if (!this.storage) throw Error('Browser storage is unavailable.');
    const text = this.serialize(value);
    if (!this.active) {
      const current = this.storage.getItem(this.key);
      const history = [...new Set([...(current ? [current] : []), ...this.history()])].filter(old => old !== text);
      // Save recovery first. A quota error must leave the previous work intact.
      this.storage.setItem(this.key + ':history', JSON.stringify(history));
    }
    this.storage.setItem(this.key, text); this.active = true;
  }
  attempt(value, edit = false) {
    try { this.save(value, edit); if (this.message) this.message.textContent = ''; return true; }
    catch (_) { if (this.message) this.message.textContent = 'Work could not be saved in this browser. Previous drafts were kept. Download your work to keep it.'; return false; }
  }
  mount(container, onRestore, describe = value => value.src ?? value.source ?? JSON.stringify(value, null, 2)) {
    const make = (tag, id, text) => { const node = document.createElement(tag); node.id = id; if (text) node.textContent = text; return node; };
    const button = make('button', 'resume-work', 'Resume saved work'); button.type = 'button';
    this.message = make('span', 'draft-recovery-status'); this.message.setAttribute('role', 'status');
    container.append(button, this.message);
    const dialog = make('dialog', 'draft-dialog'); dialog.className = 'draft-recovery';
    const title = make('h2', 'draft-title', 'Resume saved work'); dialog.setAttribute('aria-labelledby', title.id);
    const note = make('p', 'draft-note', 'URLs open the linked document. Your saved drafts stay in this browser and can be resumed here.');
    const select = make('select', 'saved-work'); select.setAttribute('aria-label', 'Saved work');
    const preview = make('pre', 'draft-preview'), restore = make('button', 'restore-work', 'Resume selected draft');
    const close = make('button', 'close-drafts', 'Close'); close.onclick = () => dialog.close();
    let values = [];
    select.onchange = () => { preview.textContent = values[select.value] ? describe(values[select.value]) || '(empty document)' : 'No saved work in this browser.'; };
    button.onclick = () => {
      try { values = this.list(); } catch (_) { values = []; this.message.textContent = 'Saved work could not be read.'; }
      select.replaceChildren(...values.map((value, index) => {
        const option = document.createElement('option'); option.value = index;
        option.textContent = (index ? 'Previous: ' : 'Latest: ') + (describe(value).split('\n').find(line => line.trim()) || '(empty document)').slice(0, 100); return option;
      }));
      restore.disabled = !values.length; select.onchange(); dialog.showModal();
    };
    restore.onclick = async () => {
      if (!values[select.value]) return;
      restore.disabled = true;
      try { await onRestore(values[select.value]); dialog.close(); }
      catch (error) { preview.textContent = error.message; }
      finally { restore.disabled = false; }
    };
    dialog.append(title, note, select, preview, restore, close); document.body.append(dialog);
  }
}
if (typeof module !== 'undefined') module.exports = LocalDrafts; else globalThis.LocalDrafts = LocalDrafts;
})();
