// Three-language rendering and HashBin UI round trips with a deterministic service.
// Real Pyodide/Graphviz/modl run; only HashBin Publish approval and storage are mocked.
// Usage: node tests/browser/languages.cjs [baseUrl] [chromium|firefox|webkit ...]
const { strict: assert } = require('node:assert');
const { createHash } = require('node:crypto');
const playwright = require('playwright');
const base = process.argv[2] || 'http://localhost:8000/';
const engines = process.argv.slice(3).length ? process.argv.slice(3) : ['chromium', 'firefox', 'webkit'];
const source = {
  graphviz: 'digraph G { a [label="π"]; a -> b }',
  modl: 'white\na square blue "Edit π"\nb circle green Preview\na -> b dashed purple Render',
  manim: 'from manim import *\nclass First(Scene):\n def construct(self): self.add(Square())\nclass Second(Scene):\n def construct(self):\n  self.play(Create(Circle()), run_time=.2)\n  self.wait(.2)'
};
function cidFor(text) {
  const bytes = Buffer.from(text), prefix = Buffer.alloc(6);
  prefix.writeUIntBE(bytes.length, 0, 6);
  return prefix.toString('base64url') + (bytes.length <= 64 ? bytes : createHash('sha512').update(bytes).digest()).toString('base64url');
}
// Stands in for the pinned SDK: popup approval, a blocked popup's redirect round trip, and revocation.
const sdk = `export class HashBinClient {
 constructor(options) { this.options = options; }
 publish(content, { contentType, clientState }) {
  if (contentType !== 'application/json') throw Error('bad content type');
  return window.__hashbinUpload(content).then(({ cid }) => {
   if (localStorage.getItem('hashbin-test-mode') !== 'redirect') return { cid };
   sessionStorage.setItem('hashbin-test-state', JSON.stringify(clientState));
   location.href = this.options.redirectUri + '#hashbin_publish=test&cid=' + cid;
   return { redirected: true };
  });
 }
 async handlePublishCallback({ hash }) {
  const clientState = JSON.parse(sessionStorage.getItem('hashbin-test-state'));
  sessionStorage.removeItem('hashbin-test-state');
  return { cid: new URLSearchParams(hash.slice(1)).get('cid'), clientState };
 }
 async disconnect() { localStorage.removeItem('hashbin:tokens:' + this.options.clientId); localStorage.setItem('hashbin-test-revoked', this.options.clientId); }
}`;
async function ready(page, type) {
  const selector = type === 'graphviz' ? '#review svg g.node' : type === 'modl' ? '#review svg [data-node-id]' : '.manim-player svg';
  await page.waitForFunction(selector => document.querySelector(selector) || document.querySelector('#review.error'), selector, {timeout:120000});
  assert.equal(await page.locator('#error').textContent(), '');
  await page.waitForFunction(type => document.querySelector('#type-indicator').className === type, type);
}
async function run(engine) {
  const browser = await playwright[engine].launch({headless:true});
  const csp = require('./csp.cjs')(browser);
  try {
    const context = await browser.newContext({ serviceWorkers: 'block' });
    const docs = new Map();
    let uploads = 0, releaseSlow;
    await context.exposeBinding('__hashbinUpload', async (_, payload) => {
      const cid = cidFor(payload);
      docs.set(cid, payload);
      uploads++;
      return { cid };
    });
    const allow = {'access-control-allow-origin':'*'};
    await context.route('https://hashbin.org/**', async route => {
      const url = new URL(route.request().url());
      if (url.pathname === '/sdk/v0.2.0/hashbin.js') return route.fulfill({body:sdk,contentType:'text/javascript',headers:allow});
      throw new Error('Unexpected HashBin path: '+url.pathname);
    });
    await context.route('https://256t.us/**', async route => {
      const cid = new URL(route.request().url()).pathname.slice(1);
      if (cid === cidFor('slow '.repeat(20))) await new Promise(resolve => { releaseSlow = resolve; });
      await route.fulfill({status:docs.has(cid)?200:404,body:docs.get(cid)||'missing',headers:allow});
    });
    for (const type of ['modl','graphviz','manim']) {
      const page = await context.newPage();
      const errors = [];
      page.on('pageerror', error => { if (!/ResizeObserver loop/.test(String(error))) errors.push(String(error)); });
      await page.goto(base+'#'+encodeURIComponent(source[type]));
      await ready(page,type);
      if (type === 'modl') await csp.probe(page);
      if (type === 'manim') {
        await page.locator('#scene-name').fill('Second');
        await page.locator('#scene-name').press('Enter');
        await ready(page,type);
      }
      if (type === 'graphviz') {
        await page.selectOption('#renderer-mode','graphviz');
        await page.selectOption('#engine select','neato');
        await ready(page,type);
      }
      if (type === 'modl') {
        const node = page.locator('[data-node-id="a"]');
        const box = await node.boundingBox();
        await page.mouse.move(box.x+box.width/2,box.y+box.height/2);
        await page.mouse.down();
        await page.mouse.move(box.x+box.width/2+40,box.y+box.height/2+25);
        await page.mouse.up();
        await page.waitForFunction(() => new URL(location.href).searchParams.has('modlpos'));
        await page.locator('#share').click();
        assert.ok(new URL(await page.locator('#shareurl').inputValue()).searchParams.has('modlpos'));
        assert.equal(await page.locator('#download').getAttribute('download'),'modl.svg');
        await page.locator('#modl-zoom-in').click();
        assert.equal(await page.locator('#modl-zoom').textContent(),'1.2×');
        // Lazy export must include the latest camera even without another render.
        const downloadEvent = page.waitForEvent('download');
        await page.locator('#download').click();
        await downloadEvent;
        const exported = decodeURIComponent((await page.locator('#download').getAttribute('href')).split(',').slice(1).join(','));
        assert.ok(exported.includes('scale(1.2)'));
        assert.ok(exported.includes('data-node-id="a"'));
        await page.locator('#modl-reset-view').click();
        assert.equal(await page.locator('#modl-zoom').textContent(),'1×');
      }
      if (type === 'modl') {
        // Tokens from the earlier OAuth flow are revoked server-side, then cleared.
        const clientId = await page.evaluate(() => document.querySelector('meta[name="hashbin-client-id"]').content);
        await page.evaluate(id => localStorage.setItem('hashbin:tokens:' + id, '{"refreshToken":"old"}'), clientId);
        await page.reload();
        await ready(page,type);
        await page.waitForFunction(id => localStorage.getItem('hashbin-test-revoked') === id && !localStorage.getItem('hashbin:tokens:' + id), clientId);
        // A blocked popup falls back to a redirect; the source and layout survive it.
        await page.evaluate(() => localStorage.setItem('hashbin-test-mode', 'redirect'));
      }
      await page.locator('#hashbin-save').click();
      await page.locator('#hashbin-confirm:not([disabled])').waitFor();
      assert.match(await page.locator('#hashbin-message').textContent(), /approve the save on hashbin\.org/);
      await page.locator('#hashbin-confirm').click();
      await page.waitForFunction(() => document.querySelector('#hashbin-status').textContent === 'Saved to HashBin.');
      await page.evaluate(() => localStorage.removeItem('hashbin-test-mode'));
      if (type === 'modl') {
        await ready(page,type);
        assert.equal(await page.evaluate(() => ace.edit('editor').getValue()),source[type]);
      }
      const url = page.url(), cid = new URL(url).hash.slice(1), payload = JSON.parse(docs.get(cid));
      assert.equal(payload.src,source[type]);
      assert.equal(payload.type,type);
      if (type === 'manim') assert.equal(payload.scene,'Second');
      if (type === 'graphviz') assert.equal(payload.graphviz.engine,'neato');
      await page.reload();
      await ready(page,type);
      assert.equal(await page.evaluate(() => ace.edit('editor').getValue()),source[type]);
      assert.equal(new URL(page.url()).hash.slice(1),cid);
      if (type === 'modl') {
        const savedPos = JSON.parse(new URL(page.url()).searchParams.get('modlpos'));
        assert.deepEqual(savedPos,payload.pos);
        await page.screenshot({path:process.env.MODL_SCREENSHOT || '/tmp/manimonline-modl-'+engine+'.png'});
      }
      if (type === 'manim') assert.equal(await page.locator('#scene-name').inputValue(),'Second');
      if (type === 'graphviz') assert.equal(await page.locator('#engine select').inputValue(),'neato');
      assert.deepEqual(errors,[]);
      await page.close();
    }
    assert.equal(uploads,3);
    const page = await context.newPage();
    const legacy = JSON.stringify({format:'hashbin-diagram',version:1,src:'a square red A\na -> b',pos:{a:[100,100],b:[300,200]}});
    const legacyCID = cidFor(legacy); docs.set(legacyCID,legacy);
    await page.goto(base+'#'+legacyCID);
    await ready(page,'modl');
    assert.equal(await page.evaluate(() => ace.edit('editor').getValue()),JSON.parse(legacy).src);
    const inline = cidFor('digraph{a->b}');
    await page.locator('#hashbin-cid').fill(inline);
    await page.locator('#hashbin-load').click();
    await ready(page,'graphviz');
    assert.equal(await page.evaluate(() => ace.edit('editor').getValue()),'digraph{a->b}');
    const slowCID = cidFor('slow '.repeat(20)); docs.set(slowCID,'slow '.repeat(20));
    await page.locator('#hashbin-cid').fill(slowCID);
    await page.locator('#hashbin-load').click();
    while (!releaseSlow) await new Promise(resolve => setTimeout(resolve,10));
    await page.evaluate(() => ace.edit('editor').setValue('digraph{newer->edit}',-1));
    releaseSlow();
    await ready(page,'graphviz');
    assert.equal(await page.evaluate(() => ace.edit('editor').getValue()),'digraph{newer->edit}');
    // Content servers cannot substitute documents behind a CID.
    const forged = JSON.stringify({format:'hashbin-diagram',version:1,src:'a square green A',pos:{}}); docs.set(cidFor(forged), forged.replace('green','red'));
    await page.locator('#hashbin-cid').fill(cidFor(forged));
    await page.locator('#hashbin-load').click();
    await page.waitForFunction(() => /does not match its CID/.test(document.querySelector('#hashbin-status').textContent));
    assert.equal(await page.evaluate(() => ace.edit('editor').getValue()),'digraph{newer->edit}');
    // A CID link opened in the same tab asks before replacing typed edits.
    await page.locator('#editor textarea').focus();
    await page.keyboard.type(' ');
    page.once('dialog', dialog => dialog.dismiss());
    await page.evaluate(cid => { location.hash = cid; }, legacyCID);
    await page.waitForTimeout(300);
    assert.equal(await page.evaluate(() => ace.edit('editor').getValue()).then(value => value.includes('digraph{newer->edit}')), true);
    page.once('dialog', dialog => dialog.accept());
    await page.evaluate(cid => { location.hash = cid; }, inline);
    await ready(page,'graphviz');
    assert.equal(await page.evaluate(() => ace.edit('editor').getValue()),'digraph{a->b}');
    await page.close();
    csp.check();
    console.log(engine+': Graphviz, modl, Manim and HashBin round trips passed (mock service)');
  } finally { await browser.close(); }
}
(async () => { for (const engine of engines) await run(engine); })().catch(error => {console.error(error);process.exitCode=1;});
