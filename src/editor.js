/* Editor orchestration, loaded last so every helper script is available. Indentation is kept from its inline origin. */
    const editorElement = document.getElementById('editor');
    const reviewElement = document.getElementById('review');
    const optionsElement = document.getElementById('options');
    // Wrapped controls must not cover the preview when the panel is narrow.
    new ResizeObserver(() => {
      reviewElement.style.top = `${optionsElement.offsetHeight}px`;
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
    const viewPreview = document.getElementById('view-preview');
    const viewCode = document.getElementById('view-code');
    const moreToggle = document.getElementById('more-toggle');
    function updateToggleLabel() {
      toggleBtn.textContent = isCollapsed ? '▶' : '◀';
      toggleBtn.setAttribute('aria-expanded', String(!isCollapsed));
      toggleBtn.setAttribute('aria-label', isCollapsed ? 'Show code editor' : 'Hide code editor');
      viewPreview.setAttribute('aria-pressed', String(isCollapsed));
      viewCode.setAttribute('aria-pressed', String(!isCollapsed));
      ace.edit('editor').getSession().setUseWrapMode(mobileLayout.matches);
    }
    mobileLayout.addEventListener('change', updateToggleLabel);
    // On phones Preview and Code are tabs: the collapsed editor means the preview is showing.
    function showCode(visible) {
      if (visible === isCollapsed) toggleBtn.click();
    }
    viewPreview.addEventListener('click', () => showCode(false));
    viewCode.addEventListener('click', () => showCode(true));
    function setMoreOpen(open) {
      optionsElement.classList.toggle('more-open', open);
      moreToggle.setAttribute('aria-expanded', String(open));
      moreToggle.textContent = open ? 'Less' : 'More';
    }
    moreToggle.addEventListener('click', () => setMoreOpen(!optionsElement.classList.contains('more-open')));
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

    toggleBtn.addEventListener('click', () => {
      isCollapsed = !isCollapsed;

      if (isCollapsed) {
        editorElement.style.transition = 'width 0.3s ease';
        splitter.style.transition = 'left 0.3s ease, opacity 0.3s ease';
        reviewElement.style.transition = 'left 0.3s ease';
        optionsElement.style.transition = 'left 0.3s ease';

        editorElement.classList.add('collapsed');
        reviewElement.classList.add('expanded');
        optionsElement.classList.add('expanded');
        toggleBtn.classList.add('collapsed');
        splitter.style.opacity = '0';
        splitter.style.left = '0';
        updateToggleLabel();

        setTimeout(() => {
          splitter.style.display = 'none';
        }, 300);
      } else {
        splitter.style.left = '0';
        splitter.style.opacity = '0';
        splitter.style.display = 'flex';

        editorElement.style.transition = 'width 0.3s ease';
        splitter.style.transition = 'left 0.3s ease, opacity 0.3s ease';
        reviewElement.style.transition = 'left 0.3s ease';
        optionsElement.style.transition = 'left 0.3s ease';

        setTimeout(() => {
          editorElement.classList.remove('collapsed');
          reviewElement.classList.remove('expanded');
          optionsElement.classList.remove('expanded');
          toggleBtn.classList.remove('collapsed');
          updateToggleLabel();
          updatePanelSizes(currentSplitPercentage);
          splitter.style.opacity = '1';
        }, 10);
      }

      setTimeout(resizeSVG, 300);
    });
    // Phone visitors mostly watch, so they start on the preview.
    if (mobileLayout.matches) toggleBtn.click();
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
        shareURLEl = document.querySelector("#shareurl"),
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
        redirectUri: location.origin + location.pathname.replace(/index\.html$/, ''),
        storage: storage('localStorage'), transactionStorage: storage('sessionStorage')
      });
      function sourceSnapshot() {
        const src = editor.getValue();
        const type = rendererMode.value === 'auto' ? ContentDetector.detect(src).type : rendererMode.value;
        return { src, type, scene: sceneNameInput.value, engine: engineEl.value,
          outputFormat: formatEl.value, pos: modlPositions };
      }
      const hashbinPanel = new HashBinPanel({ store: hashbinStore, getSnapshot: sourceSnapshot,
        getFingerprint: currentShareFingerprint,
        onLoad: applyLoadedSource,
        onSaved: (cid, fingerprint, link) => {
          savedHashbin = { cid, fingerprint };
          history.pushState(null, '', link);
          clearShare();
          shareURLEl.style.display = 'inline';
          shareURLEl.value = link;
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
      let typed = false;
      function applyLoadedSource(snapshot, cid = null) {
        typed = false;
        showVideoLink(cid && globalThis.VideoLinks?.snippets[cid]);
        const url = new URL(location.href);
        for (const key of ['example', 'raw', 'compressed', 'url', 'type', 'scene', 'engine', 'format', 'modlpos']) url.searchParams.delete(key);
        if (snapshot.type) url.searchParams.set('type', snapshot.type === 'graphviz' ? 'dot' : snapshot.type);
        url.hash = cid || encodeURIComponent(snapshot.src);
        history.replaceState(null, '', url);
        modlPositions = HashBinDocuments.positions(snapshot.pos);
        sceneNameInput.value = snapshot.scene || '';
        if (['dot','circo','fdp','nop','nop2','neato','sfdp','twopi','osage','patchwork'].includes(snapshot.engine)) engineEl.value = snapshot.engine;
        else engineEl.value = 'dot';
        if (['svg','png','json','xdot','plain','ps'].includes(snapshot.outputFormat)) formatEl.value = snapshot.outputFormat;
        else formatEl.value = 'svg';
        editor.setValue(snapshot.src, -1);
        detectAndUpdateType();
        savedHashbin = cid ? { cid, fingerprint: currentShareFingerprint() } : null;
        render();
      }
      const shareClient = new ShareClient();
      const shortenShare = document.getElementById('shorten-share');
      const shareStatus = document.getElementById('share-status');
      let shareSnapshot = null;
      let shareFingerprint = '';
      function currentShareFingerprint() {
        return JSON.stringify([editor.getSession().getDocument().getValue(),
          rendererMode.value, sceneNameInput.value, engineEl.value, formatEl.value, modlPositions]);
      }
      function clearShare() {
        shareClient.cancel();
        shareSnapshot = null;
        shareFingerprint = '';
        shareURLEl.value = '';
        shareURLEl.style.display = 'none';
        shortenShare.hidden = true;
        shortenShare.disabled = false;
        shareStatus.textContent = '';
      }
      shortenShare.addEventListener('click', async () => {
        if (!shareSnapshot) return;
        const snapshot = shareSnapshot;
        shortenShare.disabled = true;
        shareStatus.textContent = 'Shortening link…';
        const result = await shareClient.shorten(snapshot);
        if (snapshot !== shareSnapshot || !result) return;
        shareURLEl.value = result.url;
        shortenShare.disabled = false;
        shareStatus.textContent = result.shortened ? 'Short link ready.' : result.error.message;
      });
      const rendererMode = document.getElementById('renderer-mode');
      let exportingPNG = false;
      const frameFormat = document.getElementById('manim-export-format');
      const exportStatus = document.getElementById('export-status');
      window.addEventListener('offline-before-reload', () => {
        const url = new URL(location.href);
        for (const parameter of ['example', 'raw', 'compressed', 'url']) url.searchParams.delete(parameter);
        url.hash = encodeURIComponent(editor.getSession().getDocument().getValue());
        applySceneToURL(url);
        history.replaceState(null, '', url);
      });
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
        onStatus: message => { exampleStatus.textContent = message; },
        onError: error => { exampleStatus.textContent = error.message; },
        onLoad: (source, example) => {
          savedHashbin = null;
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
          editor.getSession().setValue(source);
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
        if (shareSnapshot && shareFingerprint !== currentShareFingerprint()) clearShare();
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
      rendererMode.addEventListener('change', () => {
        exampleLoader.cancel();
        const url = new URL(location.href);
        // Preserve the latest edits even when the previous render failed.
        for (const parameter of ['example', 'raw', 'compressed', 'url']) url.searchParams.delete(parameter);
        url.hash = encodeURIComponent(editor.getSession().getDocument().getValue());
        if (rendererMode.value === 'auto') url.searchParams.delete('type');
        else url.searchParams.set('type', rendererMode.value === 'graphviz' ? 'dot' : rendererMode.value);
        history.replaceState(null, '', url);
        render();
      });

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

      function copyShareURL(e) {
        clearShare();
        const code = editor.getSession().getDocument().getValue();
        const mode = rendererMode.value;
        shareSnapshot = ShareLinks.build({ url: location.href, code, mode,
          type: mode === 'auto' ? ContentDetector.detect(code).type : mode,
          scene: sceneNameInput.value, engine: engineEl.value, format: formatEl.value,
          positions: modlPositions,
          compress: typeof LZString === 'undefined' ? null : text => LZString.compressToEncodedURIComponent(text) });
        shareFingerprint = currentShareFingerprint();
        shareURLEl.style.display = 'inline';
        shareURLEl.value = shareSnapshot.fallback;
        shareURLEl.select();
        shortenShare.hidden = false;
        shareStatus.textContent = 'Source link ready to copy.';
      }

      // Detect content type and update UI
      function detectAndUpdateType() {
        const code = editor.getSession().getDocument().getValue();

        // Check URL override first
        const urlType = ContentDetector.getTypeFromURL();
        rendererMode.value = urlType || 'auto';
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
        const updatedUrl = new URL(window.location)
        for (const parameter of ['example', 'raw', 'compressed', 'url', 'modlpos']) updatedUrl.searchParams.delete(parameter);
        const content = encodeURIComponent(editor.getSession().getDocument().getValue());
        updatedUrl.hash = savedHashbin?.fingerprint === currentShareFingerprint() ? savedHashbin.cid : content;
        if (currentType === 'modl' && Object.keys(modlPositions).length) updatedUrl.searchParams.set('modlpos', JSON.stringify(modlPositions));
        applySceneToURL(updatedUrl);
        if (currentType === 'graphviz') {
          updatedUrl.searchParams.set("engine", engineEl.value)
        }
        history.replaceState({ "content": content, "type": currentType }, "", updatedUrl.toString())
      }

      // Set editor theme based on detected type
      editor.setTheme("ace/theme/twilight");

      // Debounced change handler
      editor.getSession().on("change", function () {
        exampleLoader.cancel();
        invalidateRender();
        sceneNamesList.replaceChildren();
        scheduler.schedule();
      });

      window.onpopstate = function (event) {
        if (event.state != null && event.state.content != undefined) {
          editor.getSession().setValue(decodeURIComponent(event.state.content));
        }
      };
      editor.commands.on('afterExec', event => { if (!event.command.readOnly) typed = true; });
      window.addEventListener('hashchange', () => {
        if (!HashBinDocuments.isCID(location.hash.slice(1))) return;
        if (typed && !confirm('This link opens different source. Replace your unsaved edits?')) return;
        hashbinPanel.load(location.hash);
      });

      sceneNameInput.addEventListener('input', () => {
        exampleLoader.cancel();
        invalidateRender();
        scheduler.schedule({ detect: false });
      });
      sceneNameInput.addEventListener('keydown', event => {
        if (event.key === 'Enter') render();
      });
      formatEl.addEventListener("change", render);
      engineEl.addEventListener("change", render);
      rawEl.addEventListener("change", render);
      shareEl.addEventListener("click", copyShareURL);

      HTMLOptionsCollection.prototype.indexOf = function (name) {
        for (let i = 0; i < this.length; i++) {
          if (this[i].value == name) {
            return i;
          }
        }
        return -1;
      };

      // URL parameter parsing
      hashbinStore.retireLegacyTokens().catch(() => { /* Retried on the next load. */ });
      const publishRevision = renderRevision;
      const published = await hashbinStore.published(location.hash);
      if (published) {
        history.replaceState(null, '', location.pathname + location.search);
        if (publishRevision === renderRevision && published.snapshot) applyLoadedSource(published.snapshot, published.cid || null);
        hashbinPanel.status.textContent = published.error || 'Saved to HashBin.';
        setMoreOpen(true);
        if (published.snapshot) return;
      }
      const params = new URLSearchParams(location.search.substring(1));
      try { modlPositions = HashBinDocuments.positions(JSON.parse(params.get('modlpos') || '{}')); } catch (_) { /* Ignore invalid layout. */ }
      sceneNameInput.value = params.get('scene') || '';

      if (params.has('engine')) {
        const engine = params.get('engine');
        const index = engineEl.options.indexOf(engine);
        if (index > -1) {
          engineEl.selectedIndex = index;
        }
      }

      if (params.has('format')) {
        const format = params.get('format');
        const index = formatEl.options.indexOf(format);
        if (index > -1) {
          formatEl.selectedIndex = index;
        }
      }

      if (params.has("presentation")) {
        document.body.classList.add("presentation");
      }

      if (params.has('example')) {
        await exampleLoader.load(params.get('example'));
      } else if (params.has('raw')) {
        editor.getSession().setValue(params.get('raw'));
        render();
      } else if (params.has('compressed')) {
        const compressed = params.get('compressed');
        editor.getSession().setValue(LZString.decompressFromEncodedURIComponent(compressed));
        render();
      } else if (params.has('url')) {
        const url = params.get('url');
        const revision = renderRevision;
        let ok = false;
        fetch(url)
          .then(res => {
            ok = res.ok;
            return res.text();
          })
          .then(res => {
            if (revision !== renderRevision) return;
            if (!ok) {
              throw { message: res };
            }
            editor.getSession().setValue(res);
            render();
          }).catch(e => {
            if (revision === renderRevision) show_error(e);
          });
      } else if (HashBinDocuments.isCID(location.hash.slice(1))) {
        hashbinPanel.load(location.hash);
      } else if (location.hash.length > 1) {
        editor.getSession().setValue(decodeURIComponent(location.hash.substring(1)));
        render();
      } else if (editor.getValue()) {
        // Initial render with default content
        detectAndUpdateType();
        render();
      }

    })(document);
