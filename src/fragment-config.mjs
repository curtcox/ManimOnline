import * as kit from '../vendor/fragment-kit-v0.3.3/src/index.js';
import * as Detector from './detector.js';
import appConfig from '../fragment-kit.config.json' with {type:'json'};
const detect=Detector.default??globalThis.ContentDetector;
export const config=kit.createConfig(appConfig);
const languages=['graphviz','modl','manim'],engines=['dot','circo','fdp','nop','nop2','neato','sfdp','twopi','osage','patchwork'],formats=['svg','png','json','xdot','plain','ps'];
export function positions(input={}){
 if(!input||typeof input!=='object'||Array.isArray(input))throw Error('Diagram positions must be an object.');
 const out=Object.create(null);
 for(const key of Object.keys(input).sort()){
  const pair=input[key];if(!Array.isArray(pair)||pair.length!==2||!pair.every(Number.isFinite))throw Error('Diagram positions must be finite coordinate pairs.');
  out[key]=pair.slice();
 }return out;
}
export const type={type:'manim-editor',settingsKeys:['type','scene','engine','format','modlpos'],fileName:'diagram.json',contentType:'application/json',
 legacyEnvelopeTypes:['hashbin-diagram:graphviz','hashbin-diagram:modl','hashbin-diagram:manim','hashbin-diagram:'],
 normalize(value){
  if(typeof value?.src!=='string')throw Error('Source must be text.');
  const original=value.manim??value;const options=original?.type&&['dot','python'].includes(original.type)?{...original,type:original.type==='dot'?'graphviz':'manim'}:original;if(!options||typeof options!=='object'||Array.isArray(options))throw Error('Preview settings must be an object.');
  if(options.type!=null&&!languages.includes(options.type))throw Error('Unsupported source language.');
  const language=options.language??(languages.includes(options.type)?options.type:(detect.detect(value.src).type==='unknown'?'graphviz':detect.detect(value.src).type));
  if(!languages.includes(language))throw Error('Unsupported source language.');
  const mode=options.mode??(languages.includes(options.type)?options.type:'auto');if(mode!=='auto'&&!languages.includes(mode))throw Error('Unsupported renderer mode.');
  const legacy=options.mode==null&&value.manim==null&&languages.includes(options.type);
  const scene=legacy&&language!=='manim'?'':options.scene??'',engine=legacy&&language!=='graphviz'?'dot':options.engine??'dot',outputFormat=legacy&&language!=='graphviz'?'svg':options.outputFormat??'svg';
  if(typeof scene!=='string')throw Error('Scene must be text.');if(!engines.includes(engine))throw Error('Unsupported Graphviz engine.');if(!formats.includes(outputFormat))throw Error('Unsupported Graphviz format.');
  return {src:value.src,manim:{language,mode,scene:scene.trim(),engine,outputFormat,pos:positions(legacy&&language!=='modl'?{}:options.pos),autorun:options.autorun!==false}};
 },isDefault:doc=>doc.manim.autorun&&doc.manim.mode==='auto'&&!doc.manim.scene&&doc.manim.engine==='dot'&&doc.manim.outputFormat==='svg'&&!Object.keys(doc.manim.pos).length,
 parseLegacy(text){let value;try{value=JSON.parse(text);}catch{return undefined;}
  if(!value||typeof value.src!=='string')return undefined;
  if(value.version!=null&&value.version!==1)throw Error('Unsupported saved document version.');
  if(value.format!=null&&value.format!=='hashbin-diagram')throw Error('Unsupported saved document format.');
  if(value.type!=null&&!languages.includes(value.type))throw Error('Unsupported source language.');
  return type.normalize({...value,type:value.type??(value.format==='hashbin-diagram'?'modl':undefined)});
 }
};
export const fromDocument=value=>{const doc=type.normalize(value),options=doc.manim;return {src:doc.src,type:options.language,mode:options.mode,scene:options.scene,engine:options.engine,outputFormat:options.outputFormat,pos:options.pos,autorun:options.autorun};};
// Keep the deployed three-language envelope until every fleet reader supports v1.
export const serializeLegacy=value=>{const doc=fromDocument(value),out={format:'hashbin-diagram',version:1,src:doc.src,type:doc.type,mode:doc.mode};
 if(doc.type==='modl')out.pos=doc.pos;if(doc.type==='manim')out.scene=doc.scene;if(doc.type==='graphviz')out.graphviz={engine:doc.engine,format:doc.outputFormat};
 out.manim=type.normalize(value).manim;return kit.bounded(JSON.stringify(out),config.maxBytes);
};
// Legacy saved Graphviz documents nest their options separately from the renderer mode.
const normalize=type.normalize;type.normalize=value=>normalize(value?.graphviz?{...value,engine:value.graphviz.engine,outputFormat:value.graphviz.format}:value);
function applySettings(doc,url){
 const value=fromDocument(doc),params=url.searchParams;
 if(params.has('type')){const name=params.get('type'),kind={dot:'graphviz',python:'manim'}[name]??name;if(!languages.includes(kind))throw Error('Unsupported renderer mode.');value.mode=kind;value.type=kind;}
 if(params.has('scene'))value.scene=params.get('scene');if(params.has('engine'))value.engine=params.get('engine');if(params.has('format'))value.outputFormat=params.get('format');
 if(params.has('modlpos')){try{value.pos=JSON.parse(kit.bounded(params.get('modlpos'),config.maxBytes));}catch{throw Error('Invalid diagram positions.');}}
 return type.normalize(value);
}
export function legacyWriter(value,{url,run,view,compress}){
 const doc=fromDocument(value);if(doc.mode!=='auto')url.searchParams.set('type',doc.mode==='graphviz'?'dot':doc.mode);
 if(Object.keys(doc.pos).length)url.searchParams.set('modlpos',JSON.stringify(doc.pos));
 if(doc.scene)url.searchParams.set('scene',doc.scene);
 if(doc.type==='graphviz'||doc.engine!=='dot')url.searchParams.set('engine',doc.engine);if(doc.type==='graphviz'||doc.outputFormat!=='svg')url.searchParams.set('format',doc.outputFormat);
 if(run===false)url.searchParams.set('run','0');if(view)url.searchParams.set('view',view);
 url.hash=encodeURIComponent(doc.src);const long=url.href;
 try{const encoded=compress?.(doc.src);if(encoded){url.hash='';url.searchParams.set('compressed',encoded);}}catch{}
 // Existing readers understand plain fragments; avoid oversized HTTP query strings.
 return url.href.length>7000?long:url.href;
}
const core=kit.createUrlState({config,type,legacyWriter,legacyReaders:[(url,{documents})=>!url.hash&&!url.searchParams.has('doc')&&url.searchParams.has('raw')?applySettings(documents.parse(url.searchParams.get('raw')),url):null]});
export const urlState={...core,
 parse(input){const url=new URL(input),intent=core.parse(input);if(intent.kind==='source'&&!url.hash.startsWith('#v1.')&&!url.hash.startsWith('#h1=')&&!url.searchParams.has('doc'))intent.doc=applySettings(intent.doc,url);
  if(intent.kind==='none'&&url.searchParams.has('url'))return {...intent,kind:'remote',url:url.searchParams.get('url')};return intent;},
 build(value,options={}){const result=core.build(value,options),plain=new URL(result.href);plain.searchParams.delete('compressed');const doc=fromDocument(value);plain.hash=encodeURIComponent(doc.src);return Object.freeze({...result,long:plain.href,plain:plain.href});}
};
export const HashBinDocuments={...core.documents,MAX_BYTES:config.maxBytes,positions,serialize:serializeLegacy,parse:text=>fromDocument(core.documents.parse(text)),
 ...Object.fromEntries(['bytes','encode64','decode64','isCID','cidLength','verify'].map(key=>[key,kit[key]])),cid:value=>kit.cid(value,config.allowedHosts),link:core.link};
export function publishTransactions(storage,clientId=config.hashbinClientId){if(!storage)return undefined;const current=kit.createStorage({prefix:config.storagePrefix,storage}),owned=key=>key.startsWith('hashbin:publish:'+clientId+':');return{getItem(key){const value=current.getItem(key);if(value!=null||!owned(key))return value;try{return storage.getItem(key);}catch{return null;}},setItem:(key,value)=>current.setItem(key,value),removeItem(key){current.removeItem(key);if(owned(key))try{storage.removeItem(key);}catch{}}};}
export class HashBinStore extends kit.HashBinStore{
 constructor(options={}){let storage;try{storage=globalThis.sessionStorage;}catch{}super({config,type,...options,storage:undefined,transactionStorage:publishTransactions(options.transactionStorage??storage,options.clientId??config.hashbinClientId),legacyStorage:options.storage??options.legacyStorage});this.documents={...this.documents,serialize:serializeLegacy};}
 async load(value){return fromDocument(await super.load(value));}
 async callback(){return null;}
 async published(hash){const result=await super.published(hash);return result?.snapshot?{...result,snapshot:fromDocument(result.snapshot)}:result;}
}
export const ShareLinks={build:({url,code,mode='auto',type:language,scene='',engine='dot',format='svg',positions:pos={},compress})=>{
 const doc={src:code,type:language??(detect.detect(code).type==='unknown'?'graphviz':detect.detect(code).type),mode,scene,engine,outputFormat:format,pos};
 const base=core.scrub(url),long=legacyWriter(doc,{url:new URL(base),compress:null}),fallback=legacyWriter(doc,{url:new URL(base),compress});
 return Object.freeze({long,fallback});
}};
export const LZString={compressToEncodedURIComponent:kit.compress,decompressFromEncodedURIComponent:kit.decompress};
export const loadHashBinSDK=()=>import('../vendor/fragment-kit-v0.3.3/vendor/hashbin-sdk-v0.4.0.mjs');
export {ShareClient} from '../vendor/fragment-kit-v0.3.3/src/index.js';
