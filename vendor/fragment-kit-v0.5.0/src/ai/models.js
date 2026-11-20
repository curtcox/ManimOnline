import { isCID } from '../core/cid.js';
import { keys, string, number, endpoint, clone } from './data.js';
export const routeFor = ref => ref.startsWith('256t:') ? 'browser' : ref.split(':')[0];
export const ROUTES = ['openrouter', 'openai', 'anthropic', 'gemini', 'local', 'browser', 'paste'];
export const defaultModels = [
  { ref: 'paste:chat', capabilities: ['generate'], destination: 'Your chosen chat, when you paste', pinned: false, prices: { input: 0, output: 0 } },
];
export function modelEntry(input) {
  keys(input, ['ref', 'name', 'capabilities', 'destination', 'pinned', 'prices', 'contextTokens', 'baseURL', 'nativeDecisions'], 'model');
  const value = clone(input); string(value.ref, 'model ref', 2048);
  const [prefix, ...parts] = value.ref.split(':'); const route = routeFor(value.ref);
  if (!ROUTES.includes(route) || !parts.join(':').trim() || /[\s\x00-\x1f]/u.test(value.ref)) throw new Error('Invalid model ref.');
  if (route === 'browser' && (prefix !== '256t' || !isCID(parts.join(':')))) throw new Error('Browser model ref must name a manifest CID.');
  if (!Array.isArray(value.capabilities) || !value.capabilities.length || value.capabilities.some(c => !['generate', 'decide'].includes(c))) throw new Error('Invalid model capabilities.');
  string(value.destination, 'model destination');
  if (typeof value.pinned !== 'boolean') throw new Error('Model pin status is required.');
  if (value.prices != null) { keys(value.prices, ['input', 'output'], 'prices'); number(value.prices.input, 'input price'); number(value.prices.output, 'output price'); }
  if (value.contextTokens !== undefined) number(value.contextTokens, 'context tokens', { min: 1, integer: true });
  if (route === 'local') value.baseURL = endpoint(value.baseURL).href;
  else if (value.baseURL !== undefined) throw new Error('Only local models may override their endpoint.');
  if (value.nativeDecisions !== undefined && typeof value.nativeDecisions !== 'boolean') throw new Error('Invalid decision capability.');
  return Object.freeze(value);
}
export function deploymentFor(config, href) {
  if (!config.ai) return null;
  const here = new URL(href ?? config.canonicalOrigin);
  return Object.entries(config.ai.deployments).sort(([a], [b]) => b.length - a.length).find(([base]) => {
    const url = new URL(base); return here.origin === url.origin && here.pathname.startsWith(url.pathname);
  })?.[1] ?? { connection: 'paste' };
}
