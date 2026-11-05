export const MAX_BYTES = 5 * 1024 * 1024;
export const bytes = value => new TextEncoder().encode(value);
export function bounded(value, maxBytes = MAX_BYTES) {
  const length = typeof value === 'string' ? value.length : value.byteLength;
  if (length > maxBytes || (typeof value === 'string' && bytes(value).length > maxBytes)) {
    throw new Error(`Document exceeds the ${maxBytes === MAX_BYTES ? '5 MiB' : maxBytes + ' byte'} limit.`);
  }
  return value;
}
export const text = value => new TextDecoder('utf-8', { fatal: true }).decode(value);
export function encode64(value) {
  let result = '';
  for (let i = 0; i < value.length; i += 8192) result += String.fromCharCode(...value.subarray(i, i + 8192));
  return btoa(result).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}
export function decode64(value, maxBytes = MAX_BYTES) {
  if (typeof value !== 'string' || !/^[\w-]*$/.test(value) || value.length % 4 === 1) throw new Error('Invalid base64url.');
  if (value.length > Math.ceil(maxBytes * 4 / 3)) throw new Error('Encoded document exceeds the byte limit.');
  const result = Uint8Array.from(atob(value.replace(/-/g, '+').replace(/_/g, '/')), char => char.charCodeAt(0));
  if (encode64(result) !== value) throw new Error('Noncanonical base64url.');
  return bounded(result, maxBytes);
}
/** Read streams incrementally; a dishonest Content-Length cannot force an unbounded allocation. */
export async function readResponse(response, maxBytes = MAX_BYTES) {
  const declared = Number(response.headers?.get('content-length'));
  if (declared > maxBytes) { await response.body?.cancel(); throw new Error('Saved source exceeds the byte limit.'); }
  if (!response.body?.getReader) return bounded(new Uint8Array(await response.arrayBuffer()), maxBytes);
  const reader = response.body.getReader(), chunks = [];
  let length = 0;
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      length += value.length;
      if (length > maxBytes) { await reader.cancel(); throw new Error('Saved source exceeds the byte limit.'); }
      chunks.push(value);
    }
  } finally { reader.releaseLock(); }
  const result = new Uint8Array(length);
  let offset = 0;
  for (const chunk of chunks) { result.set(chunk, offset); offset += chunk.length; }
  return result;
}
