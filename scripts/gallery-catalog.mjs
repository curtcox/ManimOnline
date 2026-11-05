import fs from 'node:fs/promises';import{createRequire}from'node:module';const{ExampleCatalog}=createRequire(import.meta.url)('../src/examples.js');
const catalog=await Promise.all(ExampleCatalog.map(async example=>({...example,title:example.label,tags:[example.type],description:example.type==='manim'?'Browser Manim-lite animation. Pre-rendered preview available.':'Editable '+example.type+' diagram.',document:{src:await fs.readFile(example.path,'utf8')}})));
const source='// Generated from the app-owned examples and catalog.\nglobalThis.ManimGalleryCatalog='+JSON.stringify(catalog,null,2)+';\n';
if(process.argv.includes('--check')){if(await fs.readFile('src/gallery-catalog.js','utf8')!==source)throw Error('Gallery catalog is stale.');}else await fs.writeFile('src/gallery-catalog.js',source);
console.log(catalog.length+' gallery sources current.');
