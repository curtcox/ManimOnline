export class OfflineClient {
  constructor({ url = './service-worker.js', navigator = globalThis.navigator, timeout = 30000, onStatus = () => {}, onUpdate = () => {} } = {}) {
    Object.assign(this, { url, navigator, timeout, onStatus, onUpdate });
  }
  async init() {
    if (!this.navigator?.serviceWorker) { this.onStatus({ ready: false, unsupported: true }); return null; }
    this.registration = await this.navigator.serviceWorker.register(this.url);
    if (!this.registration) { this.onStatus({ ready: false, unsupported: true }); return null; }
    const announce = () => { if (this.registration.waiting) this.onUpdate(this.registration); };
    announce();
    this.registration.addEventListener('updatefound', () => this.registration.installing?.addEventListener('statechange', announce));
    this.navigator.serviceWorker.addEventListener('controllerchange', () => { void this.status().catch(error => this.onStatus({ ready: false, error: error.message })); });
    let timer, statechange;
    const installing = this.registration.installing;
    try {
      await Promise.race([
        this.navigator.serviceWorker.ready,
        new Promise((_, reject) => {
          timer = setTimeout(() => reject(new Error('Offline installation timed out. Use Repair offline copy to retry.')), this.timeout);
          statechange = () => { if (installing.state === 'redundant') reject(new Error('Offline installation failed verification. Reconnect and retry.')); };
          installing?.addEventListener('statechange', statechange);
          if (installing) statechange();
        }),
      ]);
    } finally { clearTimeout(timer); if (statechange) installing?.removeEventListener('statechange', statechange); }
    return this.status();
  }
  async request(type, worker = this.registration?.active ?? this.navigator.serviceWorker?.controller) {
    if (!worker) return { ready: false };
    return new Promise((resolve, reject) => {
      const channel = new MessageChannel();
      const cleanup = () => { clearTimeout(timer); channel.port1.close(); };
      const timer = setTimeout(() => { cleanup(); reject(new Error('Offline status request timed out.')); }, this.timeout);
      channel.port1.onmessage = event => { cleanup(); resolve(event.data); };
      worker.postMessage({ type }, [channel.port2]);
    });
  }
  async status() { const result = await this.request('offline-status'); this.onStatus(result); return result; }
  async repair() { const result = await this.request('repair-offline'); this.onStatus(result); return result; }
  async update() { await this.registration?.update(); return this.registration?.waiting; }
  activateUpdate() { this.registration?.waiting?.postMessage({ type: 'activate-update' }); }
}
