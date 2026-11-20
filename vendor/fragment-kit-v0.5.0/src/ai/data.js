import { bounded, MAX_BYTES } from '../core/bytes.js';
export const clone = value => JSON.parse(JSON.stringify(value));
export function object(value, label = 'object') {
  if (!value || typeof value !== 'object' || Array.isArray(value) || ![Object.prototype, null].includes(Object.getPrototypeOf(value))) throw new Error(`Expected ${label}.`);
  return value;
}
export function keys(value, allowed, label) {
  object(value, label);
  if (Object.keys(value).some(key => !allowed.includes(key) || ['__proto__', 'constructor', 'prototype'].includes(key))) throw new Error(`Unknown ${label ?? 'object'} field.`);
  return value;
}
export function string(value, label, max = 65536) {
  if (typeof value !== 'string' || !value.trim()) throw new Error(`Expected ${label}.`);
  return bounded(value, max);
}
export function number(value, label, { min = 0, max = Number.MAX_SAFE_INTEGER, integer = false } = {}) {
  if (!Number.isFinite(value) || value < min || value > max || (integer && !Number.isSafeInteger(value))) throw new Error(`Invalid ${label}.`);
  return value;
}
export function parseData(value, max = MAX_BYTES) {
  if (typeof value === 'string') return JSON.parse(bounded(value, max));
  return JSON.parse(bounded(JSON.stringify(value), max));
}
export function abort(signal) { signal?.throwIfAborted(); }
export function endpoint(value, { loopback = true } = {}) {
  const url = new URL(value);
  if (url.username || url.password || url.search || url.hash || (url.protocol !== 'https:' && !(loopback && url.protocol === 'http:' && ['localhost', '127.0.0.1', '[::1]'].includes(url.hostname)))) throw new Error('Use an HTTPS endpoint, or HTTP on localhost, without credentials or query.');
  return url;
}
export async function sha256(value) {
  return [...new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(value)))].map(n => n.toString(16).padStart(2, '0')).join('');
}
export function pointer(doc, path) {
  if (typeof path !== 'string' || !path.startsWith('/') || /~(?![01])/u.test(path)) throw new Error('Invalid edit path.');
  const parts = path.slice(1).split('/').map(p => p.replace(/~1/g, '/').replace(/~0/g, '~'));
  if (parts.some(p => !p || ['__proto__', 'constructor', 'prototype'].includes(p))) throw new Error('Unsafe edit path.');
  let parent = doc;
  for (const part of parts.slice(0, -1)) { if (!Object.hasOwn(object(parent), part)) throw new Error('Unknown edit path.'); parent = parent[part]; }
  const key = parts.at(-1);
  if (!Object.hasOwn(object(parent), key)) throw new Error('Unknown edit path.');
  return { parent, key, value: parent[key] };
}

export const byteLimit = value => number(value ?? MAX_BYTES, 'AI byte limit', { min:1, max:MAX_BYTES, integer:true });
