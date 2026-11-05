import{test}from'@playwright/test';
test.setTimeout(120000);
test.beforeEach(async({context},info)=>{
 const source=info.title.startsWith('atomic install')?'from manim import *\nclass Offline(Scene):\n def construct(self): self.add(Square())':'digraph { hello -> world }';
 await context.route('**/',async route=>{const response=await route.fetch();await route.fulfill({response,body:(await response.text()).replace(/(<pre id="editor">)[\s\S]*?(<\/pre>)/,'$1'+source+'$2')});});
});
export default{
 ready:'body[data-ready="true"]',editor:'#editor',status:'#hashbin-status',draftKey:'manimonline:draft',more:'#more-toggle',share:'#share',qr:'#qr',tabs:['Code','Preview'],example:'dot',cachePrefix:'manimonline-offline-',offlineAsset:'src/app.css',kitURL:'./vendor/fragment-kit-v0.3.3/src/index.js',
 isWrittenURL:href=>{const url=new URL(href);return url.hash.length>1||url.searchParams.has('compressed');},
 getSource:page=>page.evaluate(()=>ManimOnline.editor.getValue()),getDocument:page=>page.evaluate(()=>ManimOnline.snapshot()),
 // Generic prose fixtures use forced DOT; real modl layout/drag races run in the native suites.
 edit:(page,src)=>page.evaluate(src=>{document.getElementById('renderer-mode').value='graphviz';ManimOnline.editor.setValue(src,-1);},src),openMore:async page=>{if(!await page.locator('#fk-more-drawer').isVisible())await page.click('#more-toggle');},
 configureHashBin:async(context,clientId)=>context.route('**/',async route=>{const response=await route.fetch();await route.fulfill({response,body:(await response.text()).replace(/name="hashbin-client-id" content="[^"]*"/,'name="hashbin-client-id" content="'+clientId+'"')});}),
 build:(page,doc,canonical=false)=>page.evaluate(async({doc,canonical})=>{const{urlState,config}=await import('./src/fragment-config.mjs');return urlState.build(doc,canonical?{url:config.canonicalOrigin}:{}).href;},{doc,canonical})
};
