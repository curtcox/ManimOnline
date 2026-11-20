import { HOST_PROTOCOL } from '../connections/host.js';
import { bounded, MAX_BYTES } from '../../core/bytes.js';
import { keys } from '../data.js';
/** Exact origins are rechecked independently of frame-ancestors headers. */
export function installAiHost({ allowedOrigins, createClient, window = globalThis.window, onConnection = () => {}, onModel = () => {}, authorizeDownload = () => false }) {
  const clients = new Set(); let connected = false;
  const receive = async event => {
    if (connected || event.source !== window.parent || event.source === window || !allowedOrigins.includes(event.origin) || event.data?.protocol !== HOST_PROTOCOL || event.data?.type !== 'connect' || event.ports.length !== 1) return;
    connected = true;
    const port = event.ports[0], ai = await createClient(event.origin), controllers = new Map(); clients.add({ ai, port });
    onConnection({ ai, origin: event.origin });
    port.onmessage = async message => {
      let id, controller;
      try {
        bounded(JSON.stringify(message.data), MAX_BYTES); const data = message.data;
        if (typeof data.id !== 'string' || data.id.length > 100) throw new Error('Invalid host request ID.'); id = data.id;
        if (data.type === 'abort') { controllers.get(id)?.abort(); return; }
        keys(data, ['type', 'id', 'method', 'payload'], 'host request');
        if (data.type !== 'request' || !['models', 'generate', 'decide', 'loadModel', 'downloadModel', 'removeModel'].includes(data.method) || controllers.has(id) || controllers.size >= 4) throw new Error('Invalid host request.');
        controller = new AbortController(); controllers.set(id, controller);
        const { stream, ...payload } = data.payload;
        let result;
        if (data.method === 'models') result = await ai.models();
        else if (data.method === 'loadModel') { result = await ai.loadModel(payload.value, { signal: controller.signal }); onModel({ ai, origin: event.origin, ...result }); }
        else if (data.method === 'downloadModel') { if (!authorizeDownload(event.origin, payload.cid)) throw new Error('Approve model download on the AI host first.'); result = await ai.downloadModel(payload.cid, { consent: true, signal: controller.signal }); }
        else if (data.method === 'removeModel') result = await ai.removeModel(payload.cid);
        else result = await ai[data.method]({ ...payload, signal: controller.signal, ...(stream ? { onText: text => port.postMessage({ id, type: 'text', text }) } : {}) });
        bounded(JSON.stringify(result), MAX_BYTES);
        if (!controller.signal.aborted) port.postMessage({ id, type: 'result', result });
      } catch { port.postMessage({ id, type: 'error' }); }
      finally { if (id && controller) controllers.delete(id); }
    };
    port.start(); port.postMessage({ protocol: HOST_PROTOCOL, type: 'ready' });
  };
  window.addEventListener('message', receive);
  if (window.parent !== window) window.parent.postMessage({ protocol: HOST_PROTOCOL, type: 'available' }, '*');
  return { destroy() { window.removeEventListener('message', receive); for (const { ai, port } of clients) { ai.destroy(); port.close(); } } };
}
