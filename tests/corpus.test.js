const{test}=require('node:test'),assert=require('node:assert/strict'),{urlState,HashBinDocuments:D,type,fromDocument,publishTransactions}=require('../src/fragment-config.mjs'),{compress,createUrlState,config}=require('../vendor/fragment-kit-v0.3.5/src/index.js');
const corpus=require('./legacy-urls.json');
test('harvested source links preserve source and all language options',()=>{
 let count=0;for(const entry of corpus.cases){if(entry.kind!=='source')continue;const doc=fromDocument(urlState.parse(entry.href).doc),expected=entry.raw?D.parse(entry.raw):{src:entry.src};assert.equal(doc.src,expected.src);if(entry.raw)for(const field of ['type','scene','engine','outputFormat'])assert.equal(doc[field],expected[field]);count++;}assert.ok(count>=4);
});
test('v1 and deployed writers retain explicit mode, scene and fractional diagram positions',()=>{
 const docs=[{src:'a -> b',type:'modl',mode:'modl',pos:{a:[1.125,-2.75]}},{src:'from manim import *',type:'manim',mode:'auto',scene:'Second',engine:'neato',outputFormat:'png',pos:{hidden:[1.5,-3.25]}},{src:'digraph{a->b}',type:'graphviz',mode:'graphviz',engine:'neato',outputFormat:'png'}];
 const app=require('../src/fragment-config.mjs').config,canonical=createUrlState({config:app,type});
 for(const doc of docs){const normalized=type.normalize(doc);assert.deepEqual(urlState.parse(urlState.build(doc,{run:false}).href).doc,normalized);assert.deepEqual(urlState.parse(canonical.build(doc).href).doc,normalized);assert.deepEqual(type.normalize(D.parse(D.serialize(doc))),normalized);}
});
test('explicit fragments outrank examples and invalid layouts and versions fail visibly',()=>{
 assert.equal(urlState.parse('https://manim.hashbin.page/?example=old#digraph%7Ba-%3Eb%7D').doc.src,'digraph{a->b}');
 assert.throws(()=>urlState.parse('https://manim.hashbin.page/?raw=a&modlpos=bad'),/positions/);
 assert.throws(()=>urlState.parse('https://manim.hashbin.page/?compressed=invalid!'),/decompressed/);
 assert.throws(()=>urlState.parse('https://manim.hashbin.page/#v2.bad'),/version/);
});
test('large sources retain deployed fragment support and avoid oversized HTTP queries',()=>{
 const src=Array.from({length:16000},(_,i)=>(Math.imul(i,2654435761)>>>0).toString(36)).join(' '),href=urlState.build({src}).href;assert.ok(new URL(href).hash.length>1);assert.ok(!new URL(href).searchParams.has('compressed'));assert.equal(urlState.parse(href).doc.src,src);
});
test('new Publish transactions are prefixed and legacy reads belong only to this client',()=>{
 const values=new Map(),storage={getItem:key=>values.get(key)??null,setItem:(key,value)=>values.set(key,value),removeItem:key=>values.delete(key)},tx=publishTransactions(storage,'mine');
 values.set('hashbin:publish:mine:old','owned');values.set('hashbin:publish:other:old','foreign');assert.equal(tx.getItem('hashbin:publish:mine:old'),'owned');assert.equal(tx.getItem('hashbin:publish:other:old'),null);
 tx.setItem('hashbin:publish:mine:new','new');assert.equal(values.get('manimonline:hashbin:publish:mine:new'),'new');tx.removeItem('hashbin:publish:mine:old');assert.equal(values.has('hashbin:publish:mine:old'),false);
});
