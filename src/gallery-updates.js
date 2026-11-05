import{OfflineClient}from'../vendor/fragment-kit-v0.3.3/src/index.js';
const button=document.createElement('button');button.id='offline-update';button.textContent='Update and reload';button.hidden=true;document.querySelector('header nav').append(button);
const client=new OfflineClient({onUpdate:()=>{button.hidden=false;}});
let controlled=Boolean(navigator.serviceWorker?.controller);
navigator.serviceWorker?.addEventListener('controllerchange',()=>{if(controlled)location.reload();else controlled=true;});
button.onclick=()=>client.activateUpdate();client.init().catch(()=>{});
