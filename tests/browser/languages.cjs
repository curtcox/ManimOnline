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
// Stands in for the vendored SDK: popup approval, a blocked popup's redirect round trip, and revocation.
// The sandbox is the real one.
const sdk = `
export class HashBinClient {
 constructor(options) { this.options = options; }
 publish(content, { contentType, clientState }) {
  if (contentType !== 'application/json') throw Error('bad content type');
  return window.__hashbinUpload(content).then(({ cid }) => {
   if (localStorage.getItem('hashbin-test-mode') !== 'redirect') return { cid };
   sessionStorage.setItem('hashbin-test-state', JSON.stringify(clientState));
   location.href = new URL('./',location.href).href + '#hashbin_publish=test&cid=' + cid;
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
async function more(page){if(!await page.locator('#fk-more-drawer').isVisible())await page.click('#more-toggle');}
async function closeMore(page){if(await page.locator('#fk-more-drawer').isVisible())await page.click('#fk-more-drawer .fk-close');}
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
    await context.route('**/vendor/hashbin-sdk-v0.4.0.mjs', route => route.fulfill({body:sdk,contentType:'text/javascript'}));
    await context.route('https://hashbin.org/**', async route => { throw new Error('Unexpected HashBin path: '+new URL(route.request().url()).pathname); });
    await context.route('https://256t.us/**', async route => {
      const cid = new URL(route.request().url()).pathname.slice(1);
      if (cid === cidFor('slow '.repeat(20))) await new Promise(resolve => { releaseSlow = resolve; });
      await route.fulfill({status:docs.has(cid)?200:404,body:docs.get(cid)||'missing',headers:allow});
    });
    for (const type of ['modl','graphviz','manim']) {
      console.log(engine+': starting '+type);
      const page = await context.newPage();
      const errors = [];
      page.on('pageerror', error => { if (!/ResizeObserver loop/.test(String(error))) errors.push(String(error)); });
      await page.goto(base+'#'+encodeURIComponent(source[type]));
      await ready(page,type);
      if (type === 'modl') await csp.probe(page);
      if (type === 'manim') {
        await more(page);await page.locator('#scene-name').fill('Second');
        await page.locator('#scene-name').press('Enter');
        await ready(page,type);
      }
      if (type === 'graphviz') {
        await more(page);await page.selectOption('#renderer-mode','graphviz');
        await page.selectOption('#engine select','neato');
        await ready(page,type);
      }
      if (type === 'modl') {
        await closeMore(page);const node = page.locator('[data-node-id="a"]');
        const box = await node.boundingBox();
        await page.mouse.move(box.x+box.width/2,box.y+box.height/2);
        await page.mouse.down();
        await page.mouse.move(box.x+box.width/2+40,box.y+box.height/2+25);
        await page.mouse.up();
        await page.waitForFunction(() => new URL(location.href).searchParams.has('modlpos'));
        await page.locator('#share').click();
        assert.ok(new URL(await page.locator('#share-link').inputValue()).searchParams.has('modlpos'));
        await page.locator('#share-dialog .fk-close').click();await more(page);
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
      await more(page);console.log(engine+': saving '+type);await page.locator('#hashbin-save').click();
      await page.locator('#hashbin-confirm:not([disabled])').waitFor();
      assert.match(await page.locator('#hashbin-message').textContent(), /approve the save on hashbin\.org/);
      await page.locator('#hashbin-confirm').click();
      await page.waitForFunction(() => document.querySelector('#hashbin-status').textContent === 'Saved to HashBin.');
      await page.evaluate(() => localStorage.removeItem('hashbin-test-mode'));
      if (type === 'modl') {
        await ready(page,type);
        assert.equal(await page.evaluate(() => ace.edit('editor').getValue()),source[type]);
      }
      // A pending debounced source write must not replace the newly approved CID.
      await page.waitForTimeout(350);console.log(engine+': saved '+type);const url = page.url(), cid = new URL(url).hash.slice(1), payload = JSON.parse(docs.get(cid));
      assert.equal(payload.src,source[type]);
      assert.equal(payload.type,type);
      if (type === 'manim') assert.equal(payload.scene,'Second');
      if (type === 'graphviz') assert.equal(payload.graphviz.engine,'neato');
      await page.reload();
      await ready(page,type);
      assert.equal(await page.evaluate(() => ace.edit('editor').getValue()),source[type]);
      assert.equal(new URL(page.url()).hash.slice(1),cid);
      if (type === 'modl') {
        const savedPos = await page.evaluate(()=>ManimOnline.snapshot().pos);
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
    await more(page);await page.locator('#hashbin-cid').fill(inline);
    await page.locator('#hashbin-load').click();
    await ready(page,'graphviz');
    assert.equal(await page.evaluate(() => ace.edit('editor').getValue()),'digraph{a->b}');
    const slowCID = cidFor('slow '.repeat(20)); docs.set(slowCID,'slow '.repeat(20));
    await more(page);await page.locator('#hashbin-cid').fill(slowCID);
    await page.locator('#hashbin-load').click();
    for(let tries=0;!releaseSlow;tries++){if(tries>500)throw Error('Slow CID request never started: '+await page.locator('#hashbin-status').textContent());await new Promise(resolve=>setTimeout(resolve,10));}
    await page.evaluate(() => ace.edit('editor').setValue('digraph{newer->edit}',-1));
    releaseSlow();
    await ready(page,'graphviz');
    assert.equal(await page.evaluate(() => ace.edit('editor').getValue()),'digraph{newer->edit}');
    // Content servers cannot substitute documents behind a CID.
    const forged = JSON.stringify({format:'hashbin-diagram',version:1,src:'a square green A',pos:{}}); docs.set(cidFor(forged), forged.replace('green','red'));
    await more(page);await page.locator('#hashbin-cid').fill(cidFor(forged));
    await page.locator('#hashbin-load').click();
    await page.waitForFunction(() => /does not match its CID|byte limit/.test(document.querySelector('#hashbin-status').textContent));
    assert.equal(await page.evaluate(() => ace.edit('editor').getValue()),'digraph{newer->edit}');
    // Same-tab CID navigation loads the linked source and retains typed edits for recovery.
    await closeMore(page);await page.locator('#editor textarea').focus(); await page.keyboard.type(' ');
    await page.evaluate(cid => { location.hash = cid; }, legacyCID);
    await ready(page,'modl');
    assert.equal(await page.evaluate(() => ace.edit('editor').getValue()),JSON.parse(legacy).src);
    assert.match(await page.evaluate(() => localStorage.getItem('manimonline:draft')),/newer->edit/);
    await page.evaluate(cid => { location.hash = cid; }, inline);
    await ready(page,'graphviz');
    assert.equal(await page.evaluate(() => ace.edit('editor').getValue()),'digraph{a->b}');
    await page.close();
    csp.check();
    console.log(engine+': Graphviz, modl, Manim and HashBin round trips passed (mock service)');
  } finally { await browser.close(); }
}
(async () => { for (const engine of engines) await run(engine); })().catch(error => {console.error(error);process.exitCode=1;});
