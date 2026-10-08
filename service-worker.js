importScripts('offline-assets.js');
const CACHE = OfflineAssets.VERSION;
const scope = self.registration.scope;
const assets = OfflineAssets.urls(scope);

async function missingFiles(cache) {
  const results = await Promise.all(assets.map(url => cache.match(url)));
  return assets.filter((_, index) => !results[index]);
}

self.addEventListener('install', event => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    try {
      // CORS responses are readable; opaque responses cannot prove readiness.
      await cache.addAll(assets.map(url => new Request(url, { mode: 'cors', cache: 'reload' })));
    } catch (error) {
      await caches.delete(CACHE);
      throw error;
    }
    // Updates wait for current pages to close, or an explicit update action.
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
  if (!['offline-status', 'repair-offline'].includes(event.data?.type)) return;
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    if (event.data.type === 'repair-offline') {
      try {
        await cache.addAll((await missingFiles(cache)).map(url => new Request(url, { mode: 'cors', cache: 'reload' })));
      } catch (_) { /* Report incomplete setup; retain files that are still valid. */ }
    }
    const missing = await missingFiles(cache);
    event.ports[0]?.postMessage({ version: CACHE, ready: missing.length === 0, missing: missing.length });
  })());
});

self.addEventListener('fetch', event => {
  const key = OfflineAssets.key(event.request, scope);
  if (!key) return;
  event.respondWith((async () => {
    const cache = await caches.open(CACHE);
    const cached = await cache.match(key);
    if (cached && (event.request.mode !== 'navigate' || !(await missingFiles(cache)).length)) return cached;
    try {
      const response = await fetch(event.request);
      if (response.ok && response.type !== 'opaque') await cache.put(key, response.clone());
      return response;
    } catch (error) {
      if (event.request.mode !== 'navigate') throw error;
      return new Response('<!doctype html><html lang="en"><meta charset="utf-8"><title>ManimOnline offline</title><h1>Connect to finish offline setup</h1><p>The saved editor files are incomplete or were cleared. Reconnect, reload ManimOnline, and wait for “Ready offline” before disconnecting.</p></html>', {
        status: 503, headers: { 'Content-Type': 'text/html; charset=utf-8' }
      });
    }
  })());
});
