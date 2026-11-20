import { bytes, text as decodeText } from '../core/bytes.js';
import { cidLength, computeCID, isCID } from '../core/cid.js';
import { loadContent } from '../core/content.js';
import { createDocuments } from '../core/envelope.js';
import { CATALOG_FORMAT, CATALOG_MODES, parseCatalog } from './catalog.js';
import { LibraryError, indexedDBBackend } from './backends.js';
import { LIBRARY_LIMITS, cleanName, cleanDescription, nameKey, suggestName } from './names.js';

export { LibraryError };
export const LIBRARY_SCHEMA = Object.freeze({ version: 1, stores: {
  entries: { key: 'id', indexes: { nameKey: { path: 'nameKey', unique: true } } },
  revisions: { key: 'id', indexes: { entry: { path: 'entry' }, cid: { path: 'cid' } } },
  blobs: { key: 'cid' },
  recent: { key: 'id', indexes: { cid: { path: 'cid' } } },
} });
const ALL = Object.keys(LIBRARY_SCHEMA.stores);
const publicEntry = entry => { const { nameKey: _, ...rest } = entry; return rest; };
const newest = (a, b) => (b.savedAt ?? b.openedAt).localeCompare(a.savedAt ?? a.openedAt) || b.id.localeCompare(a.id);

function translate(error) {
  if (error instanceof LibraryError) return error;
  if (error?.name === 'QuotaExceededError') return new LibraryError('quota', 'This browser is out of space for the library. Export or delete older revisions, then try again.');
  return new LibraryError('storage', `The local library could not be updated (${error?.name ?? 'Error'}).`);
}

export const IMPORT_CHOICES = Object.freeze({ new: ['import', 'skip'], conflict: ['merge-local', 'merge-imported', 'copy', 'skip'], same: ['skip', 'merge-local', 'merge-imported', 'copy'] });

export async function openLibrary({ config, type, backend, describe = doc => doc.src, now = () => Date.now(), id = () => crypto.randomUUID(), channel,
  storageManager = globalThis.navigator?.storage, fetchSource = (...args) => globalThis.fetch(...args) }) {
  const documents = createDocuments(type, config.maxBytes), prefix = config.storagePrefix, previews = new WeakMap();
  const app = typeof config.slug === 'string' && /^[a-z0-9][a-z0-9-]{0,63}$/.test(config.slug) ? config.slug : null;
  const db = await (backend ?? indexedDBBackend({ name: `${prefix}:library` })).open(LIBRARY_SCHEMA);
  const listeners = new Set();
  const broadcast = channel !== undefined ? channel : typeof BroadcastChannel === 'function' ? new BroadcastChannel(`${prefix}:library`) : null;
  const notify = () => { for (const listener of listeners) { try { listener(); } catch { /* listeners own their errors */ } } };
  if (broadcast) broadcast.onmessage = notify;
  let last = 0;
  const clock = () => { last = Math.max(now(), last + 1); return new Date(last).toISOString(); };
  const read = (stores, work) => db.transaction(stores, 'readonly', work).catch(error => { throw translate(error); });
  async function write(stores, work) {
    let result;
    try { result = await db.transaction(stores, 'readwrite', work); } catch (error) { throw translate(error); }
    notify(); try { broadcast?.postMessage('changed'); } catch { /* other tabs refresh on focus */ }
    return result;
  }
  async function prepare(doc) {
    const text = documents.serialize(doc);
    return { text, cid: await computeCID(text), size: bytes(text).length, doc: documents.parse(text) };
  }
  async function storeBlob(ops, item) { if (!await ops.get('blobs', item.cid)) await ops.put('blobs', { cid: item.cid, text: item.text, size: item.size }); }
  async function addRevision(ops, entry, item, parent, kind) {
    await storeBlob(ops, item);
    const revision = { id: id(), entry: entry.id, cid: item.cid, parent: parent ?? null, savedAt: clock(), kind, size: item.size, title: suggestName(item.doc, describe) };
    await ops.put('revisions', revision);
    Object.assign(entry, { head: revision.id, updated: revision.savedAt }); await ops.put('entries', entry);
    return revision;
  }
  async function freeName(ops, base, except) {
    for (let n = 1; ; n++) {
      const candidate = n === 1 ? base : `${base} ${n}`, [row] = await ops.index('entries', 'nameKey', nameKey(candidate));
      if (!row || row.id === except) return candidate;
    }
  }
  async function claim(ops, name, except) {
    const [existing] = await ops.index('entries', 'nameKey', nameKey(name));
    if (existing && existing.id !== except) throw new LibraryError('exists', `“${existing.name}” already exists.`, { entry: publicEntry(existing) });
  }
  async function collect(ops, cids) {
    for (const cid of new Set(cids)) {
      if (!(await ops.index('revisions', 'cid', cid)).length && !(await ops.index('recent', 'cid', cid)).length) await ops.delete('blobs', cid);
    }
  }
  async function matches(ops, cid) {
    const revisions = (await ops.index('revisions', 'cid', cid)).sort(newest), result = [];
    for (const revision of revisions) { const entry = await ops.get('entries', revision.entry); if (entry) result.push({ entry: publicEntry(entry), revision }); }
    return result;
  }
  async function fetchBlob(cid, signal) {
    // Only referenced (published) revisions reach the network, and only from an explicit load.
    const content = await loadContent(cid, { maxBytes: config.maxBytes, fetchSource, signal }), text = decodeText(content);
    documents.parse(text);
    await write(['blobs'], ops => storeBlob(ops, { cid, text, size: content.length }));
    return text;
  }
  async function contents(cid, { signal, remote = false } = {}) {
    const blob = await read(['blobs'], ops => ops.get('blobs', cid));
    if (!blob && !remote) throw new LibraryError('missing', 'This revision is not stored in this browser.', { cid });
    const text = blob ? blob.text : await fetchBlob(cid, signal).catch(error => { throw new LibraryError('missing', `This revision is not stored in this browser and could not be fetched: ${error.message}`, { cid }); });
    if (await computeCID(text) !== cid) throw new LibraryError('damaged', 'This stored revision is damaged and cannot be opened.', { cid });
    return { doc: documents.parse(text), text };
  }

  return Object.freeze({
    documents, describe,
    async entries() {
      return read(['entries', 'revisions'], async ops => {
        const counts = new Map();
        for (const revision of await ops.all('revisions')) counts.set(revision.entry, (counts.get(revision.entry) ?? 0) + 1);
        return (await ops.all('entries')).map(entry => ({ ...publicEntry(entry), count: counts.get(entry.id) ?? 0 }))
          .sort((a, b) => b.updated.localeCompare(a.updated) || a.name.localeCompare(b.name));
      });
    },
    async entry(entryId) { const entry = await read(['entries'], ops => ops.get('entries', entryId)); return entry ? publicEntry(entry) : null; },
    async history(entryId) {
      return read(['entries', 'revisions', 'blobs'], async ops => {
        const entry = await ops.get('entries', entryId);
        if (!entry) throw new LibraryError('missing', 'This saved document no longer exists in this browser.');
        const stored = new Set(await ops.keys('blobs'));
        return (await ops.index('revisions', 'entry', entryId)).sort(newest).map(revision => ({ ...revision, head: revision.id === entry.head, stored: stored.has(revision.cid) }));
      });
    },
    async load(revisionId, { signal } = {}) {
      const found = await read(['entries', 'revisions'], async ops => {
        const revision = await ops.get('revisions', revisionId);
        return revision && { revision, entry: await ops.get('entries', revision.entry) };
      });
      if (!found?.entry) throw new LibraryError('missing', 'This revision no longer exists in this browser.');
      const { doc, text } = await contents(found.revision.cid, { signal, remote: true });
      return { doc, text, revision: found.revision, entry: publicEntry(found.entry) };
    },
    async save({ doc, entry: entryId, parent, expectedHead }) {
      const item = await prepare(doc);
      return write(['entries', 'revisions', 'blobs'], async ops => {
        const entry = await ops.get('entries', entryId);
        if (!entry) throw new LibraryError('missing', 'This saved document no longer exists in this browser.');
        if (expectedHead !== undefined && entry.head !== expectedHead) throw new LibraryError('conflict', `“${entry.name}” was saved again elsewhere since you opened it.`, { entry: publicEntry(entry) });
        const head = await ops.get('revisions', entry.head);
        if (head?.cid === item.cid) return { entry: publicEntry(entry), revision: head, unchanged: true };
        const revision = await addRevision(ops, entry, item, parent === undefined ? entry.head : parent, 'save');
        return { entry: publicEntry(entry), revision, unchanged: false };
      });
    },
    async saveAs({ doc, name, description, parent = null }) {
      const item = await prepare(doc), wanted = cleanName(name), text = cleanDescription(description);
      return write(['entries', 'revisions', 'blobs'], async ops => {
        if (wanted) await claim(ops, wanted);
        const final = wanted || await freeName(ops, suggestName(item.doc, describe)), at = clock();
        const entry = { id: id(), name: final, nameKey: nameKey(final), nameGenerated: !wanted, description: text, created: at, updated: at, head: null };
        const revision = await addRevision(ops, entry, item, parent, 'save');
        return { entry: publicEntry(entry), revision };
      });
    },
    async update(entryId, { name, description } = {}) {
      const wanted = name === undefined ? undefined : cleanName(name), text = description === undefined ? undefined : cleanDescription(description);
      return write(['entries', 'revisions', 'blobs'], async ops => {
        const entry = await ops.get('entries', entryId);
        if (!entry) throw new LibraryError('missing', 'This saved document no longer exists in this browser.');
        if (wanted) { await claim(ops, wanted, entry.id); Object.assign(entry, { name: wanted, nameGenerated: false }); }
        else if (wanted === '') {
          const head = await ops.get('revisions', entry.head), blob = head && await ops.get('blobs', head.cid);
          let doc = null; try { doc = blob && documents.parse(blob.text); } catch { /* name from fallback */ }
          Object.assign(entry, { name: await freeName(ops, doc ? suggestName(doc, describe) : 'Untitled', entry.id), nameGenerated: true });
        }
        entry.nameKey = nameKey(entry.name);
        if (text !== undefined) entry.description = text;
        await ops.put('entries', entry); return publicEntry(entry);
      });
    },
    async remove(entryId) {
      return write(ALL, async ops => {
        const revisions = await ops.index('revisions', 'entry', entryId);
        for (const revision of revisions) await ops.delete('revisions', revision.id);
        await ops.delete('entries', entryId); await collect(ops, revisions.map(revision => revision.cid));
      });
    },
    async removeRevision(revisionId) {
      return write(ALL, async ops => {
        const revision = await ops.get('revisions', revisionId);
        if (!revision) return;
        const entry = await ops.get('entries', revision.entry);
        if (entry?.head === revisionId) throw new LibraryError('invalid', 'The current revision cannot be deleted. Save a newer revision or delete the whole document.');
        for (const child of (await ops.all('revisions')).filter(row => row.parent === revisionId)) await ops.put('revisions', { ...child, parent: revision.parent });
        await ops.delete('revisions', revisionId); await collect(ops, [revision.cid]);
      });
    },
    async record(doc, { kind = 'link', cid: source } = {}) {
      const item = await prepare(doc);
      return write(ALL, async ops => {
        await storeBlob(ops, item);
        for (const old of await ops.index('recent', 'cid', item.cid)) await ops.delete('recent', old.id);
        await ops.put('recent', { id: id(), cid: item.cid, kind, source: isCID(source) ? source : null, openedAt: clock(), size: item.size, title: suggestName(item.doc, describe) });
        const expired = (await ops.all('recent')).sort(newest).slice(LIBRARY_LIMITS.recent);
        for (const old of expired) await ops.delete('recent', old.id);
        await collect(ops, expired.map(old => old.cid));
        return { cid: item.cid, matches: await matches(ops, item.cid) };
      });
    },
    async recent() {
      return read(ALL, async ops => {
        const rows = (await ops.all('recent')).sort(newest), result = [];
        for (const row of rows) result.push({ ...row, matches: await matches(ops, row.cid) });
        return result;
      });
    },
    async openRecent(recentId) {
      const row = await read(['recent'], ops => ops.get('recent', recentId));
      if (!row) throw new LibraryError('missing', 'This recently opened document is no longer stored.');
      const { doc } = await contents(row.cid);
      return { doc, recent: row };
    },
    async clearRecent() {
      return write(ALL, async ops => {
        const rows = await ops.all('recent');
        for (const row of rows) await ops.delete('recent', row.id);
        await collect(ops, rows.map(row => row.cid));
      });
    },
    async match(value) {
      const cid = typeof value === 'string' ? value : (await prepare(value)).cid;
      return read(['entries', 'revisions'], ops => matches(ops, cid));
    },
    async cid(doc) { return (await prepare(doc)).cid; },
    async markPublished(cid) {
      if (!isCID(cid)) throw new LibraryError('invalid', 'HashBin returned an invalid CID.');
      return write(['revisions', 'blobs'], async ops => {
        const at = clock(), blob = await ops.get('blobs', cid);
        if (blob && !blob.publishedAt) await ops.put('blobs', { ...blob, publishedAt: at });
        const revisions = await ops.index('revisions', 'cid', cid);
        for (const revision of revisions) if (!revision.publishedAt) await ops.put('revisions', { ...revision, publishedAt: at });
        return revisions.length;
      });
    },
    async usage() {
      const counts = await read(ALL, async ops => {
        const revisions = await ops.all('revisions'), recent = await ops.all('recent'), sizes = new Map([...recent, ...revisions].map(row => [row.cid, row.size ?? 0]));
        const stored = await ops.keys('blobs');
        return { entries: (await ops.keys('entries')).length, revisions: revisions.length, recent: recent.length, blobs: stored.length,
          bytes: stored.reduce((total, cid) => total + (sizes.get(cid) ?? 0), 0), missing: [...new Set(revisions.map(row => row.cid))].filter(cid => !stored.includes(cid)).length };
      });
      let quota = null, persisted = null;
      try { quota = (await storageManager?.estimate?.())?.quota ?? null; persisted = (await storageManager?.persisted?.()) ?? null; } catch { /* unsupported */ }
      return { ...counts, quota, persisted };
    },
    async fetchMissing({ signal, onProgress = () => {} } = {}) {
      const cids = await read(['revisions', 'blobs'], async ops => {
        const stored = new Set(await ops.keys('blobs'));
        return [...new Set((await ops.all('revisions')).map(row => row.cid))].filter(cid => !stored.has(cid));
      });
      const failed = []; let fetched = 0;
      for (const cid of cids) {
        if (signal?.aborted) break;
        try { await fetchBlob(cid, signal); fetched++; } catch (error) { failed.push({ cid, error: error.message }); }
        onProgress({ done: fetched + failed.length, total: cids.length });
      }
      return { fetched, failed, total: cids.length };
    },
    async exportCatalog({ mode = 'self-contained', entries: selected, omitUnpublished = false } = {}) {
      if (!CATALOG_MODES.includes(mode)) throw new LibraryError('invalid', 'Choose an export form.');
      const data = await read(['entries', 'revisions', 'blobs'], async ops => ({ entries: await ops.all('entries'), revisions: await ops.all('revisions'), stored: new Set(await ops.keys('blobs')) }));
      const chosen = data.entries.filter(entry => !selected || selected.includes(entry.id)).sort((a, b) => a.created.localeCompare(b.created) || a.id.localeCompare(b.id));
      const byId = new Map(data.revisions.map(row => [row.id, row])), names = new Map(chosen.map(entry => [entry.id, entry.name]));
      const published = new Set(data.revisions.filter(row => row.publishedAt).map(row => row.cid));
      const unpublished = data.revisions.filter(row => names.has(row.entry) && !published.has(row.cid)).map(row => ({ name: names.get(row.entry), entry: row.entry, revision: row.id, cid: row.cid, savedAt: row.savedAt }));
      if (mode === 'references' && unpublished.length && !omitUnpublished) throw new LibraryError('unpublished', `${unpublished.length} revision${unpublished.length === 1 ? ' is' : 's are'} not published to 256t yet.`, { missing: unpublished });
      const kept = data.revisions.filter(row => names.has(row.entry) && (mode !== 'references' || published.has(row.cid)));
      const inline = new Set(mode === 'references' ? [] : kept.filter(row => mode === 'self-contained' || !published.has(row.cid)).map(row => row.cid));
      const absent = [...inline].filter(cid => !data.stored.has(cid));
      if (absent.length) throw new LibraryError('unavailable', 'Some revisions are only referenced. Fetch them before making this export.', { missing: absent });
      const exported = new Set(kept.map(row => row.id));
      const ancestor = row => { let parent = row.parent; while (parent !== null && !exported.has(parent)) parent = byId.get(parent)?.parent ?? null; return parent; };
      const entries = [], breakdown = [];
      for (const entry of chosen) {
        const rows = kept.filter(row => row.entry === entry.id).sort((a, b) => a.savedAt.localeCompare(b.savedAt) || a.id.localeCompare(b.id));
        if (!rows.length) continue;
        const head = exported.has(entry.head) ? entry.head : rows.at(-1).id;
        entries.push({ name: entry.name, nameGenerated: entry.nameGenerated, description: entry.description, created: entry.created, updated: entry.updated, head,
          revisions: rows.map(row => ({ id: row.id, cid: row.cid, parent: ancestor(row), savedAt: row.savedAt })) });
        const sizes = new Map(rows.filter(row => inline.has(row.cid)).map(row => [row.cid, row.size ?? 0]));
        breakdown.push({ name: entry.name, bytes: [...sizes.values()].reduce((total, size) => total + size, 0) });
      }
      const blobs = {};
      if (inline.size) {
        const rows = await read(['blobs'], async ops => { const found = []; for (const cid of [...inline].sort()) found.push(await ops.get('blobs', cid)); return found; });
        for (const row of rows) blobs[row.cid] = row.text;
      }
      const payload = JSON.stringify({ format: CATALOG_FORMAT, version: 1, type: type.type, ...(app ? { app } : {}), exportedAt: clock(), mode, entries, blobs });
      const size = bytes(payload).length;
      if (size > config.maxBytes) throw new LibraryError('too-large', `This export is ${size} bytes; the limit is ${config.maxBytes}. Try the compact or references-only form, or export fewer documents.`, { bytes: size, breakdown });
      return { payload, bytes: size, fileName: `${app ?? prefix}-library.json`, contentType: 'application/json', mode, entries: entries.length,
        revisions: kept.length, inline: inline.size, omitted: mode === 'references' ? unpublished : [] };
    },
    async previewImport(input) {
      const catalog = parseCatalog(input, { type, maxBytes: config.maxBytes });
      for (const [cid, text] of catalog.blobs) {
        if (await computeCID(text) !== cid) throw new LibraryError('invalid', 'This library export is invalid: some contents do not match their CIDs.');
        try { documents.parse(text); } catch (error) { throw new LibraryError('invalid', `This library export contains a document this app cannot open: ${error.message}`); }
      }
      const local = await read(['entries', 'revisions', 'blobs'], async ops => ({ entries: await ops.all('entries'), revisions: await ops.all('revisions'), stored: new Set(await ops.keys('blobs')) }));
      const byName = new Map(local.entries.map(entry => [entry.nameKey, entry]));
      const entries = catalog.entries.map(entry => {
        const match = entry.name ? byName.get(nameKey(entry.name)) : undefined;
        const mine = match ? local.revisions.filter(row => row.entry === match.id) : [], cids = new Set(mine.map(row => row.cid));
        const added = entry.revisions.filter(row => !cids.has(row.cid)).length;
        const same = match && !added && catalog.revisions.get(entry.head).cid === mine.find(row => row.id === match.head)?.cid;
        return Object.freeze({ index: entry.index, name: entry.name, description: entry.description, updated: entry.updated, revisions: entry.revisions.length, added,
          remote: entry.revisions.filter(row => !catalog.blobs.has(row.cid) && !local.stored.has(row.cid)).length,
          status: !match ? 'new' : same ? 'same' : 'conflict', local: match ? publicEntry(match) : null });
      });
      const preview = Object.freeze({ app: catalog.app, mode: catalog.mode, exportedAt: catalog.exportedAt, entries: Object.freeze(entries) });
      previews.set(preview, catalog); return preview;
    },
    async commitImport(preview, decisions = {}) {
      const catalog = previews.get(preview);
      if (!catalog) throw new LibraryError('invalid', 'Preview the import again.');
      const plan = preview.entries.map(item => {
        const choice = decisions[item.index] ?? { new: 'import', same: 'skip' }[item.status];
        if (!choice) throw new LibraryError('decision', `Choose what to do with “${item.name}”.`, { index: item.index });
        if (!IMPORT_CHOICES[item.status].includes(choice)) throw new LibraryError('invalid', `That choice is not available for “${item.name || 'Untitled'}”.`);
        return { item, entry: catalog.entries[item.index], choice };
      }).filter(step => step.choice !== 'skip');
      const result = await write(ALL, async ops => {
        const at = clock(), ids = new Map(), stored = new Set(await ops.keys('blobs')), fresh = [];
        for (const step of plan) {
          const { entry, choice } = step;
          if (choice.startsWith('merge')) {
            [step.target] = await ops.index('entries', 'nameKey', nameKey(entry.name));
            if (!step.target) throw new LibraryError('changed', 'The library changed while you were reviewing. Preview the import again.');
            const mine = new Map((await ops.index('revisions', 'entry', step.target.id)).map(row => [row.cid, row.id]));
            for (const row of entry.revisions) { const known = mine.get(row.cid); ids.set(row.id, known ?? id()); if (!known) { fresh.push([step, row]); mine.set(row.cid, ids.get(row.id)); } }
            continue;
          }
          let name;
          if (choice === 'copy') name = await freeName(ops, `${[...entry.name].slice(0, LIBRARY_LIMITS.name - 12).join('')} (imported)`);
          else if (entry.name) { await claim(ops, entry.name); name = entry.name; }
          else {
            const head = catalog.revisions.get(entry.head), text = catalog.blobs.get(head.cid);
            name = await freeName(ops, text ? suggestName(documents.parse(text), describe) : 'Untitled');
          }
          step.target = { id: id(), name, nameKey: nameKey(name), nameGenerated: choice === 'import' && entry.nameGenerated, description: entry.description, created: entry.created, updated: entry.updated, head: null };
          for (const row of entry.revisions) { ids.set(row.id, id()); fresh.push([step, row]); }
        }
        let remote = 0;
        for (const [step, row] of fresh) {
          const text = catalog.blobs.get(row.cid);
          if (text !== undefined && !stored.has(row.cid)) { await ops.put('blobs', { cid: row.cid, text, size: bytes(text).length }); stored.add(row.cid); }
          if (!stored.has(row.cid)) remote++;
          // Contents left out of an export were published, so they can be fetched from 256t.
          const known = text ?? (stored.has(row.cid) ? (await ops.get('blobs', row.cid))?.text : undefined);
          await ops.put('revisions', { id: ids.get(row.id), entry: step.target.id, cid: row.cid, parent: row.parent === null ? null : ids.get(row.parent) ?? null, savedAt: row.savedAt,
            kind: 'import', size: known === undefined ? cidLength(row.cid) : bytes(known).length, title: known === undefined ? null : suggestName(documents.parse(known), describe), ...(text === undefined ? { publishedAt: at } : {}) });
        }
        for (const { entry, choice, target } of plan) {
          if (choice === 'merge-local') continue;
          if (choice === 'merge-imported') Object.assign(target, { head: ids.get(entry.head), updated: at, description: entry.description || target.description });
          else target.head = ids.get(entry.head);
          await ops.put('entries', target);
        }
        return { entries: plan.length, revisions: fresh.length, remote };
      });
      previews.delete(preview); return result;
    },
    async persist() {
      if (typeof storageManager?.persist !== 'function') return false;
      try { return await storageManager.persist(); } catch { return false; }
    },
    subscribe(listener) { listeners.add(listener); return () => listeners.delete(listener); },
    close() { listeners.clear(); if (broadcast) { broadcast.onmessage = null; broadcast.close?.(); } db.close(); },
  });
}
