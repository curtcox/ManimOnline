import { bounded, MAX_BYTES } from '../../core/bytes.js';
import { endpoint, abort } from '../data.js';
import { createDialog } from '../../ui/dialog.js';
export const HOST_PROTOCOL = 'fragment-kit-ai-v1';
export function hostConnection({ deployment, document = globalThis.document, window = globalThis.window, timeout = 15000 }) {
  let availableListener;
  const host = endpoint(deployment.host); let frame, dialog, port, pending = new Map(), ready, sequence = 0;
  function destroy() { if (availableListener) window.removeEventListener('message', availableListener); availableListener = null; for (const entry of pending.values()) entry.reject(new Error('Host connection closed.')); pending.clear(); port?.close(); frame?.remove(); dialog?.destroy(); dialog = null; port = frame = ready = null; }
  async function init() {
    if (ready) return ready;
    ready = new Promise((resolve, reject) => {
      dialog = createDialog('AI host connection', { document, id: 'fk-ai-host-connection' });
      frame = document.createElement('iframe'); frame.src = new URL('host.html', host).href; frame.title = 'AI connection'; frame.hidden = true; frame.allow = 'webgpu; local-network-access';
      const timer = setTimeout(() => { destroy(); reject(new Error('Host is unreachable or blocked. Use paste handoff or reconnect.')); }, timeout);
      let started = false;
      availableListener = event => {
        if (started || event.source !== frame.contentWindow || event.origin !== host.origin || event.data?.protocol !== HOST_PROTOCOL || event.data?.type !== 'available') return;
        started = true; window.removeEventListener('message', availableListener);
        const channel = new MessageChannel(); port = channel.port1;
        port.onmessage = event => {
          try { bounded(JSON.stringify(event.data), MAX_BYTES); } catch { destroy(); reject(new Error('Host sent oversized data.')); return; }
          const data = event.data;
          if (data?.type === 'ready' && data.protocol === HOST_PROTOCOL) { clearTimeout(timer); resolve(); return; }
          const entry = pending.get(data?.id); if (!entry) return;
          if (data.type === 'text') { if (typeof data.text === 'string') entry.onText?.(data.text); }
          else { pending.delete(data.id); data.type === 'result' ? entry.resolve(data.result) : entry.reject(new Error('Host request failed. Open AI settings on the host to connect and approve this app.')); }
        };
        frame.contentWindow.postMessage({ protocol: HOST_PROTOCOL, type: 'connect' }, host.origin, [channel.port2]);
      };
      window.addEventListener('message', availableListener);
      dialog.body.append(frame);
    });
    return ready;
  }
  async function rpc(method, payload, { signal, onText } = {}) {
    abort(signal); await init(); abort(signal); const id = String(++sequence);
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => finish(new Error('Host request timed out.')), 120000);
      const stop = () => { port?.postMessage({ type: 'abort', id }); finish(signal.reason); };
      function finish(error, result) { clearTimeout(timer); signal?.removeEventListener('abort', stop); pending.delete(id); error ? reject(error) : resolve(result); }
      pending.set(id, { resolve: r => finish(null, r), reject: finish, onText }); signal?.addEventListener('abort', stop, { once: true });
      port.postMessage({ type: 'request', id, method, payload });
    });
  }
  return { async connect() { await init(); frame.hidden = false; frame.style.display = 'block'; frame.style.width = '100%'; frame.style.height = '300px'; dialog.open(); }, disconnect() { destroy(); }, destroy,
    models(options = {}) { return rpc('models', {}, options); },
    loadModel(value, options = {}) { return rpc('loadModel', { value }, options); },
    downloadModel(cid, options = {}) { return rpc('downloadModel', { cid }, options); },
    removeModel(cid) { return rpc('removeModel', { cid }); },
    call(kind, request, model) { const { signal, onText, ...data } = request; return rpc(kind, { ...data, model: model.ref, stream: Boolean(onText) }, { signal, onText }); },
  };
}
