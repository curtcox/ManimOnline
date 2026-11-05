import { MAX_BYTES } from './bytes.js';

export function safeURL(value, base) {
  const url = new URL(value, base);
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password) throw new Error('Expected an HTTP(S) URL.');
  return url;
}
export function createConfig(input, { document = globalThis.document } = {}) {
  if (!input) input = JSON.parse(document?.getElementById('fragment-kit-config')?.textContent || '{}');
  for (const key of ['slug', 'name', 'storagePrefix', 'canonicalOrigin', 'recoveryOrigin', 'repo', 'docs', 'gallery', 'documentType']) {
    if (typeof input[key] !== 'string' || !input[key].trim()) throw new Error(`Missing app config: ${key}.`);
  }
  if (!/^[a-z0-9][a-z0-9-]*$/.test(input.slug) || !/^[\w.-]+:?$/.test(input.storagePrefix)) throw new Error('Invalid app slug or storage prefix.');
  if (!/^[\w.-]+\/[\w.-]+$/.test(input.repo)) throw new Error('Invalid GitHub repository.');
  const canonicalOrigin = safeURL(input.canonicalOrigin).href;
  const recoveryOrigin = safeURL(input.recoveryOrigin).href;
  for (const href of [canonicalOrigin, recoveryOrigin]) {
    const url = new URL(href);
    if (url.search || url.hash || !url.pathname.endsWith('/')) throw new Error('App origins must end with / and have no query or fragment.');
  }
  const maxBytes = input.maxBytes ?? MAX_BYTES;
  if (!Number.isSafeInteger(maxBytes) || maxBytes < 1) throw new Error('Invalid maxBytes.');
  return Object.freeze({ ...input, canonicalOrigin, recoveryOrigin, maxBytes,
    hashbinClientId: input.hashbinClientId ?? document?.querySelector('meta[name="hashbin-client-id"]')?.content ?? '',
    docs: safeURL(input.docs, canonicalOrigin).href, gallery: safeURL(input.gallery, canonicalOrigin).href,
    storagePrefix: input.storagePrefix.replace(/:$/, ''),
    allowedHosts: Object.freeze([...new Set(['hashbin.org', '256t.us', new URL(canonicalOrigin).hostname, new URL(recoveryOrigin).hostname])]) });
}
export function redirectUri(config, href = globalThis.location?.href ?? config.recoveryOrigin) {
  const here = new URL(href), canonical = new URL(config.canonicalOrigin);
  return here.origin === canonical.origin && here.pathname.startsWith(canonical.pathname) ? config.canonicalOrigin : config.recoveryOrigin;
}
export function isAppURL(input, config) {
  let url;
  try { url = safeURL(input); } catch { return false; }
  return [config.canonicalOrigin, config.recoveryOrigin].some(base => {
    const expected = new URL(base);
    return url.origin === expected.origin && [expected.pathname, expected.pathname + 'index.html'].includes(url.pathname);
  });
}
