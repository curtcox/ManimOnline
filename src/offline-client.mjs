import {OfflineClient} from '../vendor/fragment-kit-v0.4.3/src/index.js';
export function initOffline(shell){
 const status=shell.offlineStatus,repair=document.createElement('button'),update=document.createElement('button');
 repair.id='offline-repair';repair.textContent='Repair offline copy';update.id='offline-update';update.textContent='Update and reload';update.hidden=true;shell.drawer.body.append(repair,update);
 let rendered=false,controlled=Boolean(navigator.serviceWorker?.controller),reloading=false,checking;
 const client=new OfflineClient({timeout:90000,onStatus:()=>{},onUpdate:()=>{update.hidden=false;status.textContent='Offline update ready';}});
 const failed=error=>{status.textContent='Offline setup incomplete';status.title=error.message;};
 async function check(download=false){
  if(checking)return checking;checking=(async()=>{const base=await client.status(),runtime=await client.request(download?'cache-runtime':'manim-runtime-status');
   if(client.registration?.waiting){update.hidden=false;status.textContent='Offline update ready';}
   else status.textContent=base.ready&&runtime.ready?'Available offline':base.ready?'Diagrams ready offline':'Offline setup incomplete';
   repair.textContent=base.ready&&!runtime.ready?'Save Python offline':'Repair offline copy';return{base,runtime};
  })().catch(failed).finally(()=>{checking=null;});return checking;
 }
 window.addEventListener('manim-rendered',()=>{rendered=true;if(client.registration?.active)check(true);});
 repair.onclick=async()=>{repair.disabled=true;try{await client.repair();await check(true);}catch(error){failed(error);}finally{repair.disabled=false;}};
 update.onclick=()=>{window.dispatchEvent(new Event('offline-before-reload'));reloading=true;client.activateUpdate();};
 navigator.serviceWorker?.addEventListener('controllerchange',()=>{if(controlled||reloading){window.dispatchEvent(new Event('offline-before-reload'));location.reload();}else{controlled=true;check(rendered);}});
 status.textContent='Saving for offline use…';client.init().then(()=>check(rendered)).catch(failed);
 return{client,check};
}
