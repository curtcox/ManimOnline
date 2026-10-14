// Browser-visible shortening diagnostics and recovery. Proxy requests are mocked.
// Usage: node tests/browser/sharing.cjs [baseUrl] [chromium|firefox|webkit ...]
const { strict: assert } = require('node:assert');
const playwright = require('playwright');
const base = process.argv[2] || 'http://localhost:8000/';
const engines = process.argv.slice(3).length ? process.argv.slice(3) : ['chromium','firefox','webkit'];
async function check(engine) {
  const browser = await playwright[engine].launch({headless:true});
  try {
    const context = await browser.newContext({serviceWorkers:'block'});
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror',error=>{if(!/ResizeObserver loop/.test(String(error)))errors.push(String(error));});
    let response, pendingRoute, requestCount = 0;
    await context.route(/^https:\/\/api\.allorigins\.win\/get\?/, async route => {
      requestCount++;
      if (response === 'blocked') return route.abort('failed');
      if (response === 'pending') { pendingRoute = route; return; }
      return route.fulfill({headers:{'access-control-allow-origin':'*'},...response});
    });
    await page.goto(base+'#'+encodeURIComponent('digraph{a->b}'));
    await page.waitForFunction(()=>document.querySelectorAll('#review svg g.node').length===2,null,{timeout:120000});
    await page.locator('#share').click();
    const sourceLink = await page.locator('#shareurl').inputValue();
    for (const [name, result, expected] of [
      ['proxy timeout',{status:522,body:'error code: 522'},/AllOrigins .*HTTP 522.*Retry later/],
      ['rate limit',{json:{contents:'Error: rate limit exceeded',status:{http_code:502}}},/is.gd .*rate limit exceeded.*Wait at least one minute/],
      ['database failure',{json:{contents:'Error, database insert failed',status:{http_code:200}}},/is.gd .*database insert failed.*problem with the shortening service.*Retry later/],
      ['large source',{json:{contents:'Error: URL too long.',status:{http_code:400}}},/URL too long.*Save to HashBin/],
      ['bad reply',{body:'not json',contentType:'text/plain'},/unreadable response.*Retry later/],
      ['unexpected URL',{json:{contents:'https://evil.test/link'}},/unexpected short-link address.*rejected/],
      ['opaque request failure','blocked',/did not provide a response.*content blockers/],
      ['untrusted provider text',{json:{contents:'Error: <img src=x onerror=alert(1)>'}},/is.gd .*<img/]
    ]) {
      response = result;
      await page.locator('#shorten-share').click();
      await page.waitForFunction(()=>!document.querySelector('#shorten-share').disabled);
      const message = await page.locator('#share-status').textContent();
      assert.match(message,expected,name);
      assert.match(message,/source link above is still ready to copy/);
      assert.equal(await page.locator('#shareurl').inputValue(),sourceLink,name);
      assert.equal(await page.locator('#share-status img').count(),0);
    }
    await context.setOffline(true);
    const beforeOffline = requestCount;
    await page.locator('#shorten-share').click();
    await page.waitForFunction(()=>!document.querySelector('#shorten-share').disabled);
    assert.match(await page.locator('#share-status').textContent(),/offline.*Reconnect/);
    assert.equal(requestCount,beforeOffline);
    await context.setOffline(false);
    response = {json:{contents:'https://is.gd/example'}};
    await page.locator('#shorten-share').click();
    await page.waitForFunction(()=>document.querySelector('#share-status').textContent==='Short link ready.');
    assert.equal(await page.locator('#shareurl').inputValue(),'https://is.gd/example');
    await page.locator('#share').click();
    response = 'pending';
    await page.locator('#shorten-share').click();
    for (let i=0;i<100&&!pendingRoute;i++) await new Promise(resolve=>setTimeout(resolve,20));
    assert.ok(pendingRoute,'pending proxy request');
    await page.evaluate(()=>ace.edit('editor').setValue('digraph{newer->edit}',-1));
    await pendingRoute.fulfill({status:522,body:'late error'}).catch(()=>{});
    assert.equal(await page.locator('#share-status').textContent(),'');
    assert.equal(await page.locator('#shareurl').inputValue(),'');
    assert.deepEqual(errors,[]);
    console.log(engine+': shortening diagnostics, source-link fallback, retry and stale-error checks passed');
  } finally { await browser.close(); }
}
(async()=>{for(const engine of engines)await check(engine);})().catch(error=>{console.error(error);process.exitCode=1;});
