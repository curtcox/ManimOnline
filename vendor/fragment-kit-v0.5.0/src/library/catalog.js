import { bounded, text as decodeText } from '../core/bytes.js';
import { isCID } from '../core/cid.js';
import { LibraryError } from './backends.js';
import { cleanName, cleanDescription, nameKey } from './names.js';

export const CATALOG_FORMAT = 'fragment-kit-library';
export const CATALOG_MODES = Object.freeze(['self-contained', 'compact', 'references']);
export const CATALOG_LIMITS = Object.freeze({ entries: 1000, revisions: 10000 });
const ISO = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?Z$/, ID = /^[\w-]{1,64}$/;
const invalid = message => new LibraryError('invalid', `This library export is invalid: ${message}`);
const plain = value => value !== null && typeof value === 'object' && !Array.isArray(value) && Object.getPrototypeOf(value) === Object.prototype;
function only(value, allowed, required, where) {
  if (!plain(value)) throw invalid(`${where} must be an object.`);
  for (const key of Object.keys(value)) if (!allowed.includes(key)) throw invalid(`${where} has an unknown field.`);
  for (const key of required) if (!Object.hasOwn(value, key)) throw invalid(`${where} is missing ${key}.`);
}
function time(value, where) {
  if (typeof value !== 'string' || !ISO.test(value) || Number.isNaN(Date.parse(value))) throw invalid(`${where} has an invalid date.`);
  return new Date(Date.parse(value)).toISOString();
}
function cleaned(clean, value, where) {
  try { return clean(value); } catch (error) { throw invalid(`${where}: ${error.message}`); }
}

/** Strictly validates catalog structure. Blob CIDs and documents are verified separately (asynchronously). */
export function parseCatalog(input, { type, maxBytes }) {
  const payload = typeof input === 'string' ? input : decodeText(bounded(input, maxBytes));
  try { bounded(payload, maxBytes); } catch { throw new LibraryError('too-large', `Library exports can be at most ${maxBytes} bytes.`); }
  let value;
  try { value = JSON.parse(payload); } catch { throw invalid('it is not JSON.'); }
  if (value?.format !== CATALOG_FORMAT) throw new LibraryError('invalid', 'This is not a Fragment Kit library export.');
  if (value.version !== 1) throw new LibraryError('invalid', 'This library export uses an unsupported version.');
  only(value, ['format', 'version', 'type', 'app', 'exportedAt', 'mode', 'entries', 'blobs'], ['type', 'exportedAt', 'mode', 'entries', 'blobs'], 'The export');
  if (value.type !== type.type) throw new LibraryError('wrong-type', `This library export is for ${typeof value.type === 'string' ? value.type.slice(0, 40) : 'another app'}, not ${type.type}.`);
  if (value.app !== undefined && (typeof value.app !== 'string' || !/^[a-z0-9][a-z0-9-]{0,63}$/.test(value.app))) throw invalid('the app name is malformed.');
  if (!CATALOG_MODES.includes(value.mode)) throw invalid('the export mode is unknown.');
  if (!Array.isArray(value.entries) || value.entries.length > CATALOG_LIMITS.entries) throw invalid(`it must list at most ${CATALOG_LIMITS.entries} documents.`);
  if (!plain(value.blobs)) throw invalid('contents must be an object.');
  const revisions = new Map(), blobs = new Map(), names = new Set();
  for (const [cid, text] of Object.entries(value.blobs)) {
    if (!isCID(cid) || typeof text !== 'string') throw invalid('contents are malformed.');
    blobs.set(cid, text);
  }
  const entries = value.entries.map((entry, index) => {
    const where = `Document ${index + 1}`;
    only(entry, ['name', 'nameGenerated', 'description', 'created', 'updated', 'head', 'revisions'], ['name', 'created', 'updated', 'head', 'revisions'], where);
    if (entry.nameGenerated !== undefined && typeof entry.nameGenerated !== 'boolean') throw invalid(`${where} has a malformed name flag.`);
    if (!Array.isArray(entry.revisions) || !entry.revisions.length) throw invalid(`${where} has no revisions.`);
    const rows = entry.revisions.map(revision => {
      only(revision, ['id', 'cid', 'parent', 'savedAt'], ['id', 'cid', 'parent', 'savedAt'], `${where} revision`);
      if (typeof revision.id !== 'string' || !ID.test(revision.id) || revisions.has(revision.id)) throw invalid(`${where} has a missing or repeated revision id.`);
      if (!isCID(revision.cid)) throw invalid(`${where} has an invalid CID.`);
      if (revision.parent !== null && (typeof revision.parent !== 'string' || !ID.test(revision.parent))) throw invalid(`${where} has a malformed parent.`);
      const row = { id: revision.id, cid: revision.cid, parent: revision.parent, savedAt: time(revision.savedAt, where), entry: index };
      revisions.set(row.id, row); return row;
    });
    if (revisions.size > CATALOG_LIMITS.revisions) throw invalid(`it must contain at most ${CATALOG_LIMITS.revisions} revisions.`);
    if (!rows.some(row => row.id === entry.head)) throw invalid(`${where} has an unknown current revision.`);
    const name = cleaned(cleanName, entry.name, where);
    if (name && names.has(nameKey(name))) throw invalid(`${where} repeats another document's name.`);
    names.add(nameKey(name));
    return { index, name, nameGenerated: entry.nameGenerated ?? !name, description: cleaned(cleanDescription, entry.description ?? '', where),
      created: time(entry.created, where), updated: time(entry.updated, where), head: entry.head, revisions: rows };
  });
  const checked = new Set();
  for (const row of revisions.values()) {
    const path = new Set();
    for (let id = row.id; id !== null && !checked.has(id); id = revisions.get(id).parent) {
      if (!revisions.has(id)) throw invalid('a revision names an unknown parent.');
      if (path.has(id)) throw invalid('revision parents form a cycle.');
      path.add(id);
    }
    for (const id of path) checked.add(id);
  }
  const referenced = new Set([...revisions.values()].map(row => row.cid));
  for (const cid of blobs.keys()) if (!referenced.has(cid)) throw invalid('it contains unreferenced contents.');
  if (value.mode === 'self-contained' && [...referenced].some(cid => !blobs.has(cid))) throw invalid('a self-contained export is missing contents.');
  if (value.mode === 'references' && blobs.size) throw invalid('a references-only export cannot contain contents.');
  return { type: value.type, app: value.app ?? null, exportedAt: time(value.exportedAt, 'The export'), mode: value.mode, entries, revisions, blobs };
}
