/* Scenes run in a worker inside an opaque-origin iframe (HashBin SDK createSandbox), so code from
   links cannot reach this origin's storage, cookies, service worker or pages. */
(() => {
const PYODIDE_URL = 'https://cdn.jsdelivr.net/pyodide/v0.27.0/full/';
const ManimSandbox = {
  // Fetched through the service worker, which serves only hash-verified bytes.
  source() {
    this.text ||= fetch('src/unified-worker.js?v=2').then(response => {
      if (!response.ok) throw new Error('Unable to load the browser animation runtime.');
      return response.text();
    });
    this.text.catch(() => { this.text = null; });
    return this.text;
  },
  // ManimClient needs a worker at once; the SDK loads first, so messages wait in a queue.
  factory({ loadSDK = () => loadHashBinSDK(), base = new URL('src/', location.href).href } = {}) {
    return () => {
      const worker = { onmessage: null, onerror: null, queue: [], sandbox: null, closed: false,
        postMessage(data) { if (this.sandbox) this.sandbox.postMessage(data); else this.queue.push(data); },
        terminate() { this.closed = true; this.sandbox?.terminate(); } };
      loadSDK().then(sdk => {
        if (worker.closed) return;
        const sandbox = worker.sandbox = sdk.createSandbox({ source: this.source(), base,
          proxy: [PYODIDE_URL, new URL('manim-lite.py', base).href, new URL('text-outlines.json', base).href] });
        sandbox.onmessage = event => worker.onmessage?.(event);
        sandbox.onerror = event => worker.onerror?.(event);
        for (const data of worker.queue.splice(0)) sandbox.postMessage(data);
      }).catch(() => worker.onerror?.({ message: 'Python sandbox failed to load. Check your connection and retry.', preventDefault() {} }));
      return worker;
    };
  }
};
if (typeof module !== 'undefined') module.exports = ManimSandbox; else globalThis.ManimSandbox = ManimSandbox;
})();
