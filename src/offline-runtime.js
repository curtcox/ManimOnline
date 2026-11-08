/* Consumer-owned deferred Pyodide/MathJax policy. The kit owns the application cache. */
(function(root){
 const CACHE='manimonline-runtime-v1';
 function createRuntime({manifest,scope,caches,fetch,verify}){
  const required=manifest.runtime,optional=manifest.optional,all=[...required,...optional];
  const checked=(response,url)=>verify(response,manifest.runtimeHashes[url],url);
  async function read(url){const cache=await caches.open(CACHE),response=await checked(await cache.match(url),url);if(!response)await cache.delete(url);return response;}
  async function status(){const missing=[];for(const url of required)if(!await read(url))missing.push(url);return{ready:!missing.length,missing:missing.length,total:required.length};}
  async function download(){
   // Never request optional wheels here. They are cached only after an actual import.
   for(const url of required){if(await read(url))continue;const response=await checked(await fetch(url,{mode:'cors'}),url);if(!response)throw Error('Python runtime failed verification.');await(await caches.open(CACHE)).put(url,response);}
   return status();
  }
  async function carry(){
   const cache=await caches.open(CACHE);
   // An older app cache can supply only the same pinned bytes; altered entries are rejected.
   for(const url of all){if(await read(url))continue;const saved=await checked(await caches.match(url),url);if(saved)await cache.put(url,saved);}
  }
  async function respond(request){const url=typeof request==='string'?request:request.url;const cached=await read(url);if(cached)return cached;
   // Classic scripts arrive as no-cors requests; fetch readable, credential-free bytes for verification.
   const response=await fetch(request,{mode:'cors',credentials:'omit'}),copy=await checked(response.clone(),url);if(!copy)throw Error('Python runtime failed verification.');await(await caches.open(CACHE)).put(url,copy);return response;
  }
  return{status,download,carry,respond,includes:url=>all.includes(url),cacheName:CACHE};
 }
 if(typeof module!=='undefined')module.exports={createRuntime,CACHE};else root.ManimOfflineRuntime={createRuntime,CACHE};
})(globalThis);
