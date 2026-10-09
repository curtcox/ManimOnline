const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const Assets = require('../offline-assets.js');
const { ExampleCatalog } = require('../src/examples.js');

function harness() {
  const handlers = {}, stores = new Map();
  let online = true, failURL = '', claims = 0;
  const caches = {
    open: async name => {
      if (!stores.has(name)) stores.set(name, new Map());
      const store = stores.get(name);
      return {
        match: async url => store.get(url)?.clone(),
        put: async (url, response) => store.set(url, response),
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
    if (!online || request.url === failURL) throw new Error('Offline');
    return new Response(request.url.endsWith('index.html') ? '<html>editor</html>' : 'asset');
  };
  vm.runInNewContext(fs.readFileSync('service-worker.js', 'utf8'), {
    OfflineAssets: Assets, importScripts() {}, caches, fetch, Request, Response,
    self: { registration: { scope: 'https://example.test/ManimOnline/' },
      addEventListener: (name, handler) => handlers[name] = handler,
      clients: { claim: async () => claims++ }, skipWaiting() {} }
  });
  const run = (type, args = {}) => {
    let result;
    handlers[type]({ ...args, waitUntil: promise => result = promise, respondWith: promise => result = promise });
    return result;
  };
  return { stores, run, setOnline: value => online = value, fail: url => failURL = url, get claims() { return claims; } };
}

test('offline manifest covers gallery, editor dependencies, and every local script', () => {
  for (const file of Assets.local) assert.ok(fs.existsSync(file), file);
  for (const example of ExampleCatalog) assert.ok(Assets.local.includes(example.path));
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
  h.stores.set('manimonline-offline-old', new Map());
  h.stores.set('unrelated-cache', new Map());
  await h.run('activate');
  assert.equal(h.claims, 1);
  assert.ok(!h.stores.has('manimonline-offline-old'));
  assert.ok(h.stores.has('unrelated-cache'));
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

test('failed preparation deletes incomplete new cache and preserves the old version', async () => {
  const h = harness();
  h.stores.set('manimonline-offline-old', new Map());
  h.fail(Assets.remote.at(-1));
  await assert.rejects(h.run('install'));
  assert.ok(!h.stores.has(Assets.VERSION));
  assert.ok(h.stores.has('manimonline-offline-old'));
});

test('partial cache offline provides a recovery page instead of a broken editor', async () => {
  const h = harness();
  await h.run('install');
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
