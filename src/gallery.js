import{mountGallery}from'../vendor/fragment-kit-v0.3.5/src/index.js';
const samples=globalThis.ManimGalleryCatalog,container=document.getElementById('gallery');
// Ordinary example links preserve the app's phone MP4 fast path and older cached editors.
const state={build:doc=>{const example=samples.find(sample=>sample.document===doc);return{href:new URL(example.editorURL||('./?url='+encodeURIComponent(example.path)),location.href).href};}};
mountGallery({container,catalog:samples.map(sample=>({...sample,cover:'gallery/covers/'+sample.id+'.png'})),urlState:state});
container.querySelector('input').id='sample-search';const tags=container.querySelector('select');tags.id='sample-type';tags.options[0].textContent='All languages';
container.querySelector('[role=status]').id='sample-count';const grid=container.querySelector('.fk-gallery-grid');grid.id='sample-grid';
const names={manim:'MANIM ANIMATION',graphviz:'GRAPHVIZ DOT',modl:'MODL DIAGRAM'};
function decorate(){for(const card of grid.children){const example=samples.find(sample=>sample.label===card.querySelector('h2').textContent);if(!example||card.dataset.preview)continue;card.dataset.preview='true';card.id=example.id;card.classList.add('card');
 const cover=card.querySelector('img'),link=card.querySelector('a'),preview=document.createElement('div');preview.className='preview';preview.append(cover);card.prepend(preview);
 const details=document.createElement('div');details.className='details';for(const node of [...card.childNodes])if(node!==preview)details.append(node);card.append(details);
 const language=document.createElement('p');language.className='language';language.textContent=names[example.type];details.prepend(language);link.classList.add('load');link.textContent='Load in editor →';link.setAttribute('aria-label','Load '+example.label+' in editor');
 const lesson=globalThis.VideoLinks?.examples[example.id];if(lesson){const watch=document.createElement('a');watch.className='watch';watch.href=lesson.url;watch.target='_blank';watch.rel='noopener';watch.textContent='▶ Video: episode '+lesson.episode+' · '+lesson.chapter;link.before(watch);}
 if(!example.video)continue;const video=document.createElement('video');video.preload='none';video.poster=example.cover;video.controls=true;video.muted=true;video.playsInline=true;video.hidden=true;video.setAttribute('aria-label',example.label+' animation preview');
 const button=document.createElement('button');button.className='play';button.type='button';button.textContent='▶ Play preview';button.setAttribute('aria-label','Play '+example.label+' preview');
 button.onclick=()=>{video.src=example.video;video.hidden=false;cover.hidden=true;button.hidden=true;video.focus();video.play().catch(()=>{});};
 video.onplay=()=>{for(const other of grid.querySelectorAll('video'))if(other!==video)other.pause();};
 video.onerror=()=>{cover.hidden=false;video.hidden=true;button.hidden=false;button.textContent='↻ Retry preview';if(!details.querySelector('.preview-error')){const error=document.createElement('p');error.className='preview-error';error.setAttribute('role','status');error.textContent='Preview could not play. Retry, or load the sample in the editor.';details.append(error);}};
 video.onplaying=()=>details.querySelector('.preview-error')?.remove();preview.append(video,button);
}}
new MutationObserver(records=>{for(const record of records)for(const node of record.removedNodes)node.querySelector?.('video')?.pause();decorate();}).observe(grid,{childList:true});decorate();
document.addEventListener('visibilitychange',()=>{if(document.hidden)for(const video of grid.querySelectorAll('video'))video.pause();});
