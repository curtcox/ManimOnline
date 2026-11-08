const {chromium,firefox,webkit}=require('playwright');
const assert=require('node:assert/strict');
const base=process.argv[2]||'http://127.0.0.1:8000/',engine=process.argv[3]||'chromium';
(async()=>{
 const browser=await({chromium,firefox,webkit}[engine]).launch();
 try{
  const context=await browser.newContext(),page=await context.newPage();
  await page.goto(base+'#'+encodeURIComponent('digraph { cold -> math }'));
  await page.waitForSelector('body[data-ready="true"]');
  await page.waitForFunction(()=>!!navigator.serviceWorker.controller);
  await page.waitForFunction(()=>document.getElementById('offline-status').textContent==='Diagrams ready offline',null,{timeout:90000});
  // CI mirrors the identical CDN bytes locally; check the cached module in either environment.
  const cached=()=>page.evaluate(async()=>[...await(await caches.open('manimonline-runtime-v1')).keys()].some(request=>new URL(request.url).pathname.endsWith('/tex-svg.js')));
  assert.equal(await cached(),false);
  assert.equal(await page.evaluate(async()=>{await ManimMath.load();return MathJax.version;}),'3.2.2');
  assert.equal(await cached(),true);
  await context.setOffline(true);await page.reload();await page.waitForSelector('body[data-ready="true"]');
  assert.equal(await page.evaluate(async()=>{await ManimMath.load();return MathJax.version;}),'3.2.2');
  await context.close();console.log(engine+': cold controlled math load and verified offline reload passed');
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
