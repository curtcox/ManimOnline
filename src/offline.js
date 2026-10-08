/** Offline preparation must succeed before the page promises offline rendering. */
(async () => {
  const status = document.getElementById('offline-status');
  const button = document.getElementById('offline-action');
  if (!('serviceWorker' in navigator)) { status.textContent = 'Offline saving unavailable'; return; }
  let registration;
  let reloadForUpdate = false;
  let controlled = Boolean(navigator.serviceWorker.controller);
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
      const timer = setTimeout(() => { channel.port1.close(); failed(); resolve(); }, type === 'repair-offline' ? 90000 : 5000);
      channel.port1.onmessage = event => {
        clearTimeout(timer);
        channel.port1.close();
        status.textContent = event.data.ready ? 'Ready offline' : 'Offline setup incomplete';
        if (!event.data.ready) failed();
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
      if (worker.state === 'activated') check();
    });
  }
  navigator.serviceWorker.addEventListener('controllerchange', () => {
    if (reloadForUpdate || controlled) {
      // An update activated in another tab also needs matching page scripts.
      window.dispatchEvent(new Event('offline-before-reload'));
      location.reload();
    } else { controlled = true; check(); }
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
  try { status.textContent = 'Saving for offline use…'; await register(); await check(); }
  catch (_) { failed(); }
})();
