// Returning-visitor regression: cached pre-gallery editor/catalog -> current release.
// Uses a real service worker and the historical editor, retaining unsaved source.
// Usage: node tests/browser/upgrade.cjs [chromium|firefox|webkit ...]
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const playwright = require('playwright');
const { ExampleCatalog } = require('../../src/examples.js');
const root = path.resolve(__dirname, '../..');
const legacyHTML = fs.readFileSync(path.join(__dirname, 'fixtures/legacy-editor.html'));
const legacyCatalog = fs.readFileSync(path.join(__dirname, 'fixtures/legacy-examples.js'));
const engines = process.argv.slice(2).length ? process.argv.slice(2) : ['chromium', 'firefox', 'webkit'];
const legacyWorker = `
const name = 'manimonline-offline-legacy-gallery';
const base = self.registration.scope;
self.addEventListener('install', event => event.waitUntil((async () => {
 const cache = await caches.open(name);
 await cache.addAll(['index.html','src/examples.js'].map(p => new Request(new URL(p,base),{cache:'reload'})));
 await self.skipWaiting();
})()));
self.addEventListener('activate', event => event.waitUntil(self.clients.claim()));
self.addEventListener('fetch', event => {
 const url = new URL(event.request.url);
 url.search = ''; url.hash = '';
 if (url.href === base) url.pathname += 'index.html';
 if (![new URL('index.html',base).href,new URL('src/examples.js',base).href].includes(url.href)) return;
 event.respondWith(caches.open(name).then(cache => cache.match(url.href)).then(cached => cached || fetch(event.request)));
});
self.addEventListener('message', event => {
 if (event.data?.type === 'offline-status') event.ports[0]?.postMessage({ready:true,version:name,missing:0});
});
`;
async function run(engine) {
  let modern = false, release;
  const held = new Promise(resolve => { release = resolve; });
  const server = http.createServer(async (request, response) => {
    try {
      const url = new URL(request.url, 'http://localhost');
      if (url.pathname === '/ManimOnline') {
        response.writeHead(301, { Location: '/ManimOnline/' + url.search }); response.end(); return;
      }
      const file = url.pathname.slice('/ManimOnline/'.length) || 'index.html';
      let body;
      if (file === 'service-worker.js') {
        if (modern) await held;
        console.log(`${engine}: serving ${modern ? 'current' : 'historical'} worker`);
        body = modern ? fs.readFileSync(path.join(root, file)) : legacyWorker;
      } else if (!modern && file === 'index.html') body = legacyHTML;
      else if (!modern && file === 'src/examples.js') body = legacyCatalog;
      else if (file === 'offline-assets.js') {
        // This test isolates local-application upgrades; pinned runtime/CDN reuse
        // and readiness failures are covered by tests/offline.test.js.
        body = fs.readFileSync(path.join(root,file),'utf8') + '\nOfflineAssets.remote = []; OfflineAssets.optional = [];';
      } else {
        const location = path.resolve(root, file);
        if (!location.startsWith(root + path.sep)) throw Error('Invalid path');
        body = fs.readFileSync(location);
      }
      const types = {'.html':'text/html','.js':'text/javascript','.css':'text/css','.png':'image/png','.mp4':'video/mp4'};
      response.writeHead(200, { 'Content-Type': types[path.extname(file)] || 'text/plain', 'Cache-Control': 'no-store' });
      response.end(body);
    } catch (_) { console.error(`${engine}: missing ${request.url}`); response.writeHead(404); response.end('Missing'); }
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const base = `http://127.0.0.1:${server.address().port}/ManimOnline/`;
  let browser;
  try {
    browser = await playwright[engine].launch({ headless: true });
    const context = await browser.newContext();
    const editor = await context.newPage();
    await editor.goto(base + '?type=dot#' + encodeURIComponent('digraph { old -> editor }'));
    await editor.waitForFunction(() => navigator.serviceWorker.controller && document.querySelector('#offline-status').textContent === 'Ready offline');
    await editor.reload();
    assert.equal(await editor.locator('#example-picker').count(), 1);
    console.log(`${engine}: historical editor and cache installed`);
    const edits = 'digraph { unsaved -> "keep these edits" }';
    await editor.evaluate(source => ace.edit('editor').setValue(source, -1), edits);
    modern = true;
    const gallery = await context.newPage();
    await gallery.goto(new URL('gallery.html',base).href, {waitUntil:'domcontentloaded'});
    // The old worker serves its metadata-free catalog, while new gallery code
    // and covers come from the network. Hold the worker update to prove this state.
    await gallery.locator('#sample-type').selectOption('graphviz');
    await gallery.locator('#dot img').evaluate(img => img.decode());
    assert.equal(await gallery.locator('#dot .load').getAttribute('href'), './?url=examples%2Fbasic_graph.dot');
    assert.equal(await gallery.locator('[href="undefined"]').count(), 0);
    console.log(`${engine}: covers and links work with the cached metadata-free catalog`);
    const linked = await context.newPage();
    await linked.goto(new URL(await gallery.locator('#dot .load').getAttribute('href'),base).href, {waitUntil:'domcontentloaded'});
    await linked.waitForSelector('#review svg g.node');
    assert.equal(await linked.evaluate(() => ace.edit('editor').getValue()), fs.readFileSync(path.join(root,'examples/basic_graph.dot'),'utf8'));
    assert.equal(await linked.locator('#example-picker').count(), 1);
    console.log(`${engine}: gallery link loads DOT in the historical editor`);
    release();
    // Upgrades activate without closing tabs or clearing storage. Both documents
    // reload through the existing controllerchange/source-preservation hooks.
    await editor.waitForSelector('#sample-gallery', {timeout:30000}).catch(async error => {
      console.error(await editor.evaluate(async () => ({ status: document.querySelector('#offline-status').textContent,
        caches: await caches.keys(), registration: (await navigator.serviceWorker.getRegistrations()).map(r => ({ active:r.active?.state, waiting:r.waiting?.state, installing:r.installing?.state })) })));
      throw error;
    });
    console.log(`${engine}: returning editor upgraded automatically`);
    assert.equal(await editor.locator('#example-picker').count(), 0);
    await editor.waitForSelector('#review svg g.node');
    assert.equal(await editor.evaluate(() => ace.edit('editor').getValue()), edits);
    await gallery.waitForFunction(count => document.querySelectorAll('.card').length === count &&
      document.querySelector('#minimal .load')?.getAttribute('href').includes('example=minimal'), ExampleCatalog.length, {timeout:90000});
    await gallery.locator('#sample-type').selectOption('graphviz');
    await gallery.locator('#dot img').evaluate(img => img.decode());
    await gallery.screenshot({path:`/tmp/manimonline-upgrade-${engine}.png`});
    await editor.waitForFunction(() => document.querySelector('#offline-status').textContent === 'Ready offline');
    await context.setOffline(true);
    await gallery.reload();
    await gallery.locator('#sample-type').selectOption('graphviz');
    await gallery.locator('#dot img').evaluate(img => img.decode());
    console.log(`${engine}: cached legacy gallery links/covers, legacy editor loading, automatic upgrade, unsaved edits, and offline gallery passed`);
  } finally {
    release();
    await browser?.close();
    await new Promise(resolve => server.close(resolve));
  }
}
(async () => { for (const engine of engines) await run(engine); })().catch(error => { console.error(error); process.exitCode = 1; });
