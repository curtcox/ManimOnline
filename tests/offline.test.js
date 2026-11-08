const{test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),{createHash}=require('node:crypto');
const Assets=require('../offline-assets.js'),{createRuntime,CACHE}=require('../src/offline-runtime.js'),{ExampleCatalog}=require('../src/examples.js');
const sha=value=>createHash('sha256').update(value).digest('hex');
function harness(){
 const stores=new Map(),calls=[];let online=true,poison=false,fail='';
 const caches={open:async name=>{if(!stores.has(name))stores.set(name,new Map());const values=stores.get(name);return{match:async key=>values.get(key)?.clone(),put:async(key,value)=>values.set(key,value.clone()),delete:async key=>values.delete(key)};},match:async key=>{for(const store of stores.values())if(store.has(key))return store.get(key).clone();}};
 const context={Response,crypto,URL};vm.runInNewContext(fs.readFileSync('vendor/hashbin-cache-v0.4.0.js','utf8'),context);
 const manifest={runtime:Assets.runtime,optional:Assets.optional,runtimeHashes:Object.fromEntries([...Assets.runtime,...Assets.optional].map(url=>[url,sha('runtime')]))};
 const runtime=createRuntime({manifest,scope:'https://example.test/ManimOnline/',caches,verify:context.HashBinCache.verify,fetch:async(request,options={})=>{if(request.mode==='no-cors'&&(options.mode!=='cors'||options.credentials!=='omit'))return Response.error();const url=typeof request==='string'?request:request.url;calls.push(url);if(!online||url===fail)throw Error('Offline');return new Response(poison?'altered':'runtime');}});
 return{runtime,stores,calls,caches,setOnline:value=>online=value,setPoison:value=>poison=value,fail:value=>fail=value};
}
test('application allowlist contains every example, cover, local script and generated document',()=>{
 for(const file of Assets.assets.filter(file=>!file.startsWith('https:')))assert.ok(fs.existsSync(file),file);
 for(const example of ExampleCatalog){assert.ok(Assets.assets.includes(example.path));assert.ok(Assets.assets.includes(example.cover));assert.ok(!Assets.assets.includes(example.video));}
 for(const [,path]of fs.readFileSync('index.html','utf8').matchAll(/<script(?: type="module")? src="([^"?]+)(?:\?[^"]*)?"/g))assert.ok(Assets.assets.includes(path),path);
 for(const file of Assets.assets.filter(file=>!file.startsWith('https:')))assert.equal(Assets.hashes[file],sha(fs.readFileSync(file)),file);
});
test('Python/math and optional wheels are deferred and separately pinned',()=>{
 assert.ok(Assets.runtime.some(url=>url.endsWith('pyodide.asm.wasm')));
 for(const url of [...Assets.runtime,...Assets.optional]){assert.ok(!Assets.assets.includes(url));assert.match(Assets.runtimeHashes[url],/^[a-f0-9]{64}$/);}
 assert.match(Assets.optional[0],/numpy-.*\.whl$/);assert.ok(CACHE.startsWith('manimonline-'));
});
test('readiness requires every runtime asset; explicit preparation never downloads optional wheels',async()=>{
 const h=harness();await h.runtime.carry();assert.deepEqual(h.calls,[]);assert.equal((await h.runtime.status()).ready,false);
 await h.runtime.download();assert.equal((await h.runtime.status()).ready,true);assert.deepEqual(h.calls,Assets.runtime);
});
test('upgrades carry only matching immutable bytes and leave unrelated caches untouched',async()=>{
 const h=harness(),old=new Map(Assets.runtime.map(url=>[url,new Response('runtime')]));old.set(Assets.runtime[0],new Response('altered'));
 h.stores.set('manimonline-offline-old',old);h.stores.set('sibling-cache',new Map([['secret',new Response('private')]]));
 await h.runtime.carry();assert.equal((await h.runtime.status()).missing,1);assert.deepEqual(h.calls,[]);assert.ok(h.stores.has('sibling-cache'));
 await h.runtime.download();assert.equal(h.calls.length,1);assert.equal((await h.runtime.status()).ready,true);
});
test('altered cached runtime is refused offline and repaired only with verified network bytes',async()=>{
 const h=harness();await h.runtime.download();h.stores.get(CACHE).set(Assets.runtime[0],new Response('poisoned'));h.setOnline(false);
 assert.equal((await h.runtime.status()).ready,false);await assert.rejects(h.runtime.respond(Assets.runtime[0]),/Offline/);
 h.setOnline(true);h.setPoison(true);await assert.rejects(h.runtime.respond(Assets.runtime[0]),/verification/);assert.equal((await h.runtime.status()).ready,false);
 h.setPoison(false);assert.equal(await(await h.runtime.respond(Assets.runtime[0])).text(),'runtime');assert.equal((await h.runtime.status()).ready,true);
});
test('a failed preparation retains valid bytes and never promises full readiness',async()=>{
 const h=harness();h.fail(Assets.runtime[2]);await assert.rejects(h.runtime.download());assert.equal((await h.runtime.status()).ready,false);assert.equal(h.stores.get(CACHE).size,2);
 h.fail('');await h.runtime.download();h.setOnline(false);for(const url of Assets.runtime)assert.equal(await(await h.runtime.respond(url)).text(),'runtime');
});
test('optional wheels are verified on demand and excluded from readiness',async()=>{
 const h=harness();await h.runtime.download();const count=h.calls.length;assert.equal(h.runtime.includes(Assets.optional[0]),true);await h.runtime.respond(Assets.optional[0]);assert.equal(h.calls.length,count+1);
 h.stores.get(CACHE).delete(Assets.optional[0]);assert.equal((await h.runtime.status()).ready,true);
});

test('cold cross-origin script loads remain verifiable without credentials',async()=>{
 const h=harness(),url=Assets.runtime.find(url=>url.endsWith('tex-svg.js'));
 const request=new Request(url,{mode:'no-cors',credentials:'include'});
 const response=await h.runtime.respond(request);
 assert.equal(await response.text(),'runtime');
 assert.equal(await(await h.runtime.respond(url)).text(),'runtime');
 assert.equal(h.calls.length,1);
});
