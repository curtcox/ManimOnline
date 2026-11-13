import { openaiDriver } from '../drivers/openai.js';
import { openrouterDriver } from '../drivers/openrouter.js';
import { anthropicDriver } from '../drivers/anthropic.js';
import { compatibleDriver } from '../drivers/openai-compatible.js';
import { decisionDriver } from '../drivers/decisions.js';
import { string } from '../data.js';
export function directConnection({ config, fetchSource = globalThis.fetch }) {
  const credentials = new Map(), controllers = new Set();
  const options = { fetchSource, title: config.name };
  const drivers = { openai: openaiDriver(options), openrouter: openrouterDriver(options), anthropic: anthropicDriver(options), gemini: compatibleDriver({ ...options, provider: 'gemini', baseURL: 'https://generativelanguage.googleapis.com/v1beta/openai/' }) };
  return {
    connect(route, key) { if (!['openai', 'openrouter', 'anthropic', 'gemini'].includes(route)) throw new Error('This route does not accept a key.'); string(key, 'API key', 8192); if (/\s/.test(key)) throw new Error('Invalid API key.'); credentials.set(route, key); },
    disconnect(route) { if (route) credentials.delete(route); else credentials.clear(); for (const controller of controllers) controller.abort(); },
    async call(kind, request, model) {
      const route = model.ref.split(':')[0], key = credentials.get(route);
      if (route !== 'local' && !key) throw new Error(`Connect ${route} before sending, or choose paste handoff.`);
      const controller = new AbortController(); controllers.add(controller);
      const signal = request.signal ? AbortSignal.any([request.signal, controller.signal]) : controller.signal;
      try {
        const driver = route === 'local' ? compatibleDriver({ ...options, provider: 'local', baseURL: model.baseURL }) : drivers[route];
        if (!driver) throw new Error('This route is unavailable. Choose another model.');
        return kind === 'decide' ? await decisionDriver({ ...options, route, baseURL: model.baseURL }).decide({ ...request, signal }, key, model) : await driver.generate({ ...request, signal }, key, model);
      } finally { controllers.delete(controller); }
    },
  };
}
