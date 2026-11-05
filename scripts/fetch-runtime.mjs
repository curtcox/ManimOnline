import fs from 'node:fs/promises';import{createHash}from'node:crypto';
const pins=JSON.parse(await fs.readFile('scripts/remote-hashes.json','utf8')),sha=data=>createHash('sha256').update(data).digest('hex');await fs.mkdir('.runtime-cache',{recursive:true});
for(const[url,pin]of Object.entries(pins)){if(url.includes('lz-string')||url.includes('typst'))continue;const file='.runtime-cache/'+sha(url);try{if(sha(await fs.readFile(file))===pin)continue;}catch{}const response=await fetch(url);if(!response.ok)throw Error('Runtime download failed: '+url);const data=Buffer.from(await response.arrayBuffer());if(sha(data)!==pin)throw Error('Runtime hash mismatch: '+url);await fs.writeFile(file,data);}
console.log('Pinned Pyodide, MathJax and optional wheels verified.');
