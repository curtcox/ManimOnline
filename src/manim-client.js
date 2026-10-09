/** One in-flight render, with termination for edits, cancellation, and timeout. */
class ManimClient {
  constructor({ workerFactory = () => new Worker('src/unified-worker.js'), timeout = 90000, onStatus = () => {} } = {}) {
    this.workerFactory = workerFactory;
    this.timeout = timeout;
    this.onStatus = onStatus;
    this.nextId = 0;
  }

  cancel(message = 'Render cancelled') {
    if (this.worker) this.worker.terminate();
    this.worker = null;
    if (this.pending) {
      clearTimeout(this.pending.timer);
      const error = new Error(message);
      error.name = 'AbortError';
      this.pending.reject(error);
      this.pending = null;
    }
  }

  render(code, options = {}) {
    if (this.pending) this.cancel();
    if (!this.worker) {
      const worker = this.workerFactory();
      this.worker = worker;
      worker.onmessage = event => {
        if (this.worker !== worker) return;
        const data = event.data;
        if (data.type === 'pyodide-loading') this.onStatus('Loading Python…');
        if (!this.pending || data.id !== this.pending.id) return;
        if (data.type === 'numpy-loading') { this.onStatus('Loading NumPy…'); return; }
        if (data.type === 'pyodide-ready') { this.onStatus('Rendering animation…'); return; }
        if (data.type !== 'error' && data.type !== 'manim-result') return;
        const pending = this.pending;
        clearTimeout(pending.timer);
        this.pending = null;
        if (data.type === 'error') pending.reject(new Error(data.error));
        else pending.resolve(data.sceneData);
      };
      worker.onerror = event => {
        event.preventDefault();
        if (this.worker !== worker) return;
        const pending = this.pending;
        this.pending = null;
        this.worker.terminate();
        this.worker = null;
        if (pending) {
          clearTimeout(pending.timer);
          pending.reject(new Error(event.message || 'Python worker failed to load. Check your connection and retry.'));
        }
      };
    }
    return new Promise((resolve, reject) => {
      const id = ++this.nextId;
      const timer = setTimeout(() => {
        this.worker.terminate();
        this.worker = null;
        this.pending = null;
        reject(new Error(`Render timed out after ${this.timeout / 1000} seconds. Shorten the scene and try again.`));
      }, this.timeout);
      this.pending = { id, resolve, reject, timer };
      this.worker.postMessage({ id, type: 'render-manim', code, options });
    });
  }
}
if (typeof module !== 'undefined' && module.exports) module.exports = ManimClient;
else window.ManimClient = ManimClient;
