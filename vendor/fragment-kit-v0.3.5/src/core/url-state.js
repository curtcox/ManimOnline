import { bounded, decode64, text } from './bytes.js';
import { compress as defaultCompress, decompress as defaultDecompress } from './compression.js';
import { isCID } from './cid.js';
import { createDocuments } from './envelope.js';

const staleKeys = ['example', 'doc', 'compressed', 'src', 'raw', 'url', 'code', 'state', 'error', 'error_description', 'hashbin_publish', 'access_token', 'refresh_token', 'token_type', 'expires_in'];
export function createUrlState({ config, type, compress = defaultCompress, decompress = defaultDecompress,
  legacyReaders = [], legacyWriter, history = globalThis.history, location = globalThis.location, timers = globalThis, delay = 300 }) {
  const documents = createDocuments(type, config.maxBytes);
  let timer, revision = 0;
  const source = (doc, common) => ({ ...common, kind: 'source', doc: documents.normalize(doc) });
  const unpack = value => bounded(decompress(value, config.maxBytes), config.maxBytes);
  function parse(input) {
    const url = new URL(input), params = url.searchParams, hash = url.hash.slice(1);
    const settings = Object.fromEntries((type.settingsKeys ?? []).filter(key => params.has(key)).map(key => [key, params.get(key)]));
    const common = { run: params.get('run') !== '0', view: params.get('view') ?? undefined, settings };
    if (new URLSearchParams(hash).has('hashbin_publish')) return { ...common, kind: 'publish', hash: url.hash };
    if (isCID(hash)) return { ...common, kind: 'cid', cid: hash };
    if (hash.startsWith('v1.')) {
      const payload = unpack(hash.slice(3));
      let value; try { value = JSON.parse(payload); } catch { /* Early v1 readers accepted raw source. */ }
      return source(typeof value === 'string' ? { src: value } : documents.parse(payload), common);
    }
    if (/^v\d+\./.test(hash)) throw new Error('Unsupported URL state version.');
    for (const reader of legacyReaders) {
      const result = reader(url, { documents, decompress: unpack, settings });
      if (result !== undefined && result !== null) return source(result.doc ?? result, common);
    }
    if (hash.startsWith('src=')) return source({ src: unpack(hash.slice(4)), ...settings }, common);
    if (hash.startsWith('h1=')) return source(documents.parse(text(decode64(hash.slice(3), config.maxBytes))), common);
    if (hash) {
      let payload;
      try { payload = decodeURIComponent(hash); } catch { throw new Error('Invalid source fragment encoding.'); }
      return source(documents.parse(bounded(payload, config.maxBytes)), common);
    }
    if (params.has('doc')) return source(documents.parse(unpack(params.get('doc'))), common);
    if (params.has('compressed')) return source({ src: unpack(params.get('compressed')), ...settings }, common);
    if (params.has('example')) return { ...common, kind: 'example', id: params.get('example') };
    return { ...common, kind: 'none' };
  }
  function scrub(input) {
    const url = new URL(input);
    for (const key of [...staleKeys, ...(type.settingsKeys ?? []), 'run', 'view']) url.searchParams.delete(key);
    url.hash = '';
    return url;
  }
  function build(value, opts = {}) {
    const doc = documents.normalize(value), url = scrub(opts.url ?? location?.href ?? config.canonicalOrigin);
    if (opts.run === false) url.searchParams.set('run', '0');
    if (opts.view) url.searchParams.set('view', opts.view);
    // Adapters must only return true when every field beyond src has its default value.
    // JSON-string encoding disambiguates source that itself resembles an envelope.
    const payload = type.isDefault?.(doc) ? JSON.stringify(doc.src) : documents.serialize(doc);
    url.hash = 'v1.' + compress(payload);
    const href = legacyWriter ? new URL(legacyWriter(doc, { url: scrub(url.href), run: opts.run, view: opts.view, compress, documents })).href : url.href;
    url.hash = encodeURIComponent(documents.serialize(doc));
    return Object.freeze({ href, plain: url.href, qrCandidate: href, long: href, fallback: href });
  }
  function link(input, cid) {
    if (!isCID(cid)) throw new Error('HashBin returned an invalid CID.');
    const previous = new URL(input), url = scrub(input);
    for (const key of ['run', 'view']) if (previous.searchParams.has(key)) url.searchParams.set(key, previous.searchParams.get(key));
    url.hash = cid; return url.href;
  }
  function cancel() { revision++; timers.clearTimeout(timer); }
  function write(doc, opts = {}) {
    const href = build(doc, opts).href;
    cancel(); const current = revision;
    timer = timers.setTimeout(() => { if (current === revision) history.replaceState(history.state, '', href); }, delay);
    return href;
  }
  return Object.freeze({ parse, build, write, cancel, scrub, link, documents });
}
