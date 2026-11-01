/* URL, browser storage and recovery integration. Engines are real; no execution mocks. */
const assert = require('node:assert/strict'), fs = require('node:fs'), path = require('node:path'), http = require('node:http');
const { chromium, firefox, webkit } = require('playwright');
const root = path.resolve(__dirname, '../..');
const APP = 'ManimOnline';
const key = {R:'ronline:work',AudioOnline:'audioonline:document',GnuPlotOnline:'gnuplotonline:document',pages:'pagesonline:project',livelier:'livelier:draft',apptron:'apptron:draft',ManimOnline:'manimonline:draft'}[APP];
const source = label => ({R:`cat("${label}")`,AudioOnline:`from audio import *\nclass ${label}(Scene):\n    pass\n`,GnuPlotOnline:label==='URL'?'plot x':`set title "${label}"\nplot x*x`,pages:`<h1>${label}</h1>`,livelier:`console.log("${label}")`,apptron:`# apptron snapshot v1\n-- main.sh --\necho ${label}\n`,ManimOnline:`digraph { ${label} -> result }`})[APP];
const cid = text => { const data=Buffer.from(text),size=Buffer.alloc(6);size.writeUIntBE(data.length,0,6);return size.toString('base64url')+(data.length<=64?data:require('node:crypto').createHash('sha512').update(data).digest()).toString('base64url'); };
const engine=process.env.BROWSER||'chromium';
(async()=>{
 let server=http.createServer((request,response)=>{
  const name=new URL(request.url,'http://localhost').pathname;
  const file=path.join(root,name==='/'?'index.html':decodeURIComponent(name));
  if(!file.startsWith(root+path.sep)||!fs.existsSync(file)||fs.statSync(file).isDirectory()){response.writeHead(404);return response.end();}
  const type={'.html':'text/html','.css':'text/css','.js':'text/javascript','.mjs':'text/javascript','.wasm':'application/wasm','.json':'application/json','.svg':'image/svg+xml'}[path.extname(file)]||'application/octet-stream';
  response.writeHead(200,{'Content-Type':type,'Access-Control-Allow-Origin':'*',...(APP==='apptron'?{'Cross-Origin-Opener-Policy':'same-origin','Cross-Origin-Embedder-Policy':'require-corp'}:{})});response.end(fs.readFileSync(file));
 });
 let base;
 if(APP==='R'){const site=require('./server.cjs').createServer();server=site.server;base=(await site.start())+'/';}
 else{await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));base='http://127.0.0.1:'+server.address().port+'/';}
 let browser;
 try{browser=await ({chromium,firefox,webkit}[engine]).launch({headless:true,...(process.env.PLAYWRIGHT_EXECUTABLE_PATH?{executablePath:process.env.PLAYWRIGHT_EXECUTABLE_PATH}:{})});
 for(const old of [null,'LocalA','LocalB']){
  console.log(APP+': profile '+(old||'fresh'));
  const context=await browser.newContext({serviceWorkers:'block'}),page=await context.newPage();page.setDefaultTimeout(30000);
  // Serve identical pinned runtime bytes locally when present, as the full engine suites do.
  await context.route('https://cdn.jsdelivr.net/pyodide/v314.0.7/full/**',route=>{
   const name=new URL(route.request().url()).pathname.split('/').pop();
   const file=[path.join(root,'node_modules/pyodide',name),path.join(root,'.pyodide-cache',name)].find(file=>fs.existsSync(file));
   if(!file)return route.continue();return route.fulfill({body:fs.readFileSync(file),contentType:name.endsWith('.wasm')?'application/wasm':/\.m?js$/.test(name)?'text/javascript':name.endsWith('.json')?'application/json':'application/zip',headers:{'Access-Control-Allow-Origin':'*'}});
  });
  const errors=[];page.on('pageerror',error=>{if(!/ResizeObserver loop/.test(String(error))){console.error(APP+' page error: '+error);errors.push(String(error));}});
  page.on('dialog',async dialog=>{errors.push('Unexpected confirmation: '+dialog.message());await dialog.dismiss();});
  await page.goto(base+'?run=0#'+encodeURIComponent(source('URL')));await page.waitForSelector('#resume-work',{state:'attached'});if(!['R','GnuPlotOnline'].includes(APP))await page.waitForLoadState('networkidle');
  if(APP==='apptron')await page.evaluate(()=>ApptronOnline.initialized);
  if(APP==='R')await page.waitForFunction(()=>ROnline.client.active.ready&&(!ROnline.client.spare||ROnline.client.spare.ready),null,{timeout:120000});
  if(APP==='AudioOnline'||APP==='GnuPlotOnline')await page.waitForFunction(()=>/^Rendered/.test(document.getElementById('status').textContent),null,{timeout:120000});
  const makeDoc=src=>page.evaluate(({src,APP})=>{
   if(APP==='R')return {src,r:{stdin:'saved input\n',autorun:false}};
   if(APP==='GnuPlotOnline')return {src,gnuplot:{width:640,height:480,background:'transparent'},files:{'values.dat':'1 2\n2 3'}};
   if(APP==='AudioOnline')return {src,type:'python',settings:{sampleRate:22050,channels:1},files:{}};
   if(APP==='pages')return Project.single(src);
   if(APP==='apptron')return {source:src,provenance:{kind:'stored',detail:''}};
   if(APP==='ManimOnline')return {src,type:'graphviz',scene:'',engine:'dot',outputFormat:'svg',pos:{}};
   return HashBinDocuments.parse(src);
  },{src,APP});
  let raw=null;
  if(old){const document=await makeDoc(source(old));raw=await page.evaluate(({APP,document})=>APP==='apptron'?JSON.stringify({version:1,...document}):APP==='R'||APP==='pages'||APP==='ManimOnline'?JSON.stringify(document):HashBinDocuments.serialize(document),{APP,document});await page.evaluate(({key,raw})=>localStorage.setItem(key,raw),{key,raw});}
  const expected=source('URL'),document=await makeDoc(expected);
  const payload=await page.evaluate(({APP,document})=>APP==='apptron'?JSON.stringify({format:'hashbin-diagram',version:1,type:'apptron',src:document.source}):APP==='R'||APP==='ManimOnline'?HashBinDocuments.serialize(document):APP==='pages'?HashBinDocuments.serialize(document):HashBinDocuments.serialize(document),{APP,document});
  const packed=await page.evaluate(text=>LZString.compressToEncodedURIComponent(text),APP==='apptron'?expected:payload);
  const urls=[base+'?run=0&compressed='+await page.evaluate(text=>LZString.compressToEncodedURIComponent(text),expected),base+'?run=0#'+cid(expected)];
  if(!['ManimOnline','apptron'].includes(APP))urls.unshift(base+'?run=0&doc='+packed);
  const getSource=()=>page.evaluate(APP=>APP==='pages'?pagesApp.getProject().files.find(file=>file.name===pagesApp.getProject().active).text:APP==='apptron'?ApptronOnline.getSource():ace.edit('editor').getValue(),APP);
  const ready=async()=>{await page.waitForFunction(({APP,expected})=>{
   if(APP==='livelier'&&!globalThis.LivelierApp?.ready)return false;
   try{return (APP==='pages'?pagesApp.getProject().files.find(file=>file.name===pagesApp.getProject().active).text:APP==='apptron'?ApptronOnline.getSource():ace.edit('editor').getValue())===expected;}catch{return false;}
  },{APP,expected},{timeout:120000});if(APP==='apptron')await page.evaluate(()=>ApptronOnline.initialized);if(APP==='R')await page.waitForFunction(()=>ROnline.client.active.ready&&(!ROnline.client.spare||ROnline.client.spare.ready),null,{timeout:120000});if(APP==='AudioOnline'||APP==='GnuPlotOnline')await page.waitForFunction(()=>/^Rendered/.test(document.getElementById('status').textContent),null,{timeout:120000});if(!['R','GnuPlotOnline'].includes(APP))await page.waitForLoadState('networkidle');};
  for(const url of urls){console.log(APP+': '+(new URL(url).searchParams.has('doc')?'document':new URL(url).hash?'CID':'compressed source'));await page.goto(url);await ready();assert.equal(await getSource(),expected);if(new URL(url).searchParams.has('doc')){if(APP==='R')assert.deepEqual(await page.evaluate(()=>ROnline.snapshot().r),document.r);if(APP==='GnuPlotOnline'){assert.equal(await page.locator('#file-count').innerText(),'1');assert.equal(await page.locator('#width').inputValue(),'640');}if(APP==='AudioOnline')assert.equal(await page.locator('#sample-rate').inputValue(),'22050');}await page.reload();await ready();assert.equal(await page.evaluate(key=>localStorage.getItem(key),key),raw);}
  // A same-document link must also win over edits in this tab.
  await page.evaluate(({APP,text})=>{if(APP==='pages')pagesApp.editor.setValue(text,-1);else if(APP==='apptron')ApptronOnline.editor.setValue(text,-1);else ace.edit('editor').setValue(text,-1);},{APP,text:source('Current')});
  if(APP==='livelier')await page.evaluate(()=>LivelierApp.saveDraft());
  if(APP==='ManimOnline')await page.evaluate(()=>ace.edit('editor').commands.exec('insertstring',ace.edit('editor'),' '));
  await page.evaluate(hash=>{history.replaceState(null,'',location.pathname+'?run=0');location.hash=hash;},encodeURIComponent(expected));await ready();
  if(old){
   // The old draft remains available, even after a new document is edited.
   await page.locator('#resume-work').evaluate(button=>button.click());await page.waitForSelector('#draft-dialog[open]');if(old==='LocalB'){await page.setViewportSize({width:375,height:812});fs.mkdirSync(path.join(root,'test-results'),{recursive:true});await page.screenshot({path:path.join(root,'test-results',engine+'-draft-recovery.png')});}
   const index=await page.evaluate(text=>{const select=document.getElementById('saved-work');for(const option of select.options){select.value=option.value;select.onchange();if(document.getElementById('draft-preview').textContent.includes(text))return option.value;}},source(old).trim());
   assert.notEqual(index,undefined,'original draft must remain recoverable');await page.locator('#saved-work').selectOption(index);await page.locator('#restore-work').click();
   await page.waitForFunction(({APP,text})=>{try{return(APP==='pages'?pagesApp.getProject().files[0].text:APP==='apptron'?ApptronOnline.getSource():ace.edit('editor').getValue()).trim()===text.trim()}catch{return false;}},{APP,text:source(old)});
  }
  assert.deepEqual(errors,[]);await context.close();
 }
 console.log(APP+' '+engine+': URL independence, reload, fragment navigation and draft recovery passed');
 }finally{await browser?.close();await new Promise(resolve=>server.close(resolve));}
})().catch(error=>{console.error(error);process.exitCode=1;});
