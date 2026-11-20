import { element, createDialog, download } from '../ui/dialog.js';
import { bounded, MAX_BYTES } from '../core/bytes.js';
import { computeCID, isCID } from '../core/cid.js';
import { loadContent } from '../core/content.js';
import { LibraryError } from './backends.js';

const DECISIONS = Object.freeze({ import: 'Import', skip: 'Skip', 'merge-local': 'Merge, keeping the local head', 'merge-imported': 'Merge, using the imported head', copy: 'Import as a copy' });
const MODES = Object.freeze({
  'self-contained': 'Self-contained: every document’s contents inside the file',
  compact: 'Compact: contents already on 256t are referenced, new work is included',
  references: 'References only: every revision must already be published to 256t',
});
const formatBytes = size => size < 1024 ? `${size} B` : size < 1024 * 1024 ? `${(size / 1024).toFixed(1)} KiB` : `${(size / 1024 / 1024).toFixed(1)} MiB`;
const formatDate = iso => { try { return new Date(iso).toLocaleString(); } catch { return iso; } };
const excerpt = (value, limit = 90) => { const line = String(value ?? '').split('\n').find(Boolean)?.trim() ?? ''; return [...line].slice(0, limit).join(''); };

export class LibraryPanel {
  constructor({ library, store = null, urlState, getSnapshot, getFingerprint = () => JSON.stringify(getSnapshot()), onLoad,
    shell = null, container = null, drafts = null, maxBytes = MAX_BYTES, fetchSource = (...args) => globalThis.fetch(...args),
    onStatus = null, document = globalThis.document }) {
    Object.assign(this, { library, store, urlState, getSnapshot, getFingerprint, onLoad, shell, drafts, maxBytes, fetchSource, onStatus, document });
    this.bound = null;       // {id, head} of the entry this editor is bound to
    this.basedOn = null;     // revision the editor content was loaded/saved from
    this.saved = null;       // getFingerprint() at the last save or load
    this.revision = 0;       // guard for loads and async status
    this.rendered = 0;       // guard for list re-renders
    this.pendingDoc = null;  // document staged for Save as (drafts)
    this.publishing = false;
    if (document?.createElement) this.mount(container ?? shell?.toolbar ?? document.body);
    this.unsubscribe = library.subscribe?.(() => { this.refreshStatus(); this.refreshList(); }) ?? null;
  }
  mount(container) {
    const doc = this.document;
    this.saveButton = element('button', 'Save', { type: 'button', id: 'library-save' }, doc);
    this.saveAsButton = element('button', 'Save as…', { type: 'button', id: 'library-save-as' }, doc);
    this.openButton = element('button', 'Library', { type: 'button', id: 'library-open' }, doc);
    this.statusEl = element('span', '', { role: 'status', id: 'library-status', className: 'fk-library-status' }, doc);
    container.append(this.saveButton, this.saveAsButton, this.openButton, this.statusEl);
    this.saveButton.onclick = () => this.save();
    this.saveAsButton.onclick = () => this.openSaveAs();
    this.openButton.onclick = () => this.openLibraryDialog();
    this.refreshStatus();
  }
  status(message) { if (this.statusEl) this.statusEl.textContent = message; this.onStatus?.(message); }
  /** Recompute the bound-entry status. Safe to call on every edit. */
  refreshStatus() {
    if (!this.statusEl) return;
    if (!this.bound) { this.statusEl.textContent = ''; return; }
    this.statusEl.textContent = this.getFingerprint() === this.saved ? `Library: “${this.bound.name}”` : `Unsaved changes to “${this.bound.name}”`;
  }
  /** The consumer calls this after an explicit URL/CID load ({kind,source}) or another applied document
      ({record:false}, for drafts, examples and restores). Recording never blocks the load. */
  async opened(doc, { kind = 'link', source, record = true } = {}) {
    const revision = ++this.revision;
    this.saved = this.getFingerprint();
    try {
      const matches = record ? (await this.library.record(doc, { kind, cid: source })).matches : await this.library.match(doc);
      if (revision !== this.revision) return;
      const found = matches?.[0];
      if (found) { this.bound = { id: found.entry.id, head: found.entry.head, name: found.entry.name }; this.basedOn = found.revision.id; this.status(`Library: “${found.entry.name}” (matched)`); }
      else { this.bound = null; this.basedOn = null; this.refreshStatus(); }
    } catch { this.bound = null; this.basedOn = null; this.refreshStatus(); }
  }
  /** Explicit editor changes invalidate the saved fingerprint. */
  changed() { this.refreshStatus(); }
  /** Confirm/choice helper: resolves the chosen value, or null when dismissed. */
  choose({ title, message, choices }) {
    const doc = this.document, ui = createDialog(title, { document: doc });
    ui.body.append(element('p', message, {}, doc));
    return new Promise(resolve => {
      let settled = false;
      const settle = value => { if (!settled) { settled = true; ui.destroy(); resolve(value); } };
      for (const { label, value } of choices) {
        const button = element('button', label, { type: 'button' }, doc);
        button.onclick = () => settle(value); ui.body.append(button);
      }
      ui.dialog.addEventListener('close', () => settle(null));
      ui.open();
    });
  }
  async save() {
    if (this.publishing) return;
    if (!this.bound) { this.openSaveAs(); return; }
    const doc = this.getSnapshot();
    try {
      const result = await this.library.save({ doc, entry: this.bound.id, expectedHead: this.bound.head, parent: this.basedOn ?? this.bound.head });
      if (result.unchanged) { this.status('Already saved in the library.'); return; }
      this.bound = { id: result.entry.id, head: result.revision.id, name: result.entry.name };
      this.basedOn = result.revision.id; this.saved = this.getFingerprint(); this.refreshStatus();
      this.status(`Saved to “${result.entry.name}”.`);
    } catch (error) {
      if (error instanceof LibraryError && error.code === 'conflict') {
        const action = await this.choose({ title: 'Saved elsewhere', message: `${error.message} Saving anyway keeps both revisions in the history.`,
          choices: [{ label: 'Save anyway', value: 'save' }, { label: 'Save as a new document', value: 'as' }, { label: 'Cancel', value: null }] });
        if (action === 'save') await this.saveAnyway(doc, error.entry);
        else if (action === 'as') this.openSaveAs();
        return;
      }
      this.status(error.message);
    }
  }
  async saveAnyway(doc, entry) {
    try {
      // The other tab's head stays in history as a sibling branch.
      const result = await this.library.save({ doc, entry: entry.id, parent: this.basedOn ?? undefined });
      this.bound = { id: result.entry.id, head: result.revision.id, name: result.entry.name };
      this.basedOn = result.revision.id; this.saved = this.getFingerprint(); this.refreshStatus();
      this.status(`Saved to “${result.entry.name}”.`);
    } catch (error) { this.status(error.message); }
  }
  openSaveAs({ doc = null, name = '', description = '' } = {}) {
    const document = this.document;
    this.pendingDoc = doc;
    if (!this.saveAsDialog) {
      const ui = createDialog('Save to library', { id: 'library-save-as-dialog', document });
      this.saveAsDialog = ui;
      this.nameInput = element('input', null, { type: 'text', id: 'library-save-as-name', placeholder: 'Name (optional)', 'aria-label': 'Document name', maxlength: 120 }, document);
      this.descriptionInput = element('textarea', null, { id: 'library-save-as-description', placeholder: 'Description (optional)', 'aria-label': 'Document description', rows: 3 }, document);
      this.saveAsMessage = element('p', '', { role: 'status', id: 'library-save-as-status' }, document);
      this.saveAsConfirm = element('button', 'Save to library', { type: 'button', id: 'library-save-as-confirm' }, document);
      ui.body.append(
        element('p', 'Names and descriptions stay in this browser. They are shared only inside a library export you choose to make.', {}, document),
        this.nameInput, this.descriptionInput, this.saveAsMessage, this.saveAsConfirm);
      this.saveAsConfirm.onclick = () => this.commitSaveAs();
    }
    this.nameInput.value = name; this.descriptionInput.value = description; this.saveAsMessage.textContent = '';
    this.saveAsConfirm.disabled = false; this.saveAsDialog.open();
    this.nameInput.focus();
  }
  async commitSaveAs() {
    if (this.saveAsConfirm.disabled) return;
    const doc = this.pendingDoc ?? this.getSnapshot(), fromEditor = !this.pendingDoc;
    this.saveAsConfirm.disabled = true;
    try {
      const { entry } = await this.library.saveAs({ doc, name: this.nameInput.value, description: this.descriptionInput.value });
      this.pendingDoc = null; this.saveAsDialog.dialog.close();
      if (fromEditor) { this.bound = { id: entry.id, head: entry.head, name: entry.name }; this.basedOn = entry.head; this.saved = this.getFingerprint(); }
      this.refreshStatus(); this.status(`Saved as “${entry.name}”.`);
    } catch (error) {
      this.saveAsConfirm.disabled = false;
      if (error instanceof LibraryError && error.code === 'exists' && error.entry) {
        const existing = error.entry;
        const action = await this.choose({ title: 'Name already used', message: `“${existing.name}” already exists. Add this as a new revision of that document?`,
          choices: [{ label: `Add revision to “${existing.name}”`, value: 'add' }, { label: 'Choose another name', value: null }] });
        if (action !== 'add') return;
        try {
          if (this.descriptionInput.value) await this.library.update(existing.id, { description: this.descriptionInput.value });
          const result = await this.library.save({ doc, entry: existing.id, expectedHead: existing.head, parent: existing.head });
          this.pendingDoc = null; this.saveAsDialog.dialog.close();
          if (fromEditor) { this.bound = { id: existing.id, head: result.revision.id, name: existing.name }; this.basedOn = result.revision.id; this.saved = this.getFingerprint(); }
          this.refreshStatus(); this.status(`Saved to “${existing.name}”.`);
        } catch (second) { this.saveAsMessage.textContent = second.message; }
        return;
      }
      this.saveAsMessage.textContent = error.message;
    }
  }
  /** Load a revision explicitly through the consumer's onLoad guard, then bind to its entry. */
  async load(revisionId) {
    const revision = ++this.revision;
    this.status('Loading from the library…');
    try {
      const { doc, revision: row, entry } = await this.library.load(revisionId);
      if (revision !== this.revision) return;
      await this.onLoad(doc, { entry, revision: row });
      if (revision !== this.revision) return;
      this.bound = { id: entry.id, head: entry.head, name: entry.name };
      this.basedOn = row.id; this.saved = this.getFingerprint(); this.refreshStatus();
      this.status(`Opened “${entry.name}”.`);
    } catch (error) { if (revision === this.revision) this.status(error.message); }
  }
  cancelLoad() { this.revision++; this.refreshStatus(); }
  /** Handle a detached HashBin result ({kind:'library'|'revision'}); wire to HashBinPanel's onDetached. */
  async published(result) {
    if (!result) return;
    try {
      if (result.error) { this.status(result.error); return; }
      if (result.kind === 'revision' && result.cid) await this.library.markPublished(result.cid);
      this.status(result.kind === 'library' ? 'Library exported to HashBin.' : 'Revision saved to HashBin.');
      this.refreshList();
    } catch (error) { this.status(error.message); }
  }
  /** Arm a button so the following click publishes synchronously (popup-safe). */
  armPublish(button, context) {
    button.textContent = 'Approve on HashBin'; button.disabled = false;
    button.onclick = () => {
      if (this.publishing) return;
      try {
        const pending = this.store.publish(context.payload, this.getSnapshot(),
          { kind: context.kind, cid: context.cid, fileName: context.fileName, contentType: context.contentType });
        this.publishing = true; button.disabled = true; this.status('Waiting for your approval on HashBin…');
        pending.then(async result => {
          if (result.redirected) return; // the redirect callback finishes through published()
          if (context.kind === 'revision') await this.library.markPublished(result.cid);
          this.status(context.kind === 'library' ? 'Library exported to HashBin.' : 'Revision saved to HashBin.');
          button.disabled = false; button.textContent = context.kind === 'library' ? 'Publish to HashBin' : 'Publish to 256t';
          this.refreshList();
        }, error => { this.status(error.message); button.disabled = false; button.textContent = context.kind === 'library' ? 'Publish to HashBin' : 'Publish to 256t'; })
          .finally(() => { this.publishing = false; });
      } catch (error) { this.status(error.message); }
    };
  }
  /** First click prepares (loads bytes, initializes the SDK); the next click publishes. */
  prepareRevisionPublish(button, revisionId) {
    button.disabled = true;
    Promise.resolve().then(async () => {
      const { text, revision } = await this.library.load(revisionId);
      if (await computeCID(text) !== revision.cid) throw new LibraryError('damaged', 'This stored revision is damaged and cannot be published.');
      await this.store.init();
      this.armPublish(button, { kind: 'revision', payload: text, cid: revision.cid });
    }).catch(error => { this.status(error.message); button.disabled = false; });
  }
  /* Library browser -------------------------------------------------- */
  openLibraryDialog() {
    const document = this.document;
    if (!this.libraryDialog) {
      this.libraryDialog = createDialog('Library', { id: 'library-dialog', document });
      this.libraryView = element('div', null, { className: 'fk-library-list', id: 'library-list' }, document);
      this.libraryDialog.body.append(this.libraryView);
    }
    this.libraryDialog.open();
    void this.renderList();
  }
  refreshList() {
    if (!this.libraryDialog?.dialog?.open) return;
    if (this.view?.kind === 'history') void this.renderHistory(this.view.entry);
    else void this.renderList();
  }
  async renderList() {
    const document = this.document, rendered = ++this.rendered;
    this.view = { kind: 'list' };
    try {
      const [entries, recent, usage] = await Promise.all([this.library.entries(), this.library.recent(), this.library.usage()]);
      if (rendered !== this.rendered || !this.libraryDialog?.dialog?.open) return;
      const view = this.libraryView; view.replaceChildren();
      const header = element('div', null, { className: 'fk-library-actions' }, document);
      const exportButton = element('button', 'Export…', { type: 'button', id: 'library-export-open' }, document);
      const importButton = element('button', 'Import…', { type: 'button', id: 'library-import-open' }, document);
      exportButton.onclick = () => this.openExport(entries); importButton.onclick = () => this.openImport();
      header.append(exportButton, importButton);
      const usageLine = element('p', '', { className: 'fk-library-usage' }, document);
      const parts = [`${entries.length} document${entries.length === 1 ? '' : 's'}`, `${usage.revisions} revisions`, formatBytes(usage.bytes)];
      if (usage.missing) parts.push(`${usage.missing} kept on 256t`);
      usageLine.textContent = parts.join(' · ');
      if (usage.persisted === false) usageLine.textContent += ' — the browser may evict it under storage pressure; export to keep it safe';
      header.append(usageLine);
      if (usage.missing) {
        const fetchAll = element('button', 'Fetch all from 256t', { type: 'button', id: 'library-fetch-all' }, document);
        fetchAll.onclick = () => this.fetchAll(fetchAll);
        header.append(fetchAll);
      }
      if (usage.persisted === false) {
        const keep = element('button', 'Ask to keep on this device', { type: 'button', id: 'library-persist' }, document);
        keep.onclick = async () => { keep.disabled = true; try { this.status(await this.library.persist() ? 'This browser will keep the library.' : 'The browser did not grant persistent storage. Export to keep the library safe.'); } finally { keep.disabled = false; } };
        header.append(keep);
      }
      view.append(header);
      const list = element('div', null, { className: 'fk-entries' }, document);
      if (!entries.length) list.append(element('p', 'Nothing saved yet. “Save as…” keeps a named copy in this browser.', {}, document));
      for (const entry of entries) list.append(this.entryCard(entry));
      view.append(list);
      if (this.drafts) view.append(this.draftsSection());
      view.append(this.recentSection(recent));
    } catch (error) { this.status(error.message); }
  }
  entryCard(entry) {
    const document = this.document, card = element('div', null, { className: 'fk-entry' }, document);
    const title = element('div', null, { className: 'fk-entry-title' }, document);
    title.append(element('strong', entry.name, {}, document));
    card.append(title);
    const description = excerpt(entry.description, 140);
    if (description) card.append(element('p', description, { className: 'fk-entry-description' }, document));
    card.append(element('p', `${entry.count} revision${entry.count === 1 ? '' : 's'} · updated ${formatDate(entry.updated)}`, { className: 'fk-entry-meta' }, document));
    const actions = element('div', null, { className: 'fk-entry-actions' }, document);
    const open = element('button', 'Open', { type: 'button' }, document);
    open.onclick = () => { this.libraryDialog.dialog.close(); void this.load(entry.head); };
    const history = element('button', 'History', { type: 'button' }, document);
    history.onclick = () => this.renderHistory(entry);
    const details = element('button', 'Details', { type: 'button' }, document);
    details.onclick = () => this.openDetails(entry);
    const remove = element('button', 'Delete', { type: 'button' }, document);
    remove.onclick = async () => {
      const ok = await this.choose({ title: 'Delete document', message: `Delete “${entry.name}” and its ${entry.count} saved revision${entry.count === 1 ? '' : 's'} from this browser? This cannot be undone.`,
        choices: [{ label: 'Delete', value: true }, { label: 'Keep', value: false }] });
      if (!ok) return;
      try {
        await this.library.remove(entry.id);
        if (this.bound?.id === entry.id) { this.bound = null; this.basedOn = null; this.refreshStatus(); }
        this.status(`Deleted “${entry.name}”.`); this.refreshList();
      } catch (error) { this.status(error.message); }
    };
    actions.append(open, history, details, remove); card.append(actions);
    return card;
  }
  openDetails(entry) {
    const document = this.document;
    if (!this.detailsDialog) {
      this.detailsDialog = createDialog('Document details', { id: 'library-details-dialog', document });
      this.detailsName = element('input', null, { type: 'text', id: 'library-details-name', 'aria-label': 'Document name', maxlength: 120 }, document);
      this.detailsDescription = element('textarea', null, { id: 'library-details-description', 'aria-label': 'Document description', rows: 4 }, document);
      this.detailsMessage = element('p', '', { role: 'status' }, document);
      this.detailsConfirm = element('button', 'Save details', { type: 'button', id: 'library-details-confirm' }, document);
      this.detailsDialog.body.append(
        element('p', 'Names and descriptions stay in this browser. Changing them does not add a revision. An empty name is generated again.', {}, document),
        this.detailsName, this.detailsDescription, this.detailsMessage, this.detailsConfirm);
    }
    this.detailsName.value = entry.name; this.detailsDescription.value = entry.description; this.detailsMessage.textContent = '';
    this.detailsConfirm.onclick = async () => {
      this.detailsConfirm.disabled = true;
      try {
        const updated = await this.library.update(entry.id, { name: this.detailsName.value, description: this.detailsDescription.value });
        if (this.bound?.id === entry.id) { this.bound.name = updated.name; this.refreshStatus(); }
        this.detailsDialog.dialog.close(); this.status('Details saved.'); this.refreshList();
      } catch (error) { this.detailsMessage.textContent = error.message; }
      finally { this.detailsConfirm.disabled = false; }
    };
    this.detailsDialog.open(); this.detailsName.focus();
  }
  async renderHistory(entry) {
    const document = this.document, rendered = ++this.rendered;
    this.view = { kind: 'history', entry };
    try {
      const rows = await this.library.history(entry.id);
      if (rendered !== this.rendered || !this.libraryDialog?.dialog?.open) return;
      const view = this.libraryView; view.replaceChildren();
      const back = element('button', '← Back', { type: 'button' }, document);
      back.onclick = () => this.renderList();
      view.append(back, element('h3', `History of “${entry.name}”`, {}, document));
      for (const row of rows) {
        const card = element('div', null, { className: 'fk-entry' }, document);
        const title = element('div', null, { className: 'fk-entry-title' }, document);
        title.append(element('strong', row.title || 'Untitled', {}, document));
        for (const badge of [
          row.head ? 'current' : null, row.kind === 'import' ? 'imported' : null,
          row.stored === false ? 'on 256t only' : null, row.publishedAt ? 'published' : null].filter(Boolean)) {
          title.append(' ', element('span', badge, { className: 'fk-badge' }, document));
        }
        card.append(title, element('p', `${formatDate(row.savedAt)} · ${formatBytes(row.size ?? 0)}`, { className: 'fk-entry-meta' }, document));
        const actions = element('div', null, { className: 'fk-entry-actions' }, document);
        const open = element('button', 'Open', { type: 'button' }, document);
        open.onclick = () => { this.libraryDialog.dialog.close(); void this.load(row.id); };
        actions.append(open);
        if (this.store?.clientId && !row.publishedAt) {
          const publish = element('button', 'Publish to 256t', { type: 'button' }, document);
          publish.onclick = () => this.prepareRevisionPublish(publish, row.id);
          actions.append(publish);
        }
        if (!row.head) {
          const remove = element('button', 'Delete', { type: 'button' }, document);
          remove.onclick = async () => {
            const ok = await this.choose({ title: 'Delete revision', message: 'Delete this revision from the history? This cannot be undone.',
              choices: [{ label: 'Delete', value: true }, { label: 'Keep', value: false }] });
            if (!ok) return;
            try { await this.library.removeRevision(row.id); this.renderHistory(entry); }
            catch (error) { this.status(error.message); }
          };
          actions.append(remove);
        }
        card.append(actions); view.append(card);
      }
    } catch (error) { this.status(error.message); }
  }
  recentSection(recent) {
    const document = this.document, section = element('div', null, { className: 'fk-recent' }, document);
    section.append(element('h3', 'Recently opened', {}, document));
    if (!recent.length) { section.append(element('p', 'Links and CIDs you open appear here.', {}, document)); return section; }
    const clear = element('button', 'Clear list', { type: 'button', id: 'library-clear-recent' }, document);
    clear.onclick = async () => { try { await this.library.clearRecent(); this.refreshList(); } catch (error) { this.status(error.message); } };
    for (const row of recent) {
      const card = element('div', null, { className: 'fk-entry' }, document);
      const match = row.matches?.[0];
      const meta = [`opened ${formatDate(row.openedAt)}`, row.kind === 'cid' ? 'CID' : 'link', match ? `saved as “${match.entry.name}”` : null].filter(Boolean).join(' · ');
      card.append(element('p', row.title || `${row.cid.slice(0, 18)}…`, { className: 'fk-entry-title' }, document),
        element('p', meta, { className: 'fk-entry-meta' }, document));
      const open = element('button', 'Open', { type: 'button' }, document);
      open.onclick = async () => {
        try {
          const { doc, recent: item } = await this.library.openRecent(row.id);
          this.libraryDialog.dialog.close();
          const revision = ++this.revision;
          await this.onLoad(doc, { recent: item });
          if (revision !== this.revision) return;
          const found = item.cid ? (await this.library.match(item.cid))[0] : null;
          if (found) { this.bound = { id: found.entry.id, head: found.entry.head, name: found.entry.name }; this.basedOn = found.revision.id; }
          else { this.bound = null; this.basedOn = null; }
          this.saved = this.getFingerprint(); this.refreshStatus();
        } catch (error) { this.status(error.message); }
      };
      const actions = element('div', null, { className: 'fk-entry-actions' }, document);
      actions.append(open); card.append(actions); section.append(card);
    }
    section.append(clear);
    return section;
  }
  draftsSection() {
    const document = this.document, section = element('div', null, { className: 'fk-drafts' }, document);
    let values = [];
    try { values = this.drafts.list(); } catch { values = []; }
    if (!values.length) return section;
    section.append(element('h3', 'Saved drafts', {}, document));
    values.forEach((doc, index) => {
      const save = element('button', `Save draft ${index + 1} to library`, { type: 'button' }, document);
      const label = excerpt(this.library.describe?.(doc), 60);
      if (label) save.textContent += ` — ${label}`;
      save.onclick = () => this.openSaveAs({ doc });
      section.append(save);
    });
    return section;
  }
  async fetchAll(button) {
    button.disabled = true;
    try {
      const result = await this.library.fetchMissing({ onProgress: ({ done, total }) => { this.status(`Fetched ${done} of ${total} from 256t…`); } });
      this.status(result.failed.length ? `Fetched ${result.fetched} of ${result.total}; ${result.failed.length} could not be fetched.` : `Fetched ${result.fetched} from 256t.`);
      this.refreshList();
    } catch (error) { this.status(error.message); }
    finally { button.disabled = false; }
  }
  /* Export ------------------------------------------------------------ */
  openExport(entries) {
    const document = this.document;
    if (!this.exportDialog) {
      this.exportDialog = createDialog('Export library', { id: 'library-export-dialog', document });
      const body = this.exportDialog.body;
      body.append(element('p', 'An export contains the document contents you select plus the names, descriptions and timestamps kept here. Anyone with the file or CID can read them. Publishing sends the export to hashbin.org and stores it on 256t.us.', {}, document));
      this.exportScope = element('div', null, { className: 'fk-export-scope', id: 'library-export-scope' }, document);
      this.exportModes = element('div', null, { className: 'fk-export-modes', role: 'radiogroup', 'aria-label': 'Export form' }, document);
      for (const [value, label] of Object.entries(MODES)) {
        const radio = element('input', null, { type: 'radio', name: 'library-export-mode', value, id: `library-export-mode-${value}` }, document);
        radio.checked = value === 'self-contained';
        const item = element('label', null, {}, document);
        item.append(radio, document.createTextNode(label));
        this.exportModes.append(item);
        radio.onchange = () => this.disarmExport();
      }
      this.exportMessage = element('p', '', { role: 'status', id: 'library-export-status' }, document);
      this.exportMissing = element('div', null, { className: 'fk-missing' }, document);
      this.downloadButton = element('button', 'Download file', { type: 'button', id: 'library-export-download' }, document);
      this.publishButton = element('button', 'Publish to HashBin', { type: 'button', id: 'library-export-publish' }, document);
      this.downloadButton.onclick = () => this.downloadExport();
      this.publishButton.onclick = () => this.prepareExportPublish();
      if (!this.store?.clientId) this.publishButton.hidden = true;
      body.append(this.exportScope, this.exportModes, this.exportMessage, this.exportMissing, this.downloadButton, this.publishButton);
    }
    this.exportScope.replaceChildren(...entries.map(entry => {
      const box = element('input', null, { type: 'checkbox', value: entry.id, id: `library-export-entry-${entry.id}` }, document);
      box.checked = true; box.onchange = () => this.disarmExport();
      const item = element('label', null, {}, document);
      item.append(box, document.createTextNode(entry.name));
      return item;
    }));
    this.exportMessage.textContent = ''; this.exportMissing.replaceChildren(); this.disarmExport();
    this.exportDialog.open();
  }
  exportSelection() {
    const selected = [...this.exportScope.querySelectorAll('input[type="checkbox"]')].filter(box => box.checked).map(box => box.value);
    const mode = this.exportModes.querySelector('input[type="radio"]:checked')?.value ?? 'self-contained';
    return { selected, mode };
  }
  disarmExport() { this.exportArmed = null; if (this.publishButton) { this.publishButton.textContent = 'Publish to HashBin'; this.publishButton.disabled = false; } }
  async downloadExport(omitUnpublished = false) {
    const { selected, mode } = this.exportSelection();
    try {
      const result = await this.library.exportCatalog({ mode, entries: selected, omitUnpublished });
      download(new Blob([result.payload], { type: 'application/json' }), result.fileName);
      this.exportMessage.textContent = `Downloaded ${result.entries} document${result.entries === 1 ? '' : 's'} (${formatBytes(result.bytes)}).`;
    } catch (error) { this.showExportError(error, omitUnpublished); }
  }
  async prepareExportPublish(omitUnpublished = false) {
    if (this.exportArmed) return;
    this.publishButton.disabled = true; this.exportMessage.textContent = 'Preparing the export…';
    const { selected, mode } = this.exportSelection();
    try {
      const [result] = await Promise.all([this.library.exportCatalog({ mode, entries: selected, omitUnpublished }), this.store.init()]);
      const cid = await computeCID(result.payload);
      this.exportMissing.replaceChildren();
      this.exportMessage.textContent = `${result.entries} document${result.entries === 1 ? '' : 's'}, ${formatBytes(result.bytes)}. HashBin shows the retention and exact price; you approve on hashbin.org.`;
      this.exportArmed = { kind: 'library', payload: result.payload, cid, fileName: result.fileName, contentType: result.contentType };
      this.armPublish(this.publishButton, this.exportArmed);
    } catch (error) { this.publishButton.disabled = false; this.exportMessage.textContent = ''; this.showExportError(error, omitUnpublished); }
  }
  async showExportError(error, omitUnpublished) {
    if (error instanceof LibraryError && error.code === 'unpublished' && error.missing) {
      this.exportMessage.textContent = error.message;
      const list = this.exportMissing; list.replaceChildren();
      list.append(element('p', 'Publish each revision first (one approval each), or export without them:', {}, this.document));
      for (const item of error.missing) {
        const row = element('div', null, { className: 'fk-entry' }, this.document);
        row.append(element('p', `${item.name} — revision from ${formatDate(item.savedAt)}`, { className: 'fk-entry-meta' }, this.document));
        if (this.store?.clientId) {
          const publish = element('button', 'Publish to 256t', { type: 'button' }, this.document);
          publish.onclick = () => this.prepareRevisionPublish(publish, item.revision);
          row.append(publish);
        }
        list.append(row);
      }
      const omit = element('button', 'Export without them', { type: 'button', id: 'library-export-omit' }, this.document);
      omit.onclick = () => this.downloadExport(true);
      const omitPublish = element('button', 'Publish export without them', { type: 'button', id: 'library-export-omit-publish' }, this.document);
      omitPublish.onclick = () => this.prepareExportPublish(true);
      list.append(omit, omitPublish);
      return;
    }
    if (error instanceof LibraryError && error.code === 'too-large' && error.breakdown) {
      this.exportMessage.textContent = error.message;
      this.exportMissing.replaceChildren(...error.breakdown.map(row => element('p', `${row.name} — ${formatBytes(row.bytes)}`, { className: 'fk-entry-meta' }, this.document)));
      return;
    }
    this.exportMessage.textContent = error.message;
  }
  /* Import ------------------------------------------------------------ */
  openImport() {
    const document = this.document;
    if (!this.importDialog) {
      this.importDialog = createDialog('Import library', { id: 'library-import-dialog', document });
      const body = this.importDialog.body;
      body.append(element('p', 'Import an export made on another device, browser or deployment. Contents are verified before anything is written.', {}, document));
      this.importInput = element('input', null, { type: 'text', id: 'library-import-cid', placeholder: 'CID or 256t link', 'aria-label': 'Export CID or link' }, document);
      this.importFile = element('input', null, { type: 'file', id: 'library-import-file', accept: '.json,application/json', 'aria-label': 'Export file' }, document);
      this.importPreview = element('button', 'Preview', { type: 'button', id: 'library-import-preview' }, document);
      this.importMessage = element('p', '', { role: 'status', id: 'library-import-status' }, document);
      this.importArea = element('div', null, { className: 'fk-import-preview' }, document);
      this.importCommit = element('button', 'Import', { type: 'button', id: 'library-import-commit' }, document);
      this.importCommit.hidden = true;
      this.importPreview.onclick = () => this.previewImport();
      this.importCommit.onclick = () => this.commitImport();
      body.append(this.importInput, this.importFile, this.importPreview, this.importMessage, this.importArea, this.importCommit);
    }
    this.importMessage.textContent = ''; this.importArea.replaceChildren(); this.importCommit.hidden = true; this.pendingImport = null;
    this.importDialog.open();
  }
  async previewImport() {
    const revision = ++this.rendered;
    this.importMessage.textContent = 'Reading the export…'; this.importCommit.hidden = true; this.importArea.replaceChildren();
    try {
      const file = this.importFile.files?.[0], value = this.importInput.value.trim();
      let input;
      if (file) input = bounded(new Uint8Array(await file.arrayBuffer()), this.maxBytes);
      else if (value) {
        const cid = this.store?.cid(value) ?? (isCID(value) ? value : null);
        if (!cid) throw new LibraryError('invalid', 'Enter a valid export CID or 256t link, or choose a file.');
        input = await loadContent(cid, { maxBytes: this.maxBytes, fetchSource: this.fetchSource });
      } else throw new LibraryError('invalid', 'Enter an export CID or choose a file.');
      const preview = await this.library.previewImport(input);
      if (revision !== this.rendered) return;
      this.pendingImport = preview;
      this.renderImportPreview(preview);
      this.importMessage.textContent = `Export from ${preview.app ?? 'this app'} made ${formatDate(preview.exportedAt)} (${preview.mode}). Review it, then import.`;
    } catch (error) { if (revision === this.rendered) this.importMessage.textContent = error.message; }
  }
  renderImportPreview(preview) {
    const document = this.document, area = this.importArea; area.replaceChildren();
    for (const item of preview.entries) {
      const row = element('div', null, { className: 'fk-entry' }, document);
      const meta = [`${item.revisions} revision${item.revisions === 1 ? '' : 's'}`];
      if (item.added) meta.push(`${item.added} new`);
      if (item.remote) meta.push(`${item.remote} kept on 256t`);
      const labels = { new: 'New', same: 'Identical', conflict: 'Conflicts with a local document' };
      row.append(element('p', `${item.name || 'Untitled'} — ${labels[item.status]}`, { className: 'fk-entry-title' }, document),
        element('p', meta.join(' · '), { className: 'fk-entry-meta' }, document));
      const select = element('select', null, { 'aria-label': `What to do with ${item.name || 'Untitled'}`, 'data-index': item.index }, document);
      const choices = { new: ['import', 'skip'], same: ['skip', 'merge-local', 'merge-imported', 'copy'], conflict: ['merge-local', 'merge-imported', 'copy', 'skip'] }[item.status];
      for (const choice of choices) select.append(element('option', DECISIONS[choice], { value: choice }, document));
      if (item.status === 'conflict') select.prepend(element('option', 'Choose…', { value: '', disabled: true, selected: true }, document));
      row.append(select); area.append(row);
    }
    if (!preview.entries.length) area.append(element('p', 'The export lists no documents.', {}, document));
    this.importCommit.hidden = !preview.entries.length;
  }
  async commitImport() {
    if (this.importCommit.disabled || !this.pendingImport) return;
    const decisions = {};
    for (const select of this.importArea.querySelectorAll('select[data-index]')) decisions[select.dataset.index] = select.value;
    this.importCommit.disabled = true;
    try {
      const result = await this.library.commitImport(this.pendingImport, decisions);
      this.importMessage.textContent = `Imported ${result.entries} document${result.entries === 1 ? '' : 's'} (${result.revisions} revision${result.revisions === 1 ? '' : 's'}${result.remote ? `, ${result.remote} kept on 256t` : ''}).`;
      this.pendingImport = null; this.importArea.replaceChildren(); this.refreshList();
      if (result.remote) {
        const fetchAll = element('button', 'Fetch all from 256t now', { type: 'button', id: 'library-import-fetch' }, this.document);
        fetchAll.onclick = () => this.fetchAll(fetchAll);
        this.importArea.append(fetchAll);
      }
    } catch (error) {
      this.importMessage.textContent = error.message;
      if (error.code === 'changed' || error.code === 'invalid') this.pendingImport = null;
    } finally { this.importCommit.disabled = false; }
  }
  destroy() {
    this.unsubscribe?.(); this.revision++;
    for (const ui of [this.saveAsDialog, this.detailsDialog, this.libraryDialog, this.exportDialog, this.importDialog]) ui?.destroy?.();
    for (const node of [this.saveButton, this.saveAsButton, this.openButton, this.statusEl]) node?.remove?.();
  }
}

export function createLibraryPanel(options) { return new LibraryPanel(options); }
