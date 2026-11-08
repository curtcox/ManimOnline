import {LocalDrafts,RenderScheduler,HashBinPanel,createShell,mountMobileTabs,createShareDialog,createQrDialog,readResponse,text} from '../vendor/fragment-kit-v0.3.5/src/index.js';
import {config,type,urlState,HashBinDocuments,HashBinStore,ShareLinks,ShareClient,LZString,fromDocument,loadHashBinSDK} from './fragment-config.mjs';
import {initOffline} from './offline-client.mjs';
Object.assign(globalThis,{HashBinDocuments,HashBinStore,ShareLinks,ShareClient,LZString,loadHashBinSDK});
const legacyControls=['shareurl','shorten-share','share-status','hashbin-save','hashbin-cid','hashbin-load','hashbin-status','hashbin-dialog','offline-status','offline-action','view-tabs'].map(id=>document.getElementById(id));
const shell=createShell({config});
shell.header.querySelector('.fk-brand').href=new URL('./',location.href).href;
shell.header.querySelector('.fk-more').id='more-toggle';
const oldMore=document.querySelectorAll('#more-toggle')[1];oldMore.remove();
const options=document.getElementById('options');
for(const node of legacyControls)node?.remove();
shell.drawer.body.append(options);shell.status.id='app-status';
const oldGallery=document.getElementById('sample-gallery'),resourceGallery=[...shell.drawer.body.querySelectorAll('a')].find(link=>link.textContent==='Gallery ↗');resourceGallery.id='sample-gallery';resourceGallery.href=oldGallery.getAttribute('href');oldGallery.remove();
const workspace=document.createElement('main');workspace.id='workspace';
for(const id of ['editor-toggle','editor','splitter','review','status'])workspace.append(document.getElementById(id));
document.body.append(workspace);shell.status.append(document.getElementById('status'));
document.querySelector('.github-fork-ribbon-wrapper')?.remove();
shell.toolbar.append(document.querySelector('.render-controls.phone-bar'),document.getElementById('type-indicator'));
const shareButton=document.getElementById('share');shell.toolbar.append(shareButton);
const qrButton=document.createElement('button');qrButton.id='qr';qrButton.textContent='QR';shell.toolbar.append(qrButton);
const tabBar=document.createElement('div');tabBar.id='panel-tabs';shell.toolbar.prepend(tabBar);
let tabs;
const resizeWorkspace=()=>document.documentElement.style.setProperty('--workspace-top',(shell.header.getBoundingClientRect().bottom)+'px');
new ResizeObserver(resizeWorkspace).observe(shell.header);new ResizeObserver(resizeWorkspace).observe(document.body);new ResizeObserver(resizeWorkspace).observe(shell.toolbar);
let autoRun=true,navigationRevision=0,applying=false,qrSave=false;
/* Editor orchestration, loaded last so every helper script is available. Indentation is kept from its inline origin. */
    const editorElement = document.getElementById('editor');
    const reviewElement = document.getElementById('review');
    const optionsElement = document.getElementById('options');
    // Wrapped controls must not cover the preview when the panel is narrow.
    new ResizeObserver(() => {
      reviewElement.style.top = '0px';
      resizeSVG();
    }).observe(optionsElement);
    const toggleBtn = document.getElementById('toggle-btn');
    const splitter = document.getElementById('splitter');
    const typeIndicator = document.getElementById('type-indicator');
    const pyodideStatus = document.getElementById('pyodide-status');
    const graphvizOptions = document.querySelector('.graphviz-options');
    const sceneNameInput = document.getElementById('scene-name');
    const sceneNamesList = document.getElementById('scene-names');

    let isCollapsed = false;
    let isDragging = false;
    let currentSplitPercentage = 50;
    // Keep in sync with the phone @media rule above.
    const mobileLayout = window.matchMedia('(max-width: 760px), (max-height: 500px)');
    const moreToggle = document.getElementById('more-toggle');
    function updateToggleLabel() {
      toggleBtn.textContent = isCollapsed ? '▶' : '◀';
      toggleBtn.setAttribute('aria-expanded', String(!isCollapsed));
      toggleBtn.setAttribute('aria-label', isCollapsed ? 'Show code editor' : 'Hide code editor');
      ace.edit('editor').getSession().setUseWrapMode(mobileLayout.matches);
    }
    mobileLayout.addEventListener('change', updateToggleLabel);
    function showCode(visible) { if(mobileLayout.matches){tabs?.select(visible?0:1);return;}if (visible === isCollapsed) toggleBtn.click(); }
    function setMoreOpen(open) { if(open&&!shell.drawer.dialog.open)shell.drawer.open();else if(!open)shell.drawer.dialog.close(); }
    new ResizeObserver(() => {
      ace.edit('editor').resize();
      resizeSVG();
    }).observe(editorElement);
    new ResizeObserver(resizeSVG).observe(reviewElement);

    // Current content type
    let currentType = 'unknown';

    // Splitter drag functionality
    splitter.addEventListener('mousedown', (e) => {
      if (isCollapsed) return;
      isDragging = true;
      splitter.classList.add('dragging');
      document.body.style.cursor = 'col-resize';
      editorElement.style.transition = 'none';
      splitter.style.transition = 'none';
      reviewElement.style.transition = 'none';
      optionsElement.style.transition = 'none';
      e.preventDefault();
    });

    document.addEventListener('mousemove', (e) => {
      if (!isDragging) return;

      const windowWidth = window.innerWidth;
      const newLeft = e.clientX;
      const percentage = (newLeft / windowWidth) * 100;

      if (percentage >= 10 && percentage <= 90) {
        currentSplitPercentage = percentage;
        updatePanelSizes(percentage);
      }
    });

    document.addEventListener('mouseup', () => {
      if (isDragging) {
        isDragging = false;
        splitter.classList.remove('dragging');
        document.body.style.cursor = '';
        editorElement.style.transition = '';
        splitter.style.transition = '';
        reviewElement.style.transition = '';
        optionsElement.style.transition = '';
        setTimeout(resizeSVG, 100);
      }
    });

    function updatePanelSizes(percentage) {
      if (!isCollapsed) {
        editorElement.style.width = `${percentage}%`;
        splitter.style.left = `${percentage}%`;
        reviewElement.style.left = `calc(${percentage}% + 5px)`;
        optionsElement.style.left = `calc(${percentage}% + 5px)`;
      }
    }

    toggleBtn.addEventListener('click', () => tabs?.select(tabs.getView()===1?'split':1));
    // Phone visitors mostly watch, so they start on the preview.

    updateToggleLabel();

    window.addEventListener('resize', resizeSVG);

    // svg-pan-zoom pans with one touch but cannot pinch. Replace its touch listeners with
    // pointer events: one finger pans, two fingers zoom about (and pan with) their midpoint.
    function touchPanZoom() {
      let stop = null;
      return {
        haltEventListeners: ['touchstart', 'touchend', 'touchmove', 'touchleave', 'touchcancel'],
        init({ svgElement: svg, instance }) {
          const points = new Map();
          let last = null;
          const state = () => {
            const [a, b = a] = [...points.values()];
            return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2, d: Math.hypot(a.x - b.x, a.y - b.y) };
          };
          const down = event => {
            if (event.pointerType !== 'touch') return;
            points.set(event.pointerId, { x: event.clientX, y: event.clientY });
            last = state();
            svg.setPointerCapture?.(event.pointerId);
          };
          const move = event => {
            if (!points.has(event.pointerId)) return;
            event.preventDefault();
            points.set(event.pointerId, { x: event.clientX, y: event.clientY });
            const now = state();
            if (points.size > 1 && last.d > 0 && now.d > 0) {
              const box = svg.getBoundingClientRect();
              instance.zoomAtPointBy(now.d / last.d, { x: now.x - box.left, y: now.y - box.top });
            }
            instance.panBy({ x: now.x - last.x, y: now.y - last.y });
            last = now;
          };
          const up = event => {
            if (!points.delete(event.pointerId)) return;
            last = points.size ? state() : null;
          };
          svg.style.touchAction = 'none';
          svg.addEventListener('pointerdown', down);
          svg.addEventListener('pointermove', move);
          for (const type of ['pointerup', 'pointercancel']) svg.addEventListener(type, up);
          stop = () => {
            svg.removeEventListener('pointerdown', down);
            svg.removeEventListener('pointermove', move);
            for (const type of ['pointerup', 'pointercancel']) svg.removeEventListener(type, up);
          };
        },
        destroy() { stop?.(); }
      };
    }

    function resizeSVG() {
      const svg = document.querySelector('#review svg');
      // A hidden preview (the phone Code tab) has no size; fitting then would scale to zero.
      if (svg && currentType === 'graphviz' && reviewElement.clientWidth && reviewElement.clientHeight) {
        try {
          const panZoom = svgPanZoom(svg);
          panZoom.resize();
          panZoom.fit();
          panZoom.center();

          svg.style.width = '100%';
          svg.style.height = '100%';
        } catch (e) {
          // Ignore pan-zoom errors
        }
      }
    }

    (async function (document) {
      window.URL = window.URL || window.webkitURL;
      var el_stetus = document.getElementById("status"),
        t_stetus = -1,
        reviewer = document.getElementById("review"),
        scale = window.devicePixelRatio || 1,
        downloadBtn = document.getElementById("download"),
        editor = ace.edit("editor"),
        parser = new DOMParser(),
        formatEl = document.querySelector("#format select"),
        engineEl = document.querySelector("#engine select"),
        rawEl = document.querySelector("#raw input"),
        shareEl = document.querySelector("#share"),
        errorEl = document.querySelector("#error");

      const renderAnimationButton = document.getElementById('render-animation');
      const cancelRenderButton = document.getElementById('cancel-render');
      function setRenderBusy(busy) {
        renderAnimationButton.disabled = busy;
        cancelRenderButton.hidden = !busy;
      }
      let renderRevision = 0;
      let player = null;
      let sampleVideo = null;
      let modlPreview = null;
      let modlPositions = Object.create(null);
      let savedHashbin = null;
      const storage = kind => { try { return window[kind]; } catch (_) { return null; } };
      const hashbinStore = new HashBinStore({
        clientId: document.querySelector('meta[name="hashbin-client-id"]').content,
        legacyStorage: storage('localStorage'), transactionStorage: storage('sessionStorage')
      });
      function sourceSnapshot() {
        const src = editor.getValue();
        const type = rendererMode.value === 'auto' ? ContentDetector.detect(src).type : rendererMode.value;
        return { src, autorun:autoRun, type: type==='unknown'?'graphviz':type, mode:rendererMode.value, scene: sceneNameInput.value, engine: engineEl.value,
          outputFormat: formatEl.value, pos: modlPositions };
      }
      const hashbinPanel = new HashBinPanel({ store: hashbinStore, urlState, container:shell.drawer.body, getSnapshot: sourceSnapshot,
        getFingerprint: currentShareFingerprint,
        onLoad: (doc,cid)=>applyLoadedSource(doc,cid,{cancel:false}),
        onSaved: (cid, fingerprint, link) => {
          urlState.cancel();lastOpened=link;
          savedHashbin = { cid, fingerprint };
          history.pushState(null, '', link);
          clearShare();if(qrSave){qrSave=false;hashbinPanel.dialog.close();qrDialog.open(link);}
        }
      });
      // Series QR codes and gallery samples link to the video chapter that explains them.
      const videoLink = document.getElementById('video-link');
      function showVideoLink(entry) {
        videoLink.hidden = !entry;
        if (!entry) return;
        const name = entry.episode === 0 ? 'trailer' : `episode ${entry.episode}`;
        videoLink.href = entry.url;
        videoLink.textContent = `▶ Video: ${name} · ${entry.chapter}`;
        videoLink.title = `Watch this in Drawing with Code ${name}, “${entry.chapter}”, on YouTube`;
      }
      // Typing marks unsaved work; loads and saves clear it, so links never silently replace it.
      const drafts = new LocalDrafts({storage:storage('localStorage'),key:'manimonline:draft'});
      drafts.mount(shell.drawer.body, snapshot => { applyLoadedSource(snapshot); });
      function applyLoadedSource(value, cid = null, {run=autoRun,write=true,cancel=true}={}) {
        const snapshot=fromDocument(value);
        if(cancel){navigationRevision++;hashbinPanel.cancelLoad();}urlState.cancel();scheduler.cancel();exampleLoader.cancel();invalidateRender();
        autoRun=run;applying=true;drafts.opened();showVideoLink(cid&&globalThis.VideoLinks?.snippets[cid]);
        modlPositions=HashBinDocuments.positions(snapshot.pos);sceneNameInput.value=snapshot.scene;engineEl.value=snapshot.engine;formatEl.value=snapshot.outputFormat;
        rendererMode.value=snapshot.mode;
        editor.setValue(snapshot.src,-1);applying=false;detectAndUpdateType();
        savedHashbin=cid?{cid,fingerprint:currentShareFingerprint()}:null;
        if(write)updateState();
        if(autoRun)render();
      }
      function currentShareFingerprint() {
        return JSON.stringify([editor.getSession().getDocument().getValue(),rendererMode.value,sceneNameInput.value,engineEl.value,formatEl.value,modlPositions]);
      }
      function clearShare() {}
      hashbinPanel.dialog.addEventListener('close',()=>{qrSave=false;});
      const shareDialog=createShareDialog({config,urlState,container:document.body,getSnapshot:()=>urlState.documents.normalize(sourceSnapshot()),onSave:()=>{shareDialog.dialog.close();shell.drawer.dialog.close();hashbinPanel.openSave();}});
      const qrDialog=createQrDialog({config,urlState,onLoad:outcome=>openURL(outcome.kind==='cid'?urlState.link(location.href,outcome.cid):outcome.href),onSave:()=>{qrSave=true;qrDialog.dialog.close();return hashbinPanel.openSave();}});
      shareDialog.dialog.querySelector('p[role=status]').id='share-status';shareDialog.dialog.querySelectorAll('button').forEach(button=>{if(button.textContent==='Shorten link')button.id='share-shorten';});
      shareEl.addEventListener('click',()=>{shareDialog.open();const run=shareDialog.dialog.querySelector('#share-run');run.checked=autoRun;run.dispatchEvent(new Event('change'));});
      qrButton.addEventListener('click',()=>qrDialog.open(urlState.build(sourceSnapshot(),{run:autoRun,view:new URL(location.href).searchParams.get('view')||undefined}).href));
      const rendererMode = document.getElementById('renderer-mode');
      let exportingPNG = false;
      const frameFormat = document.getElementById('manim-export-format');
      const exportStatus = document.getElementById('export-status');
      window.addEventListener('offline-before-reload',()=>{drafts.attempt(sourceSnapshot());urlState.cancel();updateState();});
      let videoExport = null;
      function saveBlob(blob, name) {
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = name;
        document.body.appendChild(link);
        link.click();
        link.remove();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
      }
      async function exportVideo(format) {
        // A second click while encoding cancels the export.
        if (videoExport) { videoExport.abort(); return; }
        if (exportingPNG) return;
        if (!player || reviewer.classList.contains('working') || reviewer.classList.contains('error')) {
          exportStatus.textContent = 'Render an animation before downloading a video.';
          return;
        }
        const snapshotPlayer = player;
        const revision = renderRevision;
        const label = format === 'mp4' ? 'MP4' : 'WebM';
        snapshotPlayer.pause();
        const shown = snapshotPlayer.stage.firstElementChild;
        const controller = new AbortController();
        videoExport = controller;
        downloadBtn.setAttribute('aria-busy', 'true');
        downloadBtn.textContent = 'Cancel video';
        exportStatus.textContent = `Encoding ${label}… 0%`;
        try {
          const serializer = new XMLSerializer();
          const blob = await ManimVideo.encode({
            format, frameCount: snapshotPlayer.frames.length, fps: snapshotPlayer.fps,
            width: Number(shown.getAttribute('width')), height: Number(shown.getAttribute('height')),
            svgFor: index => serializer.serializeToString(ManimRenderer.render(snapshotPlayer.frames[index], snapshotPlayer.mathGlyphs)),
            onProgress: progress => {
              if (revision === renderRevision) exportStatus.textContent = `Encoding ${label}… ${Math.floor(progress * 100)}%`;
            },
            signal: controller.signal
          });
          if (revision !== renderRevision || player !== snapshotPlayer) return;
          saveBlob(blob, `manim.${format}`);
          exportStatus.textContent = `${label} downloaded.`;
        } catch (error) {
          if (revision === renderRevision) exportStatus.textContent = error.name === 'AbortError' ? 'Video export cancelled.' : error.message;
        } finally {
          videoExport = null;
          downloadBtn.textContent = 'Download';
          downloadBtn.removeAttribute('aria-busy');
          if (revision !== renderRevision) exportStatus.textContent = '';
        }
      }
      downloadBtn.addEventListener('click', async event => {
        if (currentType === 'modl') { refreshModlDownload(); return; }
        if (sampleVideo && currentType === 'manim') {
          event.preventDefault();
          render();
          exportStatus.textContent = 'Rendering live first. Choose Download again when it is ready.';
          return;
        }
        if (currentType !== 'manim' || frameFormat.value === 'svg') return;
        event.preventDefault();
        if (frameFormat.value !== 'png') return exportVideo(frameFormat.value);
        if (exportingPNG || videoExport) return;
        if (!player || reviewer.classList.contains('working') || reviewer.classList.contains('error')) {
          exportStatus.textContent = 'Render an animation before downloading a frame.';
          return;
        }
        const snapshotPlayer = player;
        const revision = renderRevision;
        snapshotPlayer.pause();
        const snapshotSVG = snapshotPlayer.stage.firstElementChild;
        const source = new XMLSerializer().serializeToString(snapshotSVG);
        const pixelWidth = Number(snapshotSVG.getAttribute('width'));
        const pixelHeight = Number(snapshotSVG.getAttribute('height'));
        exportingPNG = true;
        downloadBtn.setAttribute('aria-busy', 'true');
        exportStatus.textContent = 'Preparing PNG…';
        try {
          const blob = await ManimExport.png(source, pixelWidth, pixelHeight);
          if (revision !== renderRevision || player !== snapshotPlayer) return;
          saveBlob(blob, 'manim.png');
          exportStatus.textContent = 'PNG downloaded.';
        } catch (error) {
          if (revision === renderRevision) exportStatus.textContent = error.message;
        } finally {
          exportingPNG = false;
          downloadBtn.removeAttribute('aria-busy');
          if (revision !== renderRevision) exportStatus.textContent = '';
        }
      });
      // Serialize only when exporting, rather than walking the whole SVG on every pan/zoom.
      function refreshModlDownload() {
        if (currentType !== 'modl' || !modlPreview) return;
        downloadBtn.href = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(new XMLSerializer().serializeToString(modlPreview.svg));
        downloadBtn.download = 'modl.svg';
      }
      downloadBtn.addEventListener('contextmenu', refreshModlDownload);
      downloadBtn.addEventListener('auxclick', refreshModlDownload);
      document.getElementById('modl-zoom-out').addEventListener('click', () => modlPreview?.zoom(1 / 1.2));
      document.getElementById('modl-zoom-in').addEventListener('click', () => modlPreview?.zoom(1.2));
      document.getElementById('modl-reset-view').addEventListener('click', () => modlPreview?.resetView());
      frameFormat.addEventListener('change', () => { exportStatus.textContent = ''; });
      // Scenes, including ones from links, render in HashBin's opaque-origin sandbox.
      const manimClient = new ManimClient({ workerFactory: ManimSandbox.factory(), onStatus: text => {
        pyodideStatus.textContent = text;
        pyodideStatus.className = 'loading';
      }});

      const exampleStatus = document.getElementById('example-status');
      const exampleLoader = new ExampleLoader({
        fetchSource:async url=>{const response=await fetch(url);if(!response.ok)return response;const source=text(await readResponse(response,config.maxBytes));return {ok:true,text:async()=>source};},
        onStatus: message => { exampleStatus.textContent = message; },
        onError: error => { exampleStatus.textContent = error.message; },
        onLoad: (source, example) => {
          drafts.opened();savedHashbin = null;rendererMode.value='auto';autoRun=true;
          showVideoLink(globalThis.VideoLinks?.examples[example.id]);
          modlPositions = Object.create(null);
          sceneNameInput.value = '';
          // Loading an example opts into automatic detection, even from a typed link.
          const url = new URL(location.href);
          for (const parameter of ['example', 'type', 'scene', 'raw', 'compressed', 'url', 'modlpos']) {
            url.searchParams.delete(parameter);
          }
          url.hash = encodeURIComponent(source);
          history.replaceState(null, '', url);
          applying=true;editor.getSession().setValue(source);applying=false;updateState();
          if (example.video && mobileLayout.matches) showSampleVideo(example);
          else render();
        }
      });

      // Phones play a sample's pre-rendered video; Python loads only once the scene must run live
      // (an edit, Render, a scene name, renderer change or export).
      function showSampleVideo(example) {
        scheduler.cancel();
        clearError();
        invalidateRender();
        detectAndUpdateType();
        clearReviewContent();
        const revision = renderRevision;
        const box = document.createElement('div');
        box.className = 'sample-video';
        const video = document.createElement('video');
        video.muted = true;
        video.playsInline = true;
        video.controls = true;
        video.loop = true;
        video.poster = example.cover;
        video.setAttribute('aria-label', `${example.label} pre-rendered preview`);
        video.addEventListener('error', () => {
          if (sampleVideo === box && revision === renderRevision) render();
        });
        video.src = example.video;
        const note = document.createElement('p');
        note.textContent = 'Pre-rendered preview. Edit the code or choose Render to run it live.';
        box.append(video, note);
        reviewer.append(box);
        sampleVideo = box;
        video.play().catch(() => { /* Native controls allow playback if autoplay is blocked. */ });
      }

      function invalidateRender() {
        hashbinPanel.cancelLoad();

        renderRevision++;
        if (videoExport) videoExport.abort();
        exportStatus.textContent = '';
        if (manimClient.pending) manimClient.cancel();
        if (player) player.pause();
        reviewer.classList.remove('working');
        pyodideStatus.className = 'hidden';
        setRenderBusy(false);
      }

      const scheduler = new RenderScheduler({ detect: detectAndUpdateType, render });
      renderAnimationButton.addEventListener('click', () => {
        autoRun=true;updateState();
        if (mobileLayout.matches) showCode(false);
        render();
      });
      cancelRenderButton.addEventListener('click', () => {
        scheduler.cancel();
        invalidateRender();
        clearError();
        pyodideStatus.textContent = 'Render cancelled';
        pyodideStatus.className = '';
        show_status('Render cancelled. Choose Render animation to retry.');
        renderAnimationButton.focus();
      });
      rendererMode.addEventListener('change', () => {navigationRevision++;exampleLoader.cancel();updateState();if(autoRun)render();else detectAndUpdateType();});

      function show_status(text, hide) {
        hide = hide || 0;
        clearTimeout(t_stetus);
        el_stetus.innerHTML = text;
        if (hide) {
          t_stetus = setTimeout(function () {
            el_stetus.innerHTML = "";
          }, hide);
        }
      }

      function show_error(e) {
        console.error(e);
        show_status("error", 500);
        reviewer.classList.remove("working");
        reviewer.classList.add("error");
        var message = e.message === undefined ? "An error occurred while processing the input." : e.message;
        while (errorEl.firstChild) {
          errorEl.removeChild(errorEl.firstChild);
        }
        errorEl.appendChild(document.createTextNode(message));
      }

      function clearError() {
        reviewer.classList.remove("error");
        while (errorEl.firstChild) {
          errorEl.removeChild(errorEl.firstChild);
        }
      }

      function svgXmlToImage(svgXml, callback) {
        var pngImage = new Image(), svgImage = new Image();

        svgImage.onload = function () {
          var canvas = document.createElement("canvas");
          canvas.width = svgImage.width * scale;
          canvas.height = svgImage.height * scale;

          var context = canvas.getContext("2d");
          context.drawImage(svgImage, 0, 0, canvas.width, canvas.height);

          pngImage.src = canvas.toDataURL("image/png");
          pngImage.width = svgImage.width;
          pngImage.height = svgImage.height;

          if (callback !== undefined) {
            callback(null, pngImage);
          }
        }

        svgImage.onerror = function (e) {
          if (callback !== undefined) {
            callback(e);
          }
        }
        svgImage.src = svgXml;
      }

      // Detect content type and update UI
      function detectAndUpdateType() {
        const code = editor.getSession().getDocument().getValue();

        // Check URL override first
        const urlType = rendererMode.value==='auto'?null:rendererMode.value;
        if (urlType) {
          updateTypeIndicator(urlType);
          return urlType;
        }

        const detection = ContentDetector.detect(code);
        updateTypeIndicator(detection.type);
        return detection.type;
      }

      function updateTypeIndicator(type) {
        document.querySelectorAll('.manim-options').forEach(option => option.classList.toggle('hidden', type !== 'manim'));
        document.querySelectorAll('.modl-options').forEach(option => option.classList.toggle('hidden', type !== 'modl'));
        currentType = type;
        typeIndicator.className = type;

        if (type === 'graphviz') {
          typeIndicator.textContent = 'Graphviz';
          graphvizOptions.classList.remove('hidden');
          editor.getSession().setMode("ace/mode/dot");
        } else if (type === 'manim') {
          typeIndicator.textContent = 'Manim';
          graphvizOptions.classList.add('hidden');
          editor.getSession().setMode("ace/mode/python");
        } else if (type === 'modl') {
          typeIndicator.textContent = 'modl';
          graphvizOptions.classList.add('hidden');
          editor.getSession().setMode("ace/mode/text");
        } else {
          typeIndicator.textContent = 'Unknown';
          graphvizOptions.classList.add('hidden');
        }
      }

      // Unified render function
      async function render() {
        scheduler.cancel();
        clearError();
        invalidateRender();
        const type = detectAndUpdateType();

        if (type === 'graphviz') {
          renderGraphviz();
        } else if (type === 'manim') {
          await renderManim();
        } else if (type === 'modl') {
          renderModl();
        } else {
          // Try Graphviz as fallback
          renderGraphviz();
        }
      }

      function renderModl() {
        const revision = renderRevision;
        const saved = savedHashbin?.fingerprint === currentShareFingerprint();
        try {
          const preview = Modl.create(editor.getValue(), {
            positions: modlPositions,
            onChange: positions => {
              if (revision !== renderRevision) return;
              modlPositions = positions;
              clearShare();
              updateState();
            },
            onFrame: (svg, viewport) => {
              if (revision !== renderRevision) return;
              document.getElementById('modl-zoom').textContent = `${Number(viewport.scale.toPrecision(4))}×`;
            }
          });
          clearReviewContent();
          modlPreview = preview;
          refreshModlDownload();
          modlPositions = preview.positions();
          if (saved) savedHashbin.fingerprint = currentShareFingerprint();
          const wrapper = document.createElement('a');
          wrapper.append(preview.svg);
          reviewer.append(wrapper);
          updateState();
          show_status('done', 500);
        } catch (error) { show_error(error); }
      }

      function renderGraphviz() {
        const revision = renderRevision;
        reviewer.classList.add("working");
        reviewer.classList.remove("error");

        show_status("rendering...");
        Viz.instance().then(function (viz) {
          if (revision !== renderRevision) return;
          let dotContent = editor.getSession().getDocument().getValue();
          let options = {
            format: formatEl.value,
            engine: engineEl.value,
          };
          let result = null;

          if (["svg", "png"].indexOf(formatEl.value) > -1) {
            result = viz.renderSVGElement(dotContent, options);
          } else {
            result = viz.render(dotContent, options);
          }

          if (result.status !== undefined && result.status != "success") {
            show_error(result.errors && result.errors.length > 0 && result.errors[0] || result);
          } else {
            updateGraphvizOutput(result);
          }
        }).catch((err) => {
          if (revision === renderRevision) show_error(err);
        }).finally(() => {
          if (revision !== renderRevision) return;
          reviewer.classList.remove("working");
          if (!reviewer.classList.contains("error")) show_status("done", 500)
        });
      }

      const mathMetrics = new Map();
      const typstSvgs = new Map();
      async function renderManim() {
        const revision = renderRevision;
        reviewer.classList.add('working');
        setRenderBusy(true);
        show_status('rendering Manim…');
        try {
          const code = editor.getSession().getDocument().getValue();
          const sceneName = sceneNameInput.value.trim();
          const renderOptions = () => ({ sceneName, mathMetrics: Object.fromEntries(mathMetrics),
            typstSvgs: Object.fromEntries(typstSvgs) });
          let sceneData = await manimClient.render(code, renderOptions());
          if (revision !== renderRevision) return;
          // Typst documents are compiled here (typst.ts) and imported by Python on a second pass.
          if ((sceneData.typst_pending || []).length) {
            pyodideStatus.textContent = 'Compiling Typst…';
            const compiled = await ManimTypst.compile(sceneData.typst_pending, () => revision === renderRevision);
            if (revision !== renderRevision || !compiled) return;
            for (const [source, svg] of Object.entries(compiled)) {
              typstSvgs.delete(source);
              typstSvgs.set(source, svg);
              if (typstSvgs.size > 256) typstSvgs.delete(typstSvgs.keys().next().value);
            }
            sceneData = await manimClient.render(code, renderOptions());
            if (revision !== renderRevision) return;
          }
          const expressions = ManimMath.expressions(sceneData);
          if (expressions.size) pyodideStatus.textContent = 'Rendering math…';
          sceneData.mathGlyphs = await ManimMath.prepare(sceneData, () => revision === renderRevision);
          if (revision !== renderRevision) return;
          for (const [expression, size] of Object.entries(ManimMath.metrics(sceneData.mathGlyphs))) {
            mathMetrics.delete(expression);
            mathMetrics.set(expression, size);
            if (mathMetrics.size > 1024) mathMetrics.delete(mathMetrics.keys().next().value);
          }
          // Python placed unmeasured formulas with estimates; repeat once with real sizes.
          if ((sceneData.math_estimated || []).some(expression => mathMetrics.has(expression))) {
            pyodideStatus.textContent = 'Placing math…';
            sceneData = await manimClient.render(code, renderOptions());
            if (revision !== renderRevision) return;
            sceneData.mathGlyphs = await ManimMath.prepare(sceneData, () => revision === renderRevision);
            if (revision !== renderRevision) return;
          }
          sceneNamesList.replaceChildren(...sceneData.scenes.map(name => {
            const option = document.createElement('option');
            option.value = name;
            return option;
          }));
          updateManimOutput(sceneData);
          window.dispatchEvent(new Event('manim-rendered'));
          pyodideStatus.textContent = 'Python ready';
          pyodideStatus.className = 'ready';
          show_status('done', 500);
        } catch (error) {
          if (revision !== renderRevision || error.name === 'AbortError') return;
          pyodideStatus.textContent = 'Render failed';
          pyodideStatus.className = '';
          show_error(error);
        } finally {
          if (revision === renderRevision) {
            reviewer.classList.remove('working');
            setRenderBusy(false);
          }
        }
      }

      function updateGraphvizOutput(result) {
        const revision = renderRevision;
        if (formatEl.value === "svg") {
          document.querySelector("#raw").classList.remove("disabled");
          rawEl.disabled = false;
        } else {
          document.querySelector("#raw").classList.add("disabled");
          rawEl.disabled = true;
        }

        clearReviewContent();

        if (!result) {
          return;
        }

        reviewer.classList.remove("working");
        reviewer.classList.remove("error");

        if (formatEl.value == "svg" && !rawEl.checked) {
          var serializer = new XMLSerializer();
          var source = serializer.serializeToString(result);
          const url = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(source);
          downloadBtn.href = url;
          downloadBtn.download = "diagram.svg";
          var a = document.createElement("a");
          a.appendChild(result);
          reviewer.appendChild(a);
          svgPanZoom(result, {
            zoomEnabled: true,
            controlIconsEnabled: true,
            fit: true,
            center: true,
            customEventsHandler: touchPanZoom(),
          });
        } else if (formatEl.value == "png") {
          var serializer = new XMLSerializer();
          var source = serializer.serializeToString(result);
          let resultWithPNGHeader = "data:image/svg+xml;base64," + btoa(unescape(encodeURIComponent(source)));
          svgXmlToImage(resultWithPNGHeader, function (err, image) {
            if (revision !== renderRevision) return;
            if (err) {
              show_error(err)
              return
            }
            image.setAttribute("title", "diagram");
            downloadBtn.href = image.src;
            downloadBtn.download = "diagram.png";
            var a = document.createElement("a");
            a.appendChild(image);
            reviewer.appendChild(a);
          })
        } else {
          var text = document.createElement("div");
          text.id = "text";
          if (formatEl.value == "svg") {
            let serializer = new XMLSerializer();
            result = serializer.serializeToString(result);
          } else {
            result = result.output;
          }
          text.appendChild(document.createTextNode(result));
          reviewer.appendChild(text);
        }

        updateState();
      }

      function updateManimOutput(sceneData) {
        clearReviewContent();
        reviewer.classList.remove('working', 'error');
        player = new ManimPlayer(reviewer, sceneData, svg => {
          const source = new XMLSerializer().serializeToString(svg);
          downloadBtn.href = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(source);
          downloadBtn.download = 'manim.svg';
        });
        updateState();
      }

      function clearReviewContent() {
        if (sampleVideo) { sampleVideo.remove(); sampleVideo = null; }
        if (modlPreview) { modlPreview.destroy(); modlPreview = null; }
        if (player) { player.destroy(); player = null; }
        var text = reviewer.querySelector("#text");
        if (text) {
          reviewer.removeChild(text);
        }

        var a = reviewer.querySelector("a");
        if (a) {
          reviewer.removeChild(a);
        }
      }

      function applySceneToURL(url) {
        const scene = sceneNameInput.value.trim();
        if (currentType === 'manim' && scene) url.searchParams.set('scene', scene);
        else url.searchParams.delete('scene');
      }

      function updateState() {
        try {urlState.cancel();const href=savedHashbin?.fingerprint===currentShareFingerprint()?urlState.link(location.href,savedHashbin.cid):urlState.build(sourceSnapshot(),{run:autoRun,view:new URL(location.href).searchParams.get('view')||undefined}).href;history.replaceState(null,'',href);lastOpened=href;}catch(error){show_error(error);}
      }

      // Set editor theme based on detected type
      editor.setTheme("ace/theme/twilight");

      // Debounced change handler
      editor.getSession().on("change", function () {
        if(applying)return;drafts.attempt(sourceSnapshot(),true);hashbinPanel.cancelLoad();navigationRevision++;urlState.cancel();exampleLoader.cancel();
        invalidateRender();sceneNamesList.replaceChildren();
        try{lastOpened=urlState.write(sourceSnapshot(),{run:autoRun,view:new URL(location.href).searchParams.get('view')||undefined});}catch(error){show_error(error);return;}
        if(autoRun)scheduler.schedule();
      });

      window.addEventListener('popstate',()=>openURL(location.href));
      window.addEventListener('hashchange',()=>openURL(location.href));
      editor.commands.on('afterExec',event=>{if(!event.command.readOnly)drafts.attempt(sourceSnapshot(),true);});
      sceneNameInput.addEventListener('input', () => {
        exampleLoader.cancel();
        invalidateRender();
        navigationRevision++;try{lastOpened=urlState.write(sourceSnapshot(),{run:autoRun,view:new URL(location.href).searchParams.get('view')||undefined});}catch(error){show_error(error);return;}if(autoRun)scheduler.schedule({ detect: false });
      });
      sceneNameInput.addEventListener('keydown', event => {
        if (event.key === 'Enter') {autoRun=true;render();}
      });
      for(const select of [formatEl,engineEl])select.addEventListener('change',()=>{navigationRevision++;updateState();if(autoRun)render();});
      rawEl.addEventListener("change", render);


      HTMLOptionsCollection.prototype.indexOf = function (name) {
        for (let i = 0; i < this.length; i++) {
          if (this[i].value == name) {
            return i;
          }
        }
        return -1;
      };

      tabs=mountMobileTabs({desktop:true,container:tabBar,panels:[{label:'Code',panel:editorElement},{label:'Preview',panel:reviewElement}],onChange:index=>{isCollapsed=index===1;editorElement.classList.remove('collapsed');reviewElement.classList.remove('expanded');optionsElement.classList.remove('expanded');toggleBtn.classList.toggle('collapsed',isCollapsed);splitter.style.display='';splitter.style.opacity='';updatePanelSizes(currentSplitPercentage);updateToggleLabel();resizeWorkspace();requestAnimationFrame(()=>{editor.resize();resizeSVG();});}});
      if(mobileLayout.matches)tabs.select(1);
      let lastOpened;
      async function openURL(href,{initial=false}={}) {
        if(!initial&&lastOpened===href)return;lastOpened=href;
        const revision=++navigationRevision;urlState.cancel();scheduler.cancel();exampleLoader.cancel();invalidateRender();
        try{
          const intent=urlState.parse(href);autoRun=intent.run;
          document.body.classList.toggle('presentation',new URL(href).searchParams.has('presentation')||Boolean(intent.view));
          if(intent.kind==='publish'){
            const result=await hashbinStore.published(intent.hash);if(revision!==navigationRevision)return;
            if(result?.snapshot)applyLoadedSource(result.snapshot,result.cid??null,{run:intent.run&&result.snapshot.autorun,cancel:false});
            if(result){hashbinPanel.status.textContent=result.error||'Saved to HashBin.';setMoreOpen(true);}
          }else if(intent.kind==='source')applyLoadedSource(intent.doc,null,{run:intent.run,cancel:false});
          else if(intent.kind==='example'){drafts.opened();await exampleLoader.load(intent.id);}
          else if(intent.kind==='cid'){
            hashbinPanel.status.textContent='Loading from HashBin…';
            const doc=await hashbinStore.load(intent.cid);if(revision!==navigationRevision)return;
            applyLoadedSource(doc,intent.cid,{run:intent.run,cancel:false});hashbinPanel.status.textContent='Loaded from HashBin.';
          }else if(intent.kind==='remote'){
            const response=await fetch(intent.url);if(!response.ok)throw Error('Source load failed (HTTP '+response.status+').');
            const source=text(await readResponse(response,config.maxBytes));if(revision!==navigationRevision)return;
            const query=new URL(href);query.searchParams.delete('url');query.hash=encodeURIComponent(source);
            applyLoadedSource(urlState.parse(query.href).doc,null,{run:intent.run,cancel:false});
          }else if(initial){rendererMode.value='auto';detectAndUpdateType();if(autoRun)render();}
        }catch(error){if(revision===navigationRevision){show_error(error);hashbinPanel.status.textContent=error.message;}}
      }
      globalThis.ManimOnline={editor,snapshot:sourceSnapshot,openURL,render};
      document.body.dataset.ready='true';
      hashbinStore.retireLegacyTokens().catch(()=>{});
      initOffline(shell);
      await openURL(location.href,{initial:true});
    })(document);
