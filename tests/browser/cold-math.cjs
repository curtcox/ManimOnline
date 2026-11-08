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
  const url='https://cdn.jsdelivr.net/npm/mathjax@3.2.2/es5/tex-svg.js';
  assert.equal(await page.evaluate(async url=>!!await(await caches.open('manimonline-runtime-v1')).match(url),url),false);
  assert.equal(await page.evaluate(async()=>{await ManimMath.load();return MathJax.version;}),'3.2.2');
  assert.equal(await page.evaluate(async url=>!!await(await caches.open('manimonline-runtime-v1')).match(url),url),true);
  await context.setOffline(true);await page.reload();await page.waitForSelector('body[data-ready="true"]');
  assert.equal(await page.evaluate(async()=>{await ManimMath.load();return MathJax.version;}),'3.2.2');
  await context.close();console.log(engine+': cold controlled math load and verified offline reload passed');
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
