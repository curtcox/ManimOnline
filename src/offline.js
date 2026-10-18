/** Offline preparation must succeed before the page promises offline rendering. */
(async () => {
  const status = document.getElementById('offline-status');
  const button = document.getElementById('offline-action');
  if (!('serviceWorker' in navigator)) { status.textContent = 'Offline saving unavailable'; return; }
  let registration;
  let reloadForUpdate = false;
  let controlled = Boolean(navigator.serviceWorker.controller);
  // After a live render the worker saves Python and MathJax too (they are not part of install).
  let rendered = false;
  const statusCheck = () => rendered ? 'cache-runtime' : 'offline-status';
  window.addEventListener('manim-rendered', () => {
    if (rendered) return;
    rendered = true;
    if (navigator.serviceWorker.controller) check('cache-runtime');
  });
  function pythonPending() {
    status.textContent = 'Diagrams ready offline';
    button.textContent = 'Save Python offline';
    button.hidden = false;
  }
  function failed() {
    status.textContent = 'Offline setup incomplete';
    button.textContent = 'Retry offline setup';
    button.hidden = false;
  }
  async function check(type = 'offline-status') {
    const worker = navigator.serviceWorker.controller;
    if (!worker) return;
    const channel = new MessageChannel();
    await new Promise(resolve => {
      const timer = setTimeout(() => { channel.port1.close(); failed(); resolve(); }, type === 'offline-status' ? 5000 : 90000);
      channel.port1.onmessage = event => {
        clearTimeout(timer);
        channel.port1.close();
        if (event.data.ready) { status.textContent = 'Ready offline'; button.hidden = true; }
        // Workers from before the runtime split report no `installed` flag.
        else if (event.data.installed) pythonPending();
        else failed();
        if (registration?.waiting) updateReady();
        resolve();
      };
      worker.postMessage({ type }, [channel.port2]);
    });
  }
  function updateReady() {
    status.textContent = 'Offline update ready';
    button.textContent = 'Update and reload';
    button.hidden = false;
  }
  function watch(worker) {
    if (!worker) return;
    status.textContent = 'Saving for offline use…';
    worker.addEventListener('statechange', () => {
      if (worker.state === 'redundant') failed();
      if (worker.state === 'installed' && navigator.serviceWorker.controller) updateReady();
      if (worker.state === 'activated') check(statusCheck());
    });
  }
  navigator.serviceWorker.addEventListener('controllerchange', () => {
    if (reloadForUpdate || controlled) {
      // An update activated in another tab also needs matching page scripts.
      window.dispatchEvent(new Event('offline-before-reload'));
      location.reload();
    } else { controlled = true; check(statusCheck()); }
  });
  button.addEventListener('click', async () => {
    button.hidden = true;
    if (registration?.waiting) {
      reloadForUpdate = true;
      registration.waiting.postMessage({ type: 'activate-update' });
    } else {
      status.textContent = 'Saving for offline use…';
      try { await register(); await registration.update(); await check('repair-offline'); } catch (_) { failed(); }
    }
  });
  async function register() {
    registration = await navigator.serviceWorker.register('service-worker.js', { updateViaCache: 'none' });
    registration.addEventListener('updatefound', () => watch(registration.installing));
    watch(registration.installing);
    if (registration.waiting) updateReady();
  }
  try { status.textContent = 'Saving for offline use…'; await register(); await check(statusCheck()); }
  catch (_) { failed(); }
})();
