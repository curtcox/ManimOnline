import { parseManifest } from './manifest.js';
import { normalizeResult } from '../drivers/http.js';
import { abort } from '../data.js';
export function createBrowserEngine({ manifest: input, cid, weights, Worker = globalThis.Worker } = {}) {
  const manifest = parseManifest(input); let worker, loaded, rejectPending, busy = false, sequence = 0;
  function destroy() { const reject = rejectPending; rejectPending = null; worker?.terminate(); worker = loaded = null; reject?.(new Error('Browser model was closed.')); }
  function rpc(method, payload, signal) {
    abort(signal);
    return new Promise((resolve, reject) => {
      const id = ++sequence, currentWorker = worker;
      const timer = setTimeout(() => finish(new Error('Browser model timed out. Try a smaller model.')), 120000);
      const stop = () => finish(signal.reason);
      const receive = event => { if (event.data.id === id) finish(event.data.error ? new Error(event.data.error) : null, event.data.result); };
      const fail = () => finish(new Error('Browser model worker failed. Try a smaller model.'));
      function finish(error, value) {
        rejectPending = null; clearTimeout(timer); signal?.removeEventListener('abort', stop); currentWorker.removeEventListener('message', receive); currentWorker.removeEventListener('error', fail);
        if (error) { destroy(); reject(error); } else resolve(value);
      }
      rejectPending = error => finish(error);
      worker.addEventListener('message', receive); worker.addEventListener('error', fail); signal?.addEventListener('abort', stop, { once: true }); worker.postMessage({ id, method, ...payload });
    });
  }
  return { destroy,
    async generate(request) {
      if (busy) throw new Error('Browser model is busy. Wait or cancel before trying again.'); busy = true;
      const started = performance.now();
      try {
        if (manifest.requires.webgpu && !globalThis.navigator?.gpu) throw new Error('Browser model requires WebGPU on a compatible device.');
        if (!loaded) {
          const files = await weights.files(manifest); abort(request.signal);
          worker = new Worker(new URL('./worker.js', import.meta.url), { type: 'module', name: 'fragment-kit-ai-engine' });
          loaded = rpc('load', { files, manifest }, request.signal); await loaded;
        }
        const raw = await rpc('generate', { request: { messages: request.messages, maxTokens: request.maxTokens, schema: request.schema, model: `256t:${cid}` } }, request.signal);
        request.onText?.(raw.text);
        return normalizeResult(raw, { model: `256t:${cid}`, provider: 'browser', started, prices: { input: 0, output: 0 } });
      } finally { busy = false; }
    },
  };
}
