import fs from 'node:fs/promises';import{execFileSync}from'node:child_process';
for(const directory of ['src','scripts','tests','tests/browser'])for(const name of await fs.readdir(directory)){if(/\.(js|cjs|mjs)$/.test(name))execFileSync(process.execPath,['--check',directory+'/'+name]);}
for(const file of ['service-worker.js','offline-assets.js'])execFileSync(process.execPath,['--check',file]);
for(const script of ['gallery-catalog','render-docs','update-offline','render-kit-gallery'])process.stdout.write(execFileSync(process.execPath,['scripts/'+script+'.mjs','--check']));
const{createRequire}=await import('node:module'),{createHash}=await import('node:crypto'),require=createRequire(import.meta.url),{ExampleCatalog}=require('../src/examples.js');
const runtimeFiles=['src/manim-lite.py','src/text-outlines.json','src/unified-worker.js','src/manim-renderer.js','src/manim-math.js','src/manim-typst.js','src/manim-video.js','src/modl.js','viz-global.js','src/manim-client.js','src/manim-sandbox.js','vendor/fragment-kit-v0.4.3/vendor/hashbin-sdk-v0.4.0.mjs'];
const hash=async files=>createHash('sha256').update(Buffer.concat(await Promise.all(files.map(file=>fs.readFile(file))))).digest('hex'),runtime=await hash(runtimeFiles),previews=JSON.parse(await fs.readFile('gallery/previews/manifest.json','utf8'));
for(const example of ExampleCatalog){if(previews[example.id]?.source!==await hash([example.path])||previews[example.id]?.runtime!==runtime)throw Error('Original gallery preview is stale: '+example.id);}
execFileSync(process.execPath,['vendor/fragment-kit-v0.4.3/tools/check.mjs'],{stdio:'inherit'});
execFileSync(process.execPath,['vendor/fragment-kit-v0.4.3/tools/vendor-sync.mjs','--check','--target','.'],{stdio:'inherit'});
console.log('App scripts, original previews, generated docs/gallery/offline and vendor pins current.');

const{SANDBOX_BOOTSTRAP}=await import('../vendor/fragment-kit-v0.4.3/vendor/hashbin-sdk-v0.4.0.mjs');const bootstrap='sha256-'+createHash('sha256').update(SANDBOX_BOOTSTRAP).digest('base64'),html=await fs.readFile('index.html','utf8');if(!html.includes(bootstrap))throw Error('Opaque sandbox CSP bootstrap changed.');
