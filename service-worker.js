importScripts('offline-assets.js','vendor/hashbin-cache-v0.4.0.js','src/offline-runtime.js');
const runtime=ManimOfflineRuntime.createRuntime({manifest:OfflineAssets,scope:self.registration.scope,caches,fetch,verify:HashBinCache.verify});
self.addEventListener('install',event=>event.waitUntil(runtime.carry()));
self.addEventListener('fetch',event=>{if(event.request.method==='GET'&&runtime.includes(event.request.url))event.respondWith(runtime.respond(event.request));});
self.FragmentKitOfflineConfig={extraCaches:[runtime.cacheName],onMessage:async event=>{
 if(!['cache-runtime','manim-runtime-status'].includes(event.data?.type))return;
 try{if(event.data.type==='cache-runtime')await runtime.download();event.ports[0]?.postMessage(await runtime.status());}
 catch(error){event.ports[0]?.postMessage({...await runtime.status(),error:error.message});}
}};
importScripts('vendor/fragment-kit-v0.3.3/src/offline/sw-core.js');
