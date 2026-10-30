const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const Assets = require('../offline-assets.js');
const { createHash } = require('node:crypto');
const body = url => url.endsWith('index.html') ? '<html>editor</html>' : 'asset';
const sha = text => createHash('sha256').update(text).digest('hex');
const { ExampleCatalog } = require('../src/examples.js');

function harness() {
  const handlers = {}, stores = new Map(), scope = 'https://example.test/ManimOnline/';
  let online = true, failURL = '', claims = 0, activations = 0, observe = () => {};
  const caches = {
    match: async url => {
      for (const store of stores.values()) if (store.has(url)) return store.get(url).clone();
    },
    open: async name => {
      if (!stores.has(name)) stores.set(name, new Map());
      const store = stores.get(name);
      return {
        match: async url => store.get(url)?.clone(),
        put: async (url, response) => store.set(url, response),
        delete: async url => store.delete(url),
        addAll: async requests => {
          const values = await Promise.all(requests.map(async request => [request.url, await fetch(request)]));
          if (values.some(([, response]) => !response.ok)) throw new Error('Bad response');
          values.forEach(([url, response]) => store.set(url, response));
        }
      };
    },
    keys: async () => [...stores.keys()],
    delete: async name => stores.delete(name)
  };
  const fetch = async request => {
    observe(request.url);
    if (!online || request.url === failURL) throw new Error('Offline');
    return new Response(body(request.url));
  };
  // The harness's pinned hashes describe its fake bodies; real ones come from offline-hashes.js.
  const hashes = {};
  for (const url of [...Assets.urls(scope), ...Assets.optional]) hashes[url] = sha(body(url));
  // The vendored HashBin cache helper is the one real import; the others are provided directly.
  const context = { Request, Response, crypto, URL };
  vm.runInNewContext(fs.readFileSync('vendor/hashbin-cache-v0.4.0.js', 'utf8'), context);
  vm.runInNewContext(fs.readFileSync('service-worker.js', 'utf8'), {
    OfflineAssets: Assets, OfflineHashes: hashes, HashBinCache: context.HashBinCache, importScripts() {}, caches, fetch, Request, Response, crypto,
    URL, self: { registration: { scope },
      addEventListener: (name, handler) => handlers[name] = handler,
      clients: { claim: async () => claims++ }, skipWaiting() { activations++; } }
  });
  const run = (type, args = {}) => {
    let result;
    handlers[type]({ ...args, waitUntil: promise => result = promise, respondWith: promise => result = promise });
    return result;
  };
  return { stores, run, onFetch: callback => observe = callback, setOnline: value => online = value, fail: url => failURL = url, get claims() { return claims; }, get activations() { return activations; } };
}

test('offline manifest covers gallery, editor dependencies, and every local script', () => {
  for (const file of Assets.local) assert.ok(fs.existsSync(file), file);
  for (const example of ExampleCatalog) {
    assert.ok(Assets.local.includes(example.path));
    assert.ok(Assets.local.includes(example.cover));
  }
  for (const file of ['gallery.html', 'src/gallery.js', 'src/gallery.css']) assert.ok(Assets.local.includes(file));
  const html = fs.readFileSync('index.html', 'utf8');
  for (const [, path] of html.matchAll(/<script src="([^"?]+)(?:\?[^" ]*)?"/g)) {
    assert.ok((path.startsWith('https:') ? Assets.remote : Assets.local).includes(path), path);
  }
});

test('cache keys respect project scope, normalize navigation and versions, and exclude sharing/source URLs', () => {
  const scope = 'https://example.test/ManimOnline/';
  assert.equal(Assets.key({ method: 'GET', mode: 'navigate', url: scope + '?scene=Demo' }, scope), scope + 'index.html');
  assert.equal(Assets.key({ method: 'GET', url: scope + 'src/manim-player.js?v=2' }, scope), scope + 'src/manim-player.js');
  for (const url of ['https://api.allorigins.win/get?secret=1', scope + 'custom.py', 'https://example.test/other/index.html', Assets.remote[0] + '?x=1']) {
    assert.equal(Assets.key({ method: 'GET', url }, scope), null);
  }
  assert.equal(Assets.key({ method: 'POST', url: scope + 'index.html' }, scope), null);
});

test('complete install supports fresh offline navigation, workers, math, and gallery fetches', async () => {
  const h = harness();
  await h.run('install');
  assert.equal(h.activations, 1);
  h.stores.set('manimonline-offline-old', new Map());
  h.stores.set('unrelated-cache', new Map());
  await h.run('activate');
  assert.equal(h.claims, 1);
  assert.ok(!h.stores.has('manimonline-offline-old'));
  assert.ok(h.stores.has('unrelated-cache'));
  await h.run('message', { data: { type: 'cache-runtime' }, ports: [] });
  h.setOnline(false);
  for (const url of Assets.urls('https://example.test/ManimOnline/')) {
    const response = await h.run('fetch', { request: { method: 'GET', mode: 'cors', url } });
    assert.equal(response.status, 200, url);
  }
  const response = await h.run('fetch', { request: { method: 'GET', mode: 'navigate', url: 'https://example.test/ManimOnline/?scene=Demo' } });
  assert.equal(await response.text(), '<html>editor</html>');
  let status;
  await h.run('message', { data: { type: 'offline-status' }, ports: [{ postMessage: value => status = value }] });
  assert.equal(status.ready, true);
});

test('install skips Python and math runtimes until a live render asks for them', async () => {
  const h = harness();
  const requested = [];
  h.onFetch(url => requested.push(url));
  await h.run('install');
  await h.run('activate');
  assert.equal(h.activations, 1);
  for (const url of Assets.runtime) assert.ok(!requested.includes(url), url);
  assert.ok(Assets.runtime.some(url => /pyodide\.asm\.wasm$/.test(url)));
  h.setOnline(false);
  const page = await h.run('fetch', { request: { method: 'GET', mode: 'navigate', url: 'https://example.test/ManimOnline/' } });
  assert.equal(await page.text(), '<html>editor</html>', 'editor and gallery still open offline');
  let status;
  await h.run('message', { data: { type: 'offline-status' }, ports: [{ postMessage: value => status = value }] });
  assert.deepEqual([status.ready, status.installed, status.missing], [false, true, Assets.runtime.length]);
  h.setOnline(true);
  await h.run('message', { data: { type: 'cache-runtime' }, ports: [{ postMessage: value => status = value }] });
  assert.deepEqual([status.ready, status.installed, status.missing], [true, true, 0]);
});

test('failed preparation deletes incomplete new cache and preserves the old version', async () => {
  const h = harness();
  h.stores.set('manimonline-offline-old', new Map());
  h.fail(Assets.remote.at(-1));
  await assert.rejects(h.run('install'));
  assert.equal(h.activations, 0);
  assert.ok(!h.stores.has(Assets.VERSION));
  assert.ok(h.stores.has('manimonline-offline-old'));
});

test('upgrades reuse pinned remote files when the CDN is unavailable', async () => {
  const h = harness();
  const pinned = [...Assets.remote, ...Assets.runtime];
  const old = new Map(pinned.map(url => [url, new Response('asset')]));
  h.stores.set('manimonline-offline-old', old);
  h.fail(Assets.remote.at(-1));
  await h.run('install');
  assert.equal(h.activations, 1);
  const cached = h.stores.get(Assets.VERSION);
  for (const url of pinned) assert.equal(await cached.get(url).text(), 'asset');
});

test('altered cache entries written by other apps on the origin are never carried over or served', async () => {
  const h = harness();
  const poisoned = [...Assets.remote, ...Assets.runtime];
  h.stores.set('manimonline-offline-old', new Map(poisoned.map(url => [url, new Response('globalThis.poisoned = true')])));
  await h.run('install');
  const cache = h.stores.get(Assets.VERSION);
  for (const url of Assets.remote) assert.equal(await cache.get(url).text(), 'asset', url);
  for (const url of Assets.runtime) assert.ok(!cache.has(url), url);
  const script = 'https://example.test/ManimOnline/src/manim-player.js';
  cache.set(script, new Response('globalThis.poisoned = true'));
  h.setOnline(false);
  await assert.rejects(h.run('fetch', { request: { method: 'GET', mode: 'cors', url: script } }));
  assert.ok(!cache.has(script));
  h.setOnline(true);
  assert.equal(await (await h.run('fetch', { request: { method: 'GET', mode: 'cors', url: script } })).text(), 'asset');
  assert.equal(await cache.get(script).text(), 'asset');
});

test('offline-hashes.js is current for every offline file', () => {
  const hashes = require('../offline-hashes.js');
  for (const path of Assets.local) assert.equal(hashes[path], sha(fs.readFileSync(path)), path);
  for (const url of [...Assets.remote, ...Assets.runtime, ...Assets.optional]) assert.match(hashes[url] || '', /^[0-9a-f]{64}$/, url);
});

test('partial cache offline provides a recovery page instead of a broken editor', async () => {
  const h = harness();
  await h.run('install');
  await h.run('message', { data: { type: 'cache-runtime' }, ports: [] });
  h.stores.get(Assets.VERSION).delete(Assets.remote.at(-1));
  h.setOnline(false);
  const response = await h.run('fetch', { request: { method: 'GET', mode: 'navigate', url: 'https://example.test/ManimOnline/' } });
  assert.equal(response.status, 503);
  assert.match(await response.text(), /Connect to finish offline setup/);
  let status;
  await h.run('message', { data: { type: 'offline-status' }, ports: [{ postMessage: value => status = value }] });
  assert.equal(status.ready, false);
  assert.equal(status.missing, 1);
  await h.run('message', { data: { type: 'repair-offline' }, ports: [{ postMessage: value => status = value }] });
  assert.equal(status.ready, false);
  h.setOnline(true);
  await h.run('message', { data: { type: 'repair-offline' }, ports: [{ postMessage: value => status = value }] });
  assert.equal(status.ready, true);
  assert.equal(status.missing, 0);
});

test('optional NumPy wheel is cacheable but not required for readiness', () => {
  const scope = 'https://example.test/ManimOnline/';
  const wheel = Assets.optional[0];
  assert.match(wheel, /numpy-.*\.whl$/);
  assert.equal(Assets.key({ method: 'GET', url: wheel, mode: 'cors' }, scope), wheel);
  assert.ok(!Assets.urls(scope).includes(wheel));
});
