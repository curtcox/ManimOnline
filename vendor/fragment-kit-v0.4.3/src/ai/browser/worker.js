import { ENGINE_PINS } from './pins.js';
import { readResponse, text, bounded, MAX_BYTES } from '../../core/bytes.js';
const originalFetch = globalThis.fetch.bind(globalThis), NativeWorker = globalThis.Worker;
const noLog = Object.freeze({ debug() {}, log() {}, warn() {}, error() {} });
let engine, busy = false, activeId;
async function asset(file) {
  const url = new URL(`../../../vendor/wllama-3.8.1/${file}`, import.meta.url);
  const response = await originalFetch(url);
  if (!response.ok) throw new Error('Engine file unavailable.');
  const data = await readResponse(response, 32 * 1024 * 1024);
  const digest = [...new Uint8Array(await crypto.subtle.digest('SHA-256', data))].map(n => n.toString(16).padStart(2, '0')).join('');
  if (digest !== ENGINE_PINS[file]) throw new Error('Engine integrity mismatch.');
  return data;
}
function restrictNetwork(allowed) {
  const guard = `const networkFetch = globalThis.fetch.bind(globalThis); globalThis.fetch = (input, options) => { const url = typeof input === 'string' ? input : input.url ?? String(input); if (!${JSON.stringify(allowed)}.includes(url)) return Promise.reject(new Error('Engine network access denied.')); return networkFetch(input, options); }; globalThis.XMLHttpRequest = globalThis.WebSocket = globalThis.EventSource = undefined;`;
  globalThis.fetch = (input, options) => { const url = typeof input === 'string' ? input : input.url ?? String(input); if (!allowed.includes(url)) return Promise.reject(new Error('Engine network access denied.')); return originalFetch(input, options); };
  globalThis.XMLHttpRequest = globalThis.WebSocket = globalThis.EventSource = undefined;
  globalThis.Worker = class extends NativeWorker {
    constructor(url, options) {
      if (!String(url).startsWith('blob:')) throw new Error('Only pinned engine workers are allowed.');
      const wrapper = URL.createObjectURL(new Blob([guard, `\nconst queued = []; self.onmessage = event => queued.push(event); await import(${JSON.stringify(String(url))}); for (const event of queued) self.onmessage(event);`], { type: 'text/javascript' }));
      super(wrapper, { ...options, type: 'module' });
      this.addEventListener('error', () => self.postMessage({ id: activeId, error: 'Browser model worker failed. Try a smaller model or another browser.' }));
    }
  };
}
self.onmessage = async event => {
  const { id, method, files, manifest, request } = event.data;
  if (busy) { self.postMessage({ id, error: 'Browser model is busy.' }); return; } busy = true; activeId = id;
  try {
    if (method === 'load') {
      const [code, wasm, compatCode, compatWasm] = await Promise.all(['index.js', 'wllama.wasm', 'compat.js', 'compat.wasm'].map(asset));
      const wasmURL = URL.createObjectURL(new Blob([wasm], { type: 'application/wasm' })), compatURL = URL.createObjectURL(new Blob([compatWasm], { type: 'application/wasm' }));
      restrictNetwork([wasmURL, compatURL]);
      const { Wllama } = await import(URL.createObjectURL(new Blob([code], { type: 'text/javascript' })));
      engine = new Wllama({ default: wasmURL }, { logger: noLog, suppressNativeLog: true, cacheManager: {}, modelManager: {} });
      engine.setCompat({ worker: { code: text(compatCode) }, wasm: compatURL });
      await engine.loadModel(files, { n_threads: 1, n_ctx: Math.min(manifest.contextTokens, 8192), n_gpu_layers: globalThis.navigator.gpu ? 99 : 0, log_level: 4 });
      self.postMessage({ id, result: { engineVersion: 'wllama-3.8.1', loaded: true } });
    } else if (method === 'generate') {
      if (!engine) throw new Error('Model is not loaded.');
      const result = await engine.createChatCompletion({ messages: request.messages, max_tokens: request.maxTokens, temperature: 0, stream: false, ...(request.schema ? { response_format: { type: 'json_schema', json_schema: { name: 'response', schema: request.schema } } } : {}) });
      const output = bounded(result.choices?.[0]?.message?.content ?? '', MAX_BYTES);
      self.postMessage({ id, result: { text: output, usage: result.usage, finish: result.choices?.[0]?.finish_reason, model: request.model, cost: 0 } });
    } else throw new Error('Unknown engine operation.');
  } catch { self.postMessage({ id, error: 'Browser model failed to load or generate. Try a smaller model; this device may lack memory or required WASM/WebGPU support.' }); }
  finally { busy = false; }
};
