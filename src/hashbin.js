/** Shared HashBin persistence. Payloads remain readable by the modl-only editor. */
const HashBinDocuments = {
  MAX_BYTES: 5 * 1024 * 1024,
  bytes(value) { return new TextEncoder().encode(value); },
  decode64(value) { return Uint8Array.from(atob(value.replace(/-/g, '+').replace(/_/g, '/')), c => c.charCodeAt(0)); },
  cidLength(cid) { return this.decode64(cid.slice(0, 8)).reduce((n, b) => n * 256 + b, 0); },
  isCID(value) {
    if (typeof value !== 'string' || !/^[A-Za-z0-9_-]{8,94}$/.test(value)) return false;
    const length = this.cidLength(value);
    if (value.length !== 8 + (length <= 64 ? Math.ceil(length * 4 / 3) : 86)) return false;
    // Reject noncanonical base64 trailing bits, so ordinary source hashes stay source.
    const rest = this.decode64(value.slice(8));
    const encoded = btoa(String.fromCharCode(...rest)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
    return encoded === value.slice(8);
  },
  cid(input) {
    const text = input.trim().replace(/^#/, '');
    if (this.isCID(text)) return text;
    try {
      const url = new URL(text);
      if (url.protocol !== 'https:' || !['hashbin.org', '256t.us', 'curtcox.github.io'].includes(url.hostname)) return null;
      const candidate = url.hash.slice(1) || url.pathname.split('/').pop();
      return this.isCID(candidate) ? candidate : null;
    } catch (_) { return null; }
  },
  positions(input) {
    const result = Object.create(null);
    if (!input || typeof input !== 'object') return result;
    for (const id of Object.keys(input).sort()) {
      const p = input[id];
      if (Array.isArray(p) && p.length === 2 && p.every(Number.isFinite)) result[id] = p.slice();
    }
    return result;
  },
  serialize({ src, type, scene = '', engine = 'dot', outputFormat = 'svg', pos = {} }) {
    if (typeof src !== 'string' || !['graphviz', 'modl', 'manim'].includes(type)) throw new Error('Choose a language before saving.');
    const doc = { format: 'hashbin-diagram', version: 1, src, type };
    if (type === 'modl') doc.pos = this.positions(pos);
    if (type === 'manim') doc.scene = scene.trim();
    if (type === 'graphviz') doc.graphviz = { engine, format: outputFormat };
    const payload = JSON.stringify(doc);
    if (this.bytes(payload).length > this.MAX_BYTES) throw new Error('Source exceeds the 5 MiB HashBin limit.');
    return payload;
  },
  parse(text) {
    if (this.bytes(text).length > this.MAX_BYTES) throw new Error('Saved source exceeds the 5 MiB limit.');
    let doc;
    try { doc = JSON.parse(text); } catch (_) { /* Plain source is also supported. */ }
    if (!doc || typeof doc.src !== 'string') return { src: text, type: null, pos: this.positions({}), scene: '' };
    if (doc.version != null && doc.version !== 1) throw new Error('Unsupported saved document version.');
    const type = ['graphviz', 'modl', 'manim'].includes(doc.type) ? doc.type : doc.format === 'hashbin-diagram' ? 'modl' : null;
    return { src: doc.src, type, pos: this.positions(doc.pos), scene: typeof doc.scene === 'string' ? doc.scene : '',
      engine: typeof doc.graphviz?.engine === 'string' ? doc.graphviz.engine : 'dot',
      outputFormat: typeof doc.graphviz?.format === 'string' ? doc.graphviz.format : 'svg' };
  },
  link(url, cid) {
    if (!this.isCID(cid)) throw new Error('HashBin returned an invalid CID.');
    const link = new URL(url);
    for (const key of ['example', 'raw', 'compressed', 'url', 'modlpos', 'code', 'state', 'error', 'error_description']) link.searchParams.delete(key);
    link.hash = cid;
    return link.href;
  }
};

class HashBinStore {
  constructor({ clientId, redirectUri, storage, transactionStorage, fetchSource = (...args) => fetch(...args),
    loadSDK = () => import('https://hashbin.org/sdk/hashbin.js'), timeout = 20000, timers = globalThis } = {}) {
    Object.assign(this, { clientId, redirectUri, storage, transactionStorage, fetchSource, loadSDK, timeout, timers });
  }
  async bounded(work) {
    const controller = new AbortController();
    let timer;
    try {
      return await Promise.race([Promise.resolve().then(() => work(controller.signal)), new Promise((_, reject) => {
        timer = this.timers.setTimeout(() => { controller.abort(); reject(new Error('HashBin request timed out. Try again.')); }, this.timeout);
      })]);
    } finally { this.timers.clearTimeout(timer); }
  }
  async load(cid) {
    if (!HashBinDocuments.isCID(cid)) throw new Error('Enter a valid HashBin CID or saved link.');
    if (HashBinDocuments.cidLength(cid) > HashBinDocuments.MAX_BYTES) throw new Error('Saved source exceeds the 5 MiB limit.');
    return this.bounded(async signal => {
      if (HashBinDocuments.cidLength(cid) <= 64) return HashBinDocuments.parse(new TextDecoder('utf-8', { fatal: true }).decode(HashBinDocuments.decode64(cid.slice(8))));
      const response = await this.fetchSource(`https://256t.us/${cid}`, { signal });
      if (!response.ok) throw new Error(response.status === 404 ? 'Saved source was not found. It may have expired or been deleted.' : `HashBin load failed (HTTP ${response.status}).`);
      return HashBinDocuments.parse(await response.text());
    });
  }
  async init() {
    if (this.oauth) return this.oauth;
    if (!this.clientId) throw new Error('HashBin sign-in needs a registered client ID.');
    if (!this.initializing) this.initializing = this.bounded(async () => {
      const { HashBinClient } = await this.loadSDK();
      this.oauth = new HashBinClient({ clientId: this.clientId, redirectUri: this.redirectUri,
        baseUrl: 'https://hashbin.org', contentBaseUrl: 'https://256t.us', storage: this.storage, transactionStorage: this.transactionStorage,
        fetch: this.fetchSource });
      return this.oauth;
    }).finally(() => { this.initializing = null; });
    return this.initializing;
  }
  async connected() { return Boolean((await this.init()).getTokens()?.refreshToken); }
  async connect(snapshot) {
    if (!this.transactionStorage) throw new Error('Enable session storage to preserve your source during sign-in.');
    const oauth = await this.init();
    const request = await this.bounded(() => oauth.authorize({ scopes: ['content:write', 'balance:read'], mode: 'manual' }));
    this.transactionStorage.setItem('manimonline:hashbin:return:' + request.state, JSON.stringify({ snapshot, createdAt: Date.now() }));
    return request.url;
  }
  async callback(search) {
    const params = new URLSearchParams(search);
    const state = params.get('state');
    if (!state || (!params.has('code') && !params.has('error'))) return null;
    const key = 'manimonline:hashbin:return:' + state;
    let saved;
    try { saved = JSON.parse(this.transactionStorage?.getItem(key) || 'null'); } catch (_) { /* Invalid transaction. */ }
    this.transactionStorage?.removeItem(key);
    if (!saved || Date.now() - saved.createdAt > 30 * 60 * 1000) return { error: 'HashBin sign-in could not be restored in this tab. Connect again.' };
    try {
      if (params.has('error')) throw new Error(params.get('error') === 'access_denied' ? 'HashBin access was not approved.' : 'HashBin sign-in failed.');
      const oauth = await this.init();
      await this.bounded(() => oauth.handleCallback({ search }));
      return { snapshot: saved.snapshot, connected: true };
    } catch (error) { return { snapshot: saved.snapshot, error: error.message }; }
  }
  async authed(path, options = {}) {
    const oauth = await this.init();
    options.signal?.throwIfAborted();
    if (!oauth.getTokens()?.refreshToken) throw new Error('Connect to HashBin before saving.');
    if ((oauth.getTokens().expiresAt || 0) <= Date.now() + 30000) await oauth.refreshAccessToken();
    options.signal?.throwIfAborted();
    let response = await oauth.authorizedFetch(path, options);
    if (response.status === 401) {
      await oauth.refreshAccessToken();
      options.signal?.throwIfAborted();
      response = await oauth.authorizedFetch(path, options);
    }
    if (response.status === 401) { oauth.clearTokens(); throw new Error('HashBin sign-in expired. Connect again.'); }
    return response;
  }
  async json(response) {
    const data = await response.json();
    if (!response.ok) throw new Error(data.message || data.error || `HashBin request failed (HTTP ${response.status}).`);
    return data;
  }
  async quote(payload) {
    return this.bounded(async signal => {
      // Sequential authenticated calls also work with older SDKs using single-use refresh tokens.
      const settings = await this.json(await this.authed('/api/account/settings', { signal }));
      const balance = await this.json(await this.authed('/api/balance', { signal }));
      const months = Number(settings.default_retention_months || 1);
      const size = HashBinDocuments.bytes(payload).length;
      const quote = size <= 64 ? { cost_cents: 0 } : await this.json(await this.fetchSource('https://hashbin.org/api/payments/calculate', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, signal,
        body: JSON.stringify({ size_bytes: size, retention_months: months })
      }));
      if (!Number.isFinite(months) || months <= 0 || !Number.isFinite(quote.cost_cents) || quote.cost_cents < 0 || !Number.isFinite(balance.balance_cents)) throw new Error('HashBin returned an invalid price quote.');
      return { months, cost: quote.cost_cents, balance: balance.balance_cents, size };
    });
  }
  async save(payload) {
    return this.bounded(async signal => {
      const body = new FormData();
      body.append('content', new Blob([payload], { type: 'application/json' }), 'diagram.json');
      const data = await this.json(await this.authed('/api/content', { method: 'POST', body, signal }));
      if (!HashBinDocuments.isCID(data.cid)) throw new Error('HashBin returned an invalid CID.');
      return data;
    });
  }
}
if (typeof module !== 'undefined') module.exports = { HashBinDocuments, HashBinStore };
else Object.assign(globalThis, { HashBinDocuments, HashBinStore });
