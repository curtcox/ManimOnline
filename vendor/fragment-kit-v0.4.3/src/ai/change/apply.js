import { createDocuments } from '../../core/envelope.js';
import { MAX_BYTES } from '../../core/bytes.js';
import { clone, keys, object, parseData, pointer, string, byteLimit } from '../data.js';
export function validateDocument(type, value) {
  const doc = createDocuments(type, byteLimit(type.ai?.maxBytes)).normalize(clone(value));
  const valid = type.ai?.validate?.(doc);
  if (valid?.then) throw new Error('Proposal validation must be synchronous. Use named async checks for evaluation.');
  if (valid === false) throw new Error('The proposed document failed application validation.');
  return doc;
}
export function applyOutput({ type, snapshot, output }) {
  output = parseData(output, byteLimit(type.ai?.maxBytes));
  if (type.ai?.output === 'full') return validateDocument(type, output);
  keys(output, ['summary', 'edits', 'settings'], 'proposal'); string(output.summary, 'proposal summary');
  if (!Array.isArray(output.edits) || output.edits.length > 1000) throw new Error('Expected a bounded edits array.');
  const doc = clone(snapshot), paths = type.ai?.paths ?? ['/src'];
  for (const edit of output.edits) {
    keys(edit, ['path', 'find', 'replace'], 'edit');
    const path = edit.path ?? '/src';
    if (!paths.includes(path)) throw new Error('This field cannot be changed by AI.');
    string(edit.find, 'nonempty find text', MAX_BYTES);
    if (typeof edit.replace !== 'string') throw new Error('Replacement must be text.');
    const target = pointer(doc, path);
    if (typeof target.value !== 'string') throw new Error('Edits require a text field.');
    const index = target.value.indexOf(edit.find);
    if (index === -1 || target.value.indexOf(edit.find, index + 1) !== -1) throw new Error('Find text must match exactly once. Regenerate this proposal.');
    target.parent[target.key] = target.value.slice(0, index) + edit.replace + target.value.slice(index + edit.find.length);
  }
  if (output.settings !== undefined) {
    object(output.settings, 'settings');
    for (const [key, value] of Object.entries(output.settings)) {
      if (!(type.ai?.settingsKeys ?? []).includes(key) || ['__proto__', 'constructor', 'prototype'].includes(key)) throw new Error('Unknown proposal setting.');
      doc[key] = clone(value);
    }
  }
  return validateDocument(type, doc);
}
