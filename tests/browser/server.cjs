// Test-only mirror of the immutable runtime bytes; production URLs and source stay unchanged.
const fs=require('node:fs'),path=require('node:path'),http=require('node:http'),{createHash}=require('node:crypto');
const root=path.resolve(__dirname,'../..'),pins=require('../../scripts/remote-hashes.json'),manifest=require('../../offline-assets.js');
const prefix='https://cdn.jsdelivr.net/',sha=data=>createHash('sha256').update(data).digest('hex');
function createServer(port=Number(process.env.PORT||8010)){
 let base;const rewrite=text=>text.split(prefix).join(base+'__runtime__/');
 function served(file){const raw=fs.readFileSync(file);return /\.(js|mjs|html|json)$/.test(file)?Buffer.from(rewrite(raw.toString())):raw;}
 const server=http.createServer({maxHeaderSize:8*1024*1024},(req,res)=>{try{
  const name=decodeURIComponent(new URL(req.url,'http://localhost').pathname);
  if(name.startsWith('/__runtime__/')){const url=prefix+name.slice('/__runtime__/'.length),pin=pins[url],file=path.join(root,'.runtime-cache',sha(url));if(!pin||!fs.existsSync(file)||sha(fs.readFileSync(file))!==pin)throw Error('Pinned runtime missing: '+url);const data=fs.readFileSync(file);res.setHeader('Content-Type',name.endsWith('.js')?'text/javascript':name.endsWith('.wasm')?'application/wasm':name.endsWith('.json')?'application/json':'application/octet-stream');res.setHeader('Access-Control-Allow-Origin','*');return res.end(data);}
  const file=path.resolve(root,'.'+(name.endsWith('/')?name+'index.html':name));if(!file.startsWith(root+path.sep)||!fs.statSync(file).isFile())throw Error('Not found');
  let data;
  if(name==='/offline-assets.js'){
   delete require.cache[require.resolve('../../offline-assets.js')];const value=JSON.parse(rewrite(JSON.stringify(require('../../offline-assets.js'))));
   for(const asset of value.assets)if(!asset.startsWith('https:'))value.hashes[asset]=sha(served(path.join(root,asset)));
   value.version='manimonline-offline-test-'+sha(JSON.stringify(value.hashes)).slice(0,16);
   data=Buffer.from('(function(self){self.OfflineAssets='+JSON.stringify(value)+';})(globalThis);');
  }else data=served(file);
  res.setHeader('Content-Type',({'.js':'text/javascript','.mjs':'text/javascript','.html':'text/html','.css':'text/css','.json':'application/json','.svg':'image/svg+xml','.png':'image/png','.mp4':'video/mp4','.wasm':'application/wasm'})[path.extname(file)]||'application/octet-stream');res.setHeader('Access-Control-Allow-Origin','*');res.end(data);
 }catch(error){res.statusCode=404;res.end(error.message);}});
 return{server,async start(){await new Promise(resolve=>server.listen(port,'127.0.0.1',resolve));base='http://127.0.0.1:'+server.address().port+'/';return base;}};
}
module.exports={createServer};if(require.main===module)createServer().start().then(console.log);
