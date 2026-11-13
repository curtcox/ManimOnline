import {createAi,createAskPanel,createAiSettings,createCompareModels,createSampleChooser,handleAiCallback} from '../vendor/fragment-kit-v0.4.3/src/ai/index.js';
import {createDialog,createStorage,element,readResponse,text} from '../vendor/fragment-kit-v0.4.3/src/index.js';
// Process and scrub the sign-in callback before document parsing or runtime startup.
export function aiCallback(){try{if(globalThis.fragmentKitAiCallback)return true;const callback=handleAiCallback();if(callback)globalThis.fragmentKitAiCallback=true;return callback;}catch(error){globalThis.fragmentKitAiCallback=true;const p=element('p',error.message,{role:'alert'});document.body.replaceChildren(p);return true;}}
export function configureAi(type){type.ai={describe:type.ai?.describe??'Edit only src. Preserve all settings and attached data. Proposed source is text until the user explicitly runs it.',paths:['/src'],...type.ai};return type;}
export async function mountClientAi({config,type,urlState,getSnapshot,getFingerprint,onApply,container,toolbar,status,prepareSnapshot}){
 configureAi(type);
 const originalUrlState=urlState;
 urlState={...urlState,commit:(doc,options)=>originalUrlState.commit(doc,{...options,run:false})};
 const storage=createStorage({prefix:config.storagePrefix}),ai=await createAi({config,type,storage});if(!ai)return null;
 const dialog=createDialog('Ask for a change',{id:config.slug+'-ai'});
 const ask=createAskPanel({ai,type,urlState,getSnapshot,getFingerprint,onApply,container:dialog.body});
 dialog.dialog.addEventListener('close',()=>ask.cancel());
 const button=element('button','Ask',{type:'button',id:'ask-open'});toolbar.prepend(button);
 button.onclick=async()=>{try{await prepareSnapshot?.();dialog.open();ask.open();}catch(error){status(error.message);}};
 createAiSettings({ai,container,onChange:ask.refreshModels});
 let comparison;
 const compare=element('button','Compare models',{type:'button',id:'compare-models'});compare.onclick=async()=>{try{
  await prepareSnapshot?.();
  if(!comparison){const response=await fetch(new URL('../ai-suite.json',import.meta.url));if(!response.ok)throw Error('AI suite is unavailable.');comparison=createCompareModels({ai,type,suite:JSON.parse(text(await readResponse(response,256*1024))),storage,getSnapshot,getFingerprint,onApply,urlState});}
  await comparison.refresh();comparison.open();
 }catch(error){status(error.message);}};container.append(compare,element('a','Synthetic comparison results',{href:new URL('../ai-comparison.json',import.meta.url).href,target:'_blank',rel:'noopener'}));
 const cancel=()=>{ask.cancel();comparison?.close();};
 for(const event of ['hashchange','popstate'])addEventListener(event,cancel);
 addEventListener('pagehide',()=>{cancel();ai.destroy();},{once:true});
 return{ai,type,cancel};
}
export async function mountGalleryAi({config,type,urlState,catalog,container}){
 configureAi(type);const section=element('section','',{id:'ai-starting-point'});container.before(section);
 const ai=await createAi({config,type,storage:createStorage({prefix:config.storagePrefix})});
 const chooser=createSampleChooser({ai,catalog,urlState,container:section});
 if(ai)createAiSettings({ai,container:section,onChange:()=>void chooser.refresh()});
 addEventListener('pagehide',()=>{chooser.destroy();ai?.destroy();},{once:true});return chooser;
}
