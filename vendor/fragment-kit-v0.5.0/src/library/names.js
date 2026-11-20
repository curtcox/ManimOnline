import { LibraryError } from './backends.js';

export const LIBRARY_LIMITS = Object.freeze({ name: 120, description: 4000, generatedName: 60, recent: 50 });
// Control, zero-width and bidirectional override characters can disguise imported names.
const HIDDEN = /[\u0000-\u0008\u000b-\u001f\u007f-\u009f\u200b-\u200f\u2028-\u202e\u2060-\u2064\u2066-\u2069\ufeff]/g;
const length = value => [...value].length;

export function cleanName(value) {
  if (value === undefined || value === null) return '';
  if (typeof value !== 'string') throw new LibraryError('invalid', 'Names must be text.');
  const name = value.normalize('NFC').replace(/[\t\n\r]/g, ' ').replace(HIDDEN, '').replace(/\s+/g, ' ').trim();
  if (length(name) > LIBRARY_LIMITS.name) throw new LibraryError('invalid', `Names can be at most ${LIBRARY_LIMITS.name} characters.`);
  return name;
}
export function cleanDescription(value) {
  if (value === undefined || value === null) return '';
  if (typeof value !== 'string') throw new LibraryError('invalid', 'Descriptions must be text.');
  const description = value.normalize('NFC').replace(/\r\n?/g, '\n').replace(HIDDEN, '').trim();
  if (length(description) > LIBRARY_LIMITS.description) throw new LibraryError('invalid', `Descriptions can be at most ${LIBRARY_LIMITS.description} characters.`);
  return description;
}
export const nameKey = name => name.normalize('NFC').toLowerCase();
export function suggestName(doc, describe = value => value.src) {
  let summary = '';
  try { summary = String(describe(doc) ?? ''); } catch { /* fall back to Untitled */ }
  const line = summary.split('\n').map(text => text.normalize('NFC').replace(HIDDEN, '').replace(/\s+/g, ' ').trim()).find(Boolean) ?? '';
  return [...line].slice(0, LIBRARY_LIMITS.generatedName).join('').trim() || 'Untitled';
}
