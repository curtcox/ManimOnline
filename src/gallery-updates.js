/* Bring returning visitors' cached editors and catalogs up to the current release. */
(() => {
  if (!('serviceWorker' in navigator)) return;
  navigator.serviceWorker.addEventListener('controllerchange', () => {
    // The first claim can also replace a catalog reused from an older HTTP cache.
    // Always reload matching gallery scripts; editor tabs preserve edits separately.
    location.reload();
  });
  navigator.serviceWorker.register('service-worker.js', { updateViaCache: 'none' }).then(async registration => {
    const activate = () => registration.waiting?.postMessage({ type: 'activate-update' });
    const watch = worker => {
      if (!worker) return;
      worker.addEventListener('statechange', () => {
        if (worker.state === 'installed') activate();
      });
    };
    registration.addEventListener('updatefound', () => watch(registration.installing));
    watch(registration.installing);
    // Also release an already-installed update from an older application version.
    activate();
    await registration.update();
    activate();
  }).catch(() => { /* Existing previews and source links remain usable if offline. */ });
})();
