import { MAX_BYTES } from './bytes.js';

export function safeURL(value, base) {
  const url = new URL(value, base);
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password) throw new Error('Expected an HTTP(S) URL.');
  return url;
}
export function createConfig(input, { document = globalThis.document } = {}) {
  if (!input) input = JSON.parse(document?.getElementById('fragment-kit-config')?.textContent || '{}');
  for (const key of ['slug', 'name', 'storagePrefix', 'canonicalOrigin', 'recoveryOrigin', 'repo', 'docs', 'gallery', 'documentType']) {
    if (typeof input[key] !== 'string' || !input[key].trim()) throw new Error(`Missing app config: ${key}.`);
  }
  if (!/^[a-z0-9][a-z0-9-]*$/.test(input.slug) || !/^[\w.-]+:?$/.test(input.storagePrefix)) throw new Error('Invalid app slug or storage prefix.');
  if (!/^[\w.-]+\/[\w.-]+$/.test(input.repo)) throw new Error('Invalid GitHub repository.');
  const canonicalOrigin = safeURL(input.canonicalOrigin).href;
  const recoveryOrigin = safeURL(input.recoveryOrigin).href;
  for (const href of [canonicalOrigin, recoveryOrigin]) {
    const url = new URL(href);
    if (url.search || url.hash || !url.pathname.endsWith('/')) throw new Error('App origins must end with / and have no query or fragment.');
  }
  const maxBytes = input.maxBytes ?? MAX_BYTES;
  if (!Number.isSafeInteger(maxBytes) || maxBytes < 1) throw new Error('Invalid maxBytes.');
  return Object.freeze({ ...input, ai: validateAiConfig(input.ai), canonicalOrigin, recoveryOrigin, maxBytes,
    hashbinClientId: input.hashbinClientId ?? document?.querySelector('meta[name="hashbin-client-id"]')?.content ?? '',
    docs: safeURL(input.docs, canonicalOrigin).href, gallery: safeURL(input.gallery, canonicalOrigin).href,
    storagePrefix: input.storagePrefix.replace(/:$/, ''),
    allowedHosts: Object.freeze([...new Set(['hashbin.org', '256t.us', new URL(canonicalOrigin).hostname, new URL(recoveryOrigin).hostname])]) });
}
export function redirectUri(config, href = globalThis.location?.href ?? config.recoveryOrigin) {
  const here = new URL(href), canonical = new URL(config.canonicalOrigin);
  return here.origin === canonical.origin && here.pathname.startsWith(canonical.pathname) ? config.canonicalOrigin : config.recoveryOrigin;
}
export function isAppURL(input, config) {
  let url;
  try { url = safeURL(input); } catch { return false; }
  return [config.canonicalOrigin, config.recoveryOrigin].some(base => {
    const expected = new URL(base);
    return url.origin === expected.origin && [expected.pathname, expected.pathname + 'index.html'].includes(url.pathname);
  });
}

/** Validate AI configuration without loading the opt-in AI entry point. */
export function validateAiConfig(ai) {
  if (ai === undefined) return undefined;
  const plain = value => value && typeof value === 'object' && !Array.isArray(value);
  const only = (value, allowed) => {
    if (!plain(value) || Object.keys(value).some(k => !allowed.includes(k))) throw new Error('Invalid AI configuration field.');
  };
  const endpoint = value => {
    if (typeof value !== 'string') throw new Error('Missing AI endpoint.');
    const url = safeURL(value);
    if (url.search || url.hash || !url.pathname.endsWith('/') || (url.protocol !== 'https:' && !['localhost', '127.0.0.1', '[::1]'].includes(url.hostname))) throw new Error('Invalid AI deployment URL.');
    return url;
  };
  only(ai, ['deployments', 'routes', 'defaults', 'models', 'layout', 'maxBytes', 'budget']);
  if (!plain(ai.deployments)) throw new Error('AI deployments are required.');
  for (const [base, deployment] of Object.entries(ai.deployments)) {
    endpoint(base); only(deployment, ['connection', 'host', 'url']);
    if (!['direct', 'host', 'gateway'].includes(deployment.connection)) throw new Error('Invalid AI connection.');
    if (deployment.connection === 'host') {
      const host = endpoint(deployment.host);
      if (host.origin === new URL(base).origin) throw new Error('AI host needs a separate origin.');
    } else if (deployment.host !== undefined) throw new Error('Unexpected AI host.');
    if (deployment.connection === 'gateway') endpoint(deployment.url);
    else if (deployment.url !== undefined) throw new Error('Unexpected AI gateway.');
  }
  if (!Array.isArray(ai.routes) || !ai.routes.length || new Set(ai.routes).size !== ai.routes.length || ai.routes.some(r => !['openrouter', 'openai', 'anthropic', 'gemini', 'local', 'browser', 'paste'].includes(r))) throw new Error('Invalid AI routes.');
  if (ai.defaults !== undefined) {
    only(ai.defaults, ['generate', 'decide']);
    for (const value of Object.values(ai.defaults)) if (typeof value !== 'string' || !value.includes(':')) throw new Error('Invalid AI default model.');
  }
  if (ai.layout !== undefined && !['ask-first', 'tabs', 'dialog'].includes(ai.layout)) throw new Error('Invalid AI layout.');
  if (ai.maxBytes !== undefined && (!Number.isSafeInteger(ai.maxBytes) || ai.maxBytes < 1 || ai.maxBytes > MAX_BYTES)) throw new Error('Invalid AI maxBytes.');
  if (ai.models !== undefined && !Array.isArray(ai.models)) throw new Error('Invalid AI models.');
  if (ai.budget !== undefined) {
    only(ai.budget, ['total', 'day', 'month']);
    if (Object.values(ai.budget).some(n => !Number.isFinite(n) || n < 0)) throw new Error('Invalid AI budget.');
  }
  return Object.freeze(structuredClone(ai));
}
