import { bytes, encode64, decode64 } from './bytes.js';
export function cidLength(value) {
  if (typeof value !== 'string' || value.length < 8) throw new Error('Invalid CID.');
  return decode64(value.slice(0, 8), 6).reduce((n, b) => n * 256 + b, 0);
}
export function isCID(value) {
  if (typeof value !== 'string' || !/^[\w-]{8,94}$/.test(value)) return false;
  try {
    const length = cidLength(value);
    if (value.length !== 8 + (length <= 64 ? Math.ceil(length * 4 / 3) : 86)) return false;
    return encode64(decode64(value.slice(8), 64)) === value.slice(8);
  } catch { return false; }
}
export async function computeCID(value) {
  const content = typeof value === 'string' ? bytes(value) : value;
  const prefix = new Uint8Array(6);
  let length = content.length;
  for (let i = 5; i >= 0; i--) { prefix[i] = length % 256; length = Math.floor(length / 256); }
  return encode64(prefix) + encode64(content.length <= 64 ? content : new Uint8Array(await crypto.subtle.digest('SHA-512', content)));
}
export async function verify(value, content) {
  if (!isCID(value) || await computeCID(content) !== value) throw new Error('HashBin content does not match its CID.');
  return true;
}
export function cid(input, allowedHosts = ['hashbin.org', '256t.us']) {
  if (typeof input !== 'string') return null;
  const raw = input.trim().replace(/^#/, '');
  if (isCID(raw)) return raw;
  try {
    const url = new URL(raw);
    if (url.protocol !== 'https:' || url.username || url.password || url.port || !allowedHosts.includes(url.hostname)) return null;
    const candidate = url.hash.slice(1) || url.pathname.split('/').pop();
    return isCID(candidate) ? candidate : null;
  } catch { return null; }
}
