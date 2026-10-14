// Actual bundled covers/video playback, gallery navigation, and stale editor loads.
// Usage: node tests/browser/gallery.cjs [baseUrl] [chromium|firefox|webkit ...]
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const playwright = require('playwright');
const { ExampleCatalog } = require('../../src/examples.js');
const base = process.argv[2] || 'http://localhost:8000/';
const engines = process.argv.slice(3).length ? process.argv.slice(3) : ['chromium', 'firefox', 'webkit'];
const sourceFor = id => fs.readFileSync(path.join(__dirname, '../..', ExampleCatalog.find(example => example.id === id).path), 'utf8');
async function ready(page, type) {
  const selector = type === 'manim' ? '.manim-player svg' : type === 'modl' ? '#review [data-node-id]' : '#review svg g.node';
  await page.waitForFunction(selector => document.querySelector(selector) || document.querySelector('#review.error'), selector, { timeout: 120000 });
  assert.equal(await page.locator('#error').textContent(), '');
}
(async () => {
  for (const engine of engines) {
    const browser = await playwright[engine].launch({ headless: true });
    try {
      const context = await browser.newContext({ serviceWorkers: 'block' });
      const page = await context.newPage();
      const requests = [];
      page.on('request', request => requests.push(request.url()));
      await page.goto(new URL('gallery.html', base).href);
      assert.equal(await page.locator('.card').count(), ExampleCatalog.length);
      // Browse all covers, catching missing or invalid preview assets as they lazy-load.
      for (const example of ExampleCatalog) {
        const cover = page.locator(`#${example.id} img`);
        await cover.scrollIntoViewIfNeeded();
        await page.waitForFunction(id => {
          const img = document.querySelector(`#${id} img`);
          return img.complete && img.naturalWidth > 0;
        }, example.id);
      }
      assert.ok(!requests.some(url => /pyodide|unified-worker|\.mp4/.test(url)), 'gallery browsing loads covers without Python or video');
      console.log(`${engine}: all ${ExampleCatalog.length} gallery covers loaded without Python or video`);
      await page.locator('#sample-search').fill('first animation');
      assert.equal(await page.locator('.card:visible').count(), 1);
      await page.locator('#minimal .play').click();
      await page.waitForFunction(() => document.querySelector('#minimal video').currentTime > .2);
      assert.equal(await page.locator('#minimal img').isVisible(), false);
      await page.locator('#sample-search').fill('');
      await page.locator('#math .play').click();
      await page.waitForFunction(() => document.querySelector('#math video').currentTime > .2);
      assert.equal(await page.locator('#minimal video').evaluate(video => video.paused), true);
      console.log(`${engine}: gallery video playback and single-preview playback passed`);
      await page.locator('#sample-search').fill('nothing-matches-this');
      assert.equal(await page.locator('#no-samples').isVisible(), true);
      await page.locator('#sample-search').fill('');
      await page.locator('#sample-type').selectOption('graphviz');
      assert.equal(await page.locator('.card:visible').count(), 1);
      await page.locator('#dot .load').click();
      await ready(page, 'graphviz');
      assert.equal(await page.evaluate(() => ace.edit('editor').getValue()), sourceFor('dot'));
      assert.equal(await page.locator('#example-picker').count(), 0);
      assert.equal(await page.locator('#sample-gallery').getAttribute('href'), 'gallery.html');
      const popupReady = page.waitForEvent('popup');
      await page.locator('#sample-gallery').click();
      const popup = await popupReady;
      await popup.waitForSelector('.card');
      assert.equal(await page.evaluate(() => ace.edit('editor').getValue()), sourceFor('dot'));
      await popup.close();
      console.log(`${engine}: DOT load and gallery navigation preserve the editor`);
      for (const [id, type] of [['modl', 'modl'], ['minimal', 'manim']]) {
        await page.goto(new URL(`?example=${id}&type=dot&scene=Old#old-source`, base).href);
        await ready(page, type);
        assert.equal(await page.evaluate(() => ace.edit('editor').getValue()), sourceFor(id));
        assert.equal(await page.locator('#renderer-mode').inputValue(), 'auto');
        assert.equal(await page.locator('#scene-name').inputValue(), '');
        assert.ok(!new URL(page.url()).searchParams.has('example'));
      }
      const edited = 'digraph { fresh -> edits }';
      await page.evaluate(source => ace.edit('editor').setValue(source, -1), edited);
      await ready(page, 'graphviz');
      await page.reload();
      await ready(page, 'graphviz');
      assert.equal(await page.evaluate(() => ace.edit('editor').getValue()), edited);
      console.log(`${engine}: Manim/modl editor links and edited-source reload passed`);
      let release;
      const requestSeen = page.waitForRequest('**/examples/minimal_scene.py');
      const held = new Promise(resolve => { release = resolve; });
      await page.route('**/examples/minimal_scene.py', async route => {
        await held;
        await route.fulfill({ contentType: 'text/plain', body: sourceFor('minimal') });
      });
      await page.goto(new URL('?example=minimal', base).href, { waitUntil: 'domcontentloaded' });
      await requestSeen;
      await page.evaluate(source => ace.edit('editor').setValue(source, -1), edited);
      release();
      await ready(page, 'graphviz');
      assert.equal(await page.evaluate(() => ace.edit('editor').getValue()), edited);
      await page.goto(new URL('?example=unlisted', base).href);
      await page.waitForFunction(() => document.querySelector('#example-status').textContent.includes('Choose an example'));
      // Isolate media caches from earlier playback. An explicit missing-file response
      // produces a media error consistently; browsers may retry an aborted request.
      const mobileContext = await browser.newContext({ serviceWorkers: 'block', viewport: { width: 390, height: 844 } });
      const mobile = await mobileContext.newPage();
      await mobile.goto(new URL('gallery.html', base).href);
      await mobile.locator('#sample-search').fill('first animation');
      assert.ok(await mobile.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'mobile gallery fits viewport');
      await mobile.route('**/gallery/previews/minimal.mp4', route => route.fulfill({ status: 404, contentType: 'text/plain', body: 'Missing preview' }));
      const missingResponse = mobile.waitForResponse(response => response.url().endsWith('/minimal.mp4') && response.status() === 404);
      await mobile.locator('#minimal .play').click();
      await missingResponse;
      await mobile.waitForSelector('#minimal .preview-error');
      assert.equal(await mobile.locator('#minimal .load').isVisible(), true);
      await mobile.unroute('**/gallery/previews/minimal.mp4');
      await mobile.locator('#minimal .play').click();
      await mobile.waitForFunction(() => document.querySelector('#minimal video').currentTime > .2);
      assert.equal(await mobile.locator('#minimal .preview-error').count(), 0);
      await mobile.screenshot({ path: `/tmp/manimonline-gallery-${engine}.png` });
      await mobileContext.close();
      console.log(`${engine}: gallery covers, playback, filters, editor links, reload, stale loads, and mobile passed`);
    } finally { await browser.close(); }
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
