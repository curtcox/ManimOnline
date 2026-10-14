// Three-language rendering and HashBin UI round trips with a deterministic service.
// Real Pyodide/Graphviz/modl run; only HashBin authentication, pricing/storage are mocked.
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
const sdk = `export class HashBinClient {
 constructor(options) { this.options = options; }
 getTokens() { return JSON.parse(localStorage.getItem('hashbin-test-tokens') || 'null'); }
 clearTokens() { localStorage.removeItem('hashbin-test-tokens'); }
 async authorize(options) {
  if (options.mode !== 'manual' || options.scopes.join(' ') !== 'content:write balance:read') throw Error('bad authorization');
  return {state:'test-state',url:'https://hashbin.org/oauth/authorize?redirect_uri='+encodeURIComponent(this.options.redirectUri)+'&state=test-state'};
 }
 async handleCallback() { localStorage.setItem('hashbin-test-tokens',JSON.stringify({refreshToken:'mock',accessToken:'mock',expiresAt:Date.now()+3600000})); }
 async refreshAccessToken() { return this.getTokens(); }
 async authorizedFetch(path, options) { return fetch('https://hashbin.org'+path,{...options,headers:{...options?.headers,Authorization:'Bearer mock'}}); }
}`;
async function ready(page, type) {
  const selector = type === 'graphviz' ? '#review svg g.node' : type === 'modl' ? '#review svg [data-node-id]' : '.manim-player svg';
  await page.waitForFunction(selector => document.querySelector(selector) || document.querySelector('#review.error'), selector, {timeout:120000});
  assert.equal(await page.locator('#error').textContent(), '');
  await page.waitForFunction(type => document.querySelector('#type-indicator').className === type, type);
}
async function run(engine) {
  const browser = await playwright[engine].launch({headless:true});
  try {
    const context = await browser.newContext({ serviceWorkers: 'block' });
    const docs = new Map();
    let uploads = 0, authorizations = 0, releaseSlow;
    // WebKit interception can omit uploaded file bytes. Inspect the actual Blob
    // at the mocked service boundary instead of parsing browser-specific multipart.
    await context.exposeBinding('__hashbinUpload', async (_, payload, authorization) => {
      assert.equal(authorization, 'Bearer mock');
      const cid = cidFor(payload);
      docs.set(cid, payload);
      uploads++;
      return { cid, cost_cents: 1 };
    });
    await context.addInitScript(() => {
      const nativeFetch = window.fetch.bind(window);
      window.fetch = async (url, options) => {
        if (String(url) === 'https://hashbin.org/api/content') {
          const data = await window.__hashbinUpload(await options.body.get('content').text(), options.headers.Authorization);
          return new Response(JSON.stringify(data), { status: 201, headers: { 'Content-Type': 'application/json' } });
        }
        return nativeFetch(url, options);
      };
    });
    const allow = {'access-control-allow-origin':'*','access-control-allow-headers':'Authorization, Content-Type','access-control-allow-methods':'GET, POST, OPTIONS'};
    await context.route('https://hashbin.org/**', async route => {
      const request = route.request(), url = new URL(request.url());
      if (request.method() === 'OPTIONS') return route.fulfill({status:204,headers:allow});
      if (url.pathname === '/sdk/hashbin.js') return route.fulfill({body:sdk,contentType:'text/javascript',headers:allow});
      if (url.pathname === '/oauth/authorize') {
        authorizations++;
        assert.equal(url.searchParams.get('redirect_uri'), new URL(base).origin + new URL(base).pathname.replace(/index\.html$/, ''));
        // WebKit's interception cannot fulfill a redirect status; navigate from
        // a tiny approval stand-in while preserving the tab's session storage.
        return route.fulfill({contentType:'text/html',body:'<script>location.href='+JSON.stringify(base+'?code=test-code&state=test-state')+';</script>'});
      }
      let data;
      if (url.pathname === '/api/account/settings') data = { default_retention_months: '2' };
      else if (url.pathname === '/api/balance') data = {balance_cents:100};
      else if (url.pathname === '/api/payments/calculate') data = {cost_cents:1};
      else throw new Error('Unexpected HashBin path: '+url.pathname);
      await route.fulfill({json:data,headers:allow});
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
      }
      await page.locator('#hashbin-save').click();
      await page.locator('#hashbin-confirm:not([disabled])').waitFor();
      if (type === 'modl') {
        assert.equal(await page.locator('#hashbin-confirm').textContent(),'Connect to HashBin');
        await page.locator('#hashbin-confirm').click();
        await page.waitForFunction(() => document.querySelector('#hashbin-status')?.textContent.startsWith('Connected'));
        await ready(page,type);
        assert.equal(await page.evaluate(() => ace.edit('editor').getValue()),source[type]);
        await page.locator('#hashbin-save').click();
        await page.locator('#hashbin-confirm:not([disabled])').waitFor();
      }
      assert.match(await page.locator('#hashbin-message').textContent(), /Cost: \$0.01/);
      await page.locator('#hashbin-confirm').click();
      await page.waitForFunction(() => document.querySelector('#hashbin-status').textContent === 'Saved to HashBin.');
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
    assert.equal(authorizations,1);
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
    const slowCID = cidFor('slow '.repeat(20)); docs.set(slowCID,legacy);
    await page.locator('#hashbin-cid').fill(slowCID);
    await page.locator('#hashbin-load').click();
    while (!releaseSlow) await new Promise(resolve => setTimeout(resolve,10));
    await page.evaluate(() => ace.edit('editor').setValue('digraph{newer->edit}',-1));
    releaseSlow();
    await ready(page,'graphviz');
    assert.equal(await page.evaluate(() => ace.edit('editor').getValue()),'digraph{newer->edit}');
    await page.close();
    console.log(engine+': Graphviz, modl, Manim and HashBin round trips passed (mock service)');
  } finally { await browser.close(); }
}
(async () => { for (const engine of engines) await run(engine); })().catch(error => {console.error(error);process.exitCode=1;});
