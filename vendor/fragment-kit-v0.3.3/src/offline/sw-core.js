/* Classic worker: imported after the app's generated offline-assets.js. */
(() => {
  const manifest = self.OfflineAssets;
  const options = self.FragmentKitOfflineConfig ?? {};
  if (!manifest?.prefix || !manifest.version?.startsWith(manifest.prefix + '-') || !manifest.assets?.length) throw new Error('Invalid prefixed offline manifest.');
  const cacheName = manifest.version, prefix = manifest.prefix + '-';
  const concurrency = options.downloadConcurrency ?? 6;
  if (!Number.isInteger(concurrency) || concurrency < 1 || concurrency > 16) throw new Error('Invalid offline download concurrency.');
  const absolute = asset => new URL(asset, self.registration.scope).href;
  const hashes = new Map(Object.entries(manifest.hashes).map(([asset, hash]) => [absolute(asset), hash]));
  const hex = value => Array.from(new Uint8Array(value), byte => byte.toString(16).padStart(2, '0')).join('');
  const types = { html: 'text/html', js: 'text/javascript', mjs: 'text/javascript', css: 'text/css', json: 'application/json', svg: 'image/svg+xml', png: 'image/png', wasm: 'application/wasm', webmanifest: 'application/manifest+json' };
  async function verified(response, url) {
    if (!response?.ok || !hashes.has(url)) return null;
    const body = await response.arrayBuffer();
    if (hex(await crypto.subtle.digest('SHA-256', body)) !== hashes.get(url)) return null;
    const extension = new URL(url).pathname.split('.').pop();
    const headers = new Headers(response.headers);
    headers.set('Content-Type', types[extension] ?? 'application/octet-stream');
    headers.delete('content-encoding'); headers.delete('content-length');
    return new Response(body, { status: 200, headers });
  }
  let populating;
  function populate() {
    if (populating) return populating;
    populating = (async () => {
      const stagingName = cacheName + '-staging-' + crypto.randomUUID();
      const staging = await caches.open(stagingName);
      try {
        const pending = manifest.assets.slice();
        const results = await Promise.allSettled(Array.from({ length: Math.min(concurrency, pending.length) }, async () => {
          while (pending.length) {
          const asset = pending.shift();
          const url = absolute(asset);
          let response;
          try { response = await fetch(url, { cache: 'reload' }); if (!response.ok) throw new Error('HTTP ' + response.status); }
          catch (error) {
            const fallback = (options.cdnFallbacks ?? manifest.cdnFallbacks)?.[asset];
            if (!fallback) throw error;
            response = await fetch(absolute(fallback), { cache: 'reload' });
          }
          const checked = await verified(response, url);
          if (!checked) throw new Error('Offline download did not match its manifest: ' + asset);
          await staging.put(url, checked);
          }
        }));
        const failed = results.find(result => result.status === 'rejected');
        if (failed) throw failed.reason;
        const cache = await caches.open(cacheName);
        // Only copy after every asset verified; failed repair keeps the prior cache.
        for (const asset of manifest.assets) {
          const url = absolute(asset); await cache.put(url, await staging.match(url));
        }
      } finally { await caches.delete(stagingName); }
    })().finally(() => { populating = null; });
    return populating;
  }
  self.addEventListener('install', event => event.waitUntil(populate()));
  self.addEventListener('activate', event => event.waitUntil((async () => {
    for (const name of await caches.keys()) if (name.startsWith(prefix) && name !== cacheName && !(options.extraCaches ?? []).includes(name) && !options.preserveCache?.(name)) await caches.delete(name);
    await self.clients.claim();
  })()));
  self.addEventListener('fetch', event => {
    if (event.request.method !== 'GET') return;
    const url = new URL(event.request.url), local = url.origin === self.location.origin;
    const key = local ? url.origin + url.pathname : url.href;
    const navigation = event.request.mode === 'navigate';
    const entry = navigation && !hashes.has(key) && [self.registration.scope, absolute('index.html')].includes(key) ? absolute('index.html') : key;
    if (!hashes.has(entry)) return;
    event.respondWith((async () => {
      const cache = await caches.open(cacheName);
      const cached = await verified(await cache.match(entry), entry);
      if (cached) return cached;
      await cache.delete(entry);
      const response = await fetch(event.request);
      const checked = await verified(response.clone(), entry);
      if (!checked) throw new Error('Offline asset verification failed.');
      await cache.put(entry, checked.clone()); return checked;
    })());
  });
  self.addEventListener('message', event => {
    if (event.data?.type === 'activate-update') { self.skipWaiting(); return; }
    if (!['offline-status', 'repair-offline'].includes(event.data?.type)) {
      const work = options.onMessage?.(event); if (work) event.waitUntil(work); return;
    }
    event.waitUntil((async () => {
      try {
        if (event.data.type === 'repair-offline') await populate();
        const cache = await caches.open(cacheName);
        const entries = await Promise.all(manifest.assets.map(async asset => {
          const url = absolute(asset); return Boolean(await verified(await cache.match(url), url));
        }));
        event.ports[0]?.postMessage({ ready: entries.every(Boolean), version: cacheName, count: entries.filter(Boolean).length, total: entries.length });
      } catch (error) { event.ports[0]?.postMessage({ ready: false, version: cacheName, error: error.message }); }
    })());
  });
})();
