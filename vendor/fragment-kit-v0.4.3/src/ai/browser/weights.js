import { cidLength, verify, computeCID } from '../../core/cid.js';
import { readResponse } from '../../core/bytes.js';
import { parseManifest } from './manifest.js';
import { abort } from '../data.js';
export function createWeightStore({ prefix, caches = globalThis.caches, fetchSource = globalThis.fetch, storage = globalThis.navigator?.storage } = {}) {
  if (!/^[\w.-]+$/.test(prefix)) throw new Error('Model cache requires an app prefix.');
  const family = `${prefix}-ai-models-`;
  async function name(manifest) { return family + await computeCID(JSON.stringify(manifest)); }
  const key = cid => `https://fragment-kit.invalid/ai/shards/${cid}`;
  async function read(cache, shard) {
    const response = await cache.match(key(shard.cid)); if (!response) return null;
    try { const data = await readResponse(response, cidLength(shard.cid)); await verify(shard.cid, data); return data; }
    catch { await cache.delete(key(shard.cid)); return null; }
  }
  async function download(input, { consent = false, signal, onProgress = () => {} } = {}) {
    const manifest = parseManifest(input);
    if (consent !== true) throw new Error('Approve the model size, licence, memory and mirrors before downloading.');
    const total = manifest.files.reduce((n, f) => n + f.bytes, 0), estimate = await storage?.estimate?.();
    if (estimate?.quota && estimate.quota - (estimate.usage ?? 0) < total) throw new Error('This device does not have enough free model storage.');
    void storage?.persist?.().catch(() => {});
    const cache = await caches.open(await name(manifest)); let completed = 0;
    for (const file of manifest.files) for (const shard of file.shards) {
      abort(signal); let content = await read(cache, shard);
      if (!content) {
        const failures = [];
        for (const mirror of manifest.mirrors) {
          abort(signal);
          const template = typeof mirror === 'string' ? mirror : mirror.url;
          const url = template.replaceAll('{cid}', shard.cid).replaceAll('{path}', file.path.split('/').map(encodeURIComponent).join('/'));
          try {
            const headers = typeof mirror === 'string' ? {} : { Range: `bytes=${shard.offset}-${shard.offset + cidLength(shard.cid) - 1}` };
            const response = await fetchSource(url, { headers, signal, credentials: 'omit', referrerPolicy: 'no-referrer' });
            if (!response.ok) { await response.body?.cancel(); throw new Error('HTTP failure'); }
            if (typeof mirror !== 'string' && (response.status !== 206 || response.headers.get('content-range') !== `bytes ${shard.offset}-${shard.offset + cidLength(shard.cid) - 1}/${file.bytes}`)) { await response.body?.cancel(); throw new Error('Invalid content range'); }
            content = await readResponse(response, cidLength(shard.cid)); await verify(shard.cid, content);
            await cache.put(key(shard.cid), new Response(content)); break;
          } catch { content = null; abort(signal); failures.push(new URL(url).origin); }
        }
        if (!content) throw new Error(`Model shard failed verification or download from ${failures.join(', ')}. Try another mirror.`);
      }
      completed += content.byteLength; onProgress({ completed, total });
    }
    return { bytes: total, cache: await name(manifest) };
  }
  async function files(input) {
    const manifest = parseManifest(input), cache = await caches.open(await name(manifest)), files = [];
    for (const file of manifest.files) {
      const parts = [];
      for (const shard of file.shards) { const data = await read(cache, shard); if (!data) throw new Error('Verified model data is missing. Download or repair it first.'); parts.push(data); }
      files.push(new Blob(parts));
    }
    return files;
  }
  return { family, download, files, async remove(input) { return caches.delete(await name(parseManifest(input))); },
    async list() { return (await caches.keys()).filter(n => n.startsWith(family)); }, preserveCache: n => n.startsWith(family) };
}
