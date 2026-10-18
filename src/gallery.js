/* Gallery playback reads bundled media only; Python stays in the editor. */
(() => {
  const grid = document.getElementById('sample-grid');
  const search = document.getElementById('sample-search');
  const type = document.getElementById('sample-type');
  const names = { manim: 'MANIM ANIMATION', graphviz: 'GRAPHVIZ DOT', modl: 'MODL DIAGRAM' };
  const cards = [];
  // A previous service worker may supply a catalog containing only id/label/path.
  // Derive the gallery fields instead of making links and images from undefined.
  for (const entry of ExampleCatalog) {
    const type = entry.type || (entry.path.endsWith('.py') ? 'manim' : entry.path.endsWith('.dot') ? 'graphviz' : 'modl');
    const example = { ...entry, type,
      cover: entry.cover || `gallery/previews/${entry.id}.png`,
      video: entry.video ?? (type === 'manim' ? `gallery/previews/${entry.id}.mp4` : null),
      editorURL: entry.editorURL || `./?url=${encodeURIComponent(entry.path)}`
    };
    const card = document.createElement('article');
    card.className = 'card';
    card.id = example.id;
    const preview = document.createElement('div');
    preview.className = 'preview';
    const cover = document.createElement('img');
    cover.src = example.cover;
    cover.alt = `Preview of ${example.label}`;
    cover.loading = 'lazy';
    cover.width = 480;
    cover.height = 270;
    preview.appendChild(cover);
    const details = document.createElement('div');
    details.className = 'details';
    const language = document.createElement('p');
    language.className = 'language';
    language.textContent = names[example.type];
    const title = document.createElement('h2');
    title.textContent = example.label;
    const load = document.createElement('a');
    load.className = 'load';
    load.href = example.editorURL;
    load.textContent = 'Load in editor →';
    load.setAttribute('aria-label', `Load ${example.label} in editor`);
    details.append(language, title);
    // Older cached galleries load without video-links.js.
    const lesson = globalThis.VideoLinks?.examples[example.id];
    if (lesson) {
      const watch = document.createElement('a');
      watch.className = 'watch';
      watch.href = lesson.url;
      watch.target = '_blank';
      watch.rel = 'noopener';
      watch.textContent = `▶ Video: episode ${lesson.episode} · ${lesson.chapter}`;
      watch.setAttribute('aria-label', `Watch ${lesson.chapter}, Drawing with Code episode ${lesson.episode}, on YouTube`);
      details.appendChild(watch);
    }
    details.appendChild(load);
    let video;
    if (example.video) {
      video = document.createElement('video');
      video.preload = 'none';
      video.poster = example.cover;
      video.controls = true;
      video.muted = true;
      video.playsInline = true;
      video.hidden = true;
      video.setAttribute('aria-label', `${example.label} animation preview`);
      const button = document.createElement('button');
      button.className = 'play';
      button.type = 'button';
      button.textContent = '▶ Play preview';
      button.setAttribute('aria-label', `Play ${example.label} preview`);
      button.addEventListener('click', () => {
        video.src = example.video;
        video.hidden = false;
        cover.hidden = true;
        button.hidden = true;
        video.focus();
        video.play().catch(() => { /* Native controls allow retry if autoplay is blocked. */ });
      });
      video.addEventListener('play', () => {
        for (const other of grid.querySelectorAll('video')) if (other !== video) other.pause();
      });
      video.addEventListener('error', () => {
        cover.hidden = false;
        video.hidden = true;
        button.hidden = false;
        button.textContent = '↻ Retry preview';
        if (!details.querySelector('.preview-error')) {
          const error = document.createElement('p');
          error.className = 'preview-error';
          error.setAttribute('role', 'status');
          error.textContent = 'Preview could not play. Retry, or load the sample in the editor.';
          details.appendChild(error);
        }
      });
      video.addEventListener('playing', () => details.querySelector('.preview-error')?.remove());
      preview.append(video, button);
    }
    card.append(preview, details);
    grid.appendChild(card);
    cards.push({ card, example, video });
  }
  function filter() {
    const query = search.value.trim().toLowerCase();
    let count = 0;
    for (const { card, example, video } of cards) {
      card.hidden = !(type.value === 'all' || example.type === type.value) ||
        !`${example.label} ${example.type} ${example.id}`.toLowerCase().includes(query);
      if (card.hidden) video?.pause(); else count++;
    }
    document.getElementById('sample-count').textContent = `${count} of ${cards.length} samples`;
    document.getElementById('no-samples').hidden = count !== 0;
  }
  search.addEventListener('input', filter);
  type.addEventListener('change', filter);
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) for (const { video } of cards) video?.pause();
  });
  filter();
})();
