import { decode64, readResponse } from './bytes.js';
import { cidLength, isCID, verify } from './cid.js';
/** Fetch verified data, independent of a document adapter. */
export async function loadContent(cid, { maxBytes, fetchSource = globalThis.fetch, url = `https://256t.us/${cid}`, signal, headers } = {}) {
  if (!isCID(cid)) throw new Error('Invalid CID.');
  const length = cidLength(cid);
  if (!Number.isSafeInteger(maxBytes) || length > maxBytes) throw new Error('Saved source exceeds the byte limit.');
  let content;
  if (length <= 64) content = decode64(cid.slice(8), 64);
  else {
    const response = await fetchSource(url, { signal, headers, credentials: 'omit', referrerPolicy: 'no-referrer', redirect: 'follow' });
    if (!response.ok) throw new Error(response.status === 404 ? 'Saved source was not found. It may have expired or been deleted.' : `HashBin load failed (HTTP ${response.status}).`);
    content = await readResponse(response, length);
  }
  await verify(cid, content); return content;
}
