importScripts('src/examples.js', 'offline-assets.js', 'offline-hashes.js', 'vendor/hashbin-cache-v0.4.0.js');
const CACHE = OfflineAssets.VERSION;
const scope = self.registration.scope;
const assets = OfflineAssets.urls(scope);
// The editor and gallery open offline from these; Python and math also need OfflineAssets.runtime.
const installAssets = OfflineAssets.installUrls(scope);
// Cache Storage is shared by every app on this origin, so bytes must match the pinned hash
// before they are stored or served. Headers are rebuilt rather than trusted.
// (HashBin SDK v0.4.0 verified cache, vendored.)
const hashFor = HashBinCache.lookup(OfflineHashes, scope);
const verified = (response, url) => HashBinCache.verify(response, hashFor(url), url);
async function download(cache, urls, init) {
  await Promise.all(urls.map(async url => {
    const checked = await verified(await fetch(new Request(url, init)), url);
    if (!checked) throw new Error('Offline file did not match its pinned hash: ' + url);
    await cache.put(url, checked);
  }));
}
async function missingFiles(cache, urls = assets) {
  const results = await Promise.all(urls.map(async url => verified(await cache.match(url), url)));
  return urls.filter((_, index) => !results[index]);
}

self.addEventListener('install', event => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    try {
      // CORS responses are readable; opaque responses cannot prove readiness.
      const local = OfflineAssets.local.map(path => new URL(path, scope).href);
      await download(cache, local, { mode: 'cors', cache: 'reload' });
      // Pinned remote runtimes do not change with an application release. Reuse
      // already saved copies so an upgrade does not depend on CDN availability.
      await Promise.all(OfflineAssets.remote.map(async url => {
        const saved = await verified(await caches.match(url), url);
        if (saved) await cache.put(url, saved);
        else await download(cache, [url], { mode: 'cors', cache: 'reload' });
      }));
      // Runtimes are not downloaded here (see OfflineAssets.runtime), only carried over.
      await Promise.all(OfflineAssets.runtime.map(async url => {
        const saved = await verified(await caches.match(url), url);
        if (saved) await cache.put(url, saved);
      }));
    } catch (error) {
      await caches.delete(CACHE);
      throw error;
    }
    // Activate only after a complete matching cache is ready. Existing editor
    // controllerchange handlers preserve their source/options before reloading.
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    for (const name of await caches.keys()) {
      if (name.startsWith('manimonline-offline-') && name !== CACHE) await caches.delete(name);
    }
    await self.clients.claim();
  })());
});

self.addEventListener('message', event => {
  if (event.data?.type === 'activate-update') { self.skipWaiting(); return; }
  if (!['offline-status', 'repair-offline', 'cache-runtime'].includes(event.data?.type)) return;
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    if (event.data.type === 'repair-offline') {
      try {
        await download(cache, await missingFiles(cache), { mode: 'cors', cache: 'reload' });
      } catch (_) { /* Report incomplete setup; retain files that are still valid. */ }
    }
    if (event.data.type === 'cache-runtime') {
      // Sent after a live render: the browser has just downloaded these, so allow its HTTP cache.
      try {
        await download(cache, await missingFiles(cache, OfflineAssets.runtime), { mode: 'cors' });
      } catch (_) { /* Retried after the next render or by Save Python offline. */ }
    }
    const missing = await missingFiles(cache);
    const installed = !(await missingFiles(cache, installAssets)).length;
    event.ports[0]?.postMessage({ version: CACHE, ready: missing.length === 0, missing: missing.length, installed });
  })());
});

self.addEventListener('fetch', event => {
  const key = OfflineAssets.key(event.request, scope);
  if (!key) return;
  event.respondWith((async () => {
    const cache = await caches.open(CACHE);
    const cached = await verified(await cache.match(key), key);
    // A missing or altered entry is never served; offline status reports it until repaired.
    if (!cached) await cache.delete(key);
    if (cached && (event.request.mode !== 'navigate' || !(await missingFiles(cache, installAssets)).length)) return cached;
    try {
      const response = await fetch(event.request);
      const copy = await verified(response.clone(), key);
      if (copy) await cache.put(key, copy);
      return response;
    } catch (error) {
      if (event.request.mode !== 'navigate') throw error;
      return new Response('<!doctype html><html lang="en"><meta charset="utf-8"><title>ManimOnline offline</title><h1>Connect to finish offline setup</h1><p>The saved editor files are incomplete or were cleared. Reconnect, reload ManimOnline, and wait for “Ready offline” before disconnecting.</p></html>', {
        status: 503, headers: { 'Content-Type': 'text/html; charset=utf-8' }
      });
    }
  })());
});
