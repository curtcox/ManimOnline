/** Links capture one editor version; shortening is optional and bounded. */
const ShareLinks = {
  build({ url, code, mode = 'auto', type, scene = '', engine = 'dot', format = 'svg', positions = {}, compress }) {
    const link = new URL(url);
    for (const parameter of ['example', 'raw', 'compressed', 'url', 'type', 'scene', 'engine', 'format', 'modlpos']) link.searchParams.delete(parameter);
    if (mode !== 'auto') link.searchParams.set('type', mode === 'graphviz' ? 'dot' : mode);
    if (type === 'modl' && Object.keys(positions).length) link.searchParams.set('modlpos', JSON.stringify(positions));
    if (type === 'manim' && scene.trim()) link.searchParams.set('scene', scene.trim());
    if (type === 'graphviz') {
      link.searchParams.set('engine', engine);
      link.searchParams.set('format', format);
    }
    link.hash = encodeURIComponent(code);
    const long = link.href;
    try {
      const compressed = compress?.(code);
      if (typeof compressed === 'string' && compressed) {
        link.hash = '';
        link.searchParams.set('compressed', compressed);
      }
    } catch (_) { /* Uncompressed links still work if compression is unavailable. */ }
    return Object.freeze({ long, fallback: link.href });
  }
};

class ShareError extends Error {
  constructor(code, message) { super(message); this.code = code; }
}

class ShareClient {
  constructor({ fetchLink = (url, options) => fetch(url, options), timeout = 10000, timers = globalThis,
    isOnline = () => globalThis.navigator?.onLine !== false } = {}) {
    this.fetchLink = fetchLink;
    this.timeout = timeout;
    this.timers = timers;
    this.isOnline = isOnline;
    this.revision = 0;
  }
  cancel() {
    this.revision++;
    this.pending?.cancel();
    this.pending = null;
  }
  async shorten(links) {
    this.cancel();
    const revision = this.revision;
    const controller = new AbortController();
    let timer;
    const cancellation = new Promise((_, reject) => {
      this.pending = { cancel: () => { controller.abort(); reject(new Error('Cancelled')); } };
      timer = this.timers.setTimeout(() => {
        reject(new ShareError('timeout', `Link shortening did not respond within ${this.timeout / 1000} seconds. Retry later, or choose Save to HashBin for a shorter saved-source link.`));
        controller.abort();
      }, this.timeout);
    });
    const request = (async () => {
      if (!this.isOnline()) throw new ShareError('offline', 'You are offline. Reconnect and try Shorten link again.');
      const endpoint = 'https://is.gd/create.php?' + new URLSearchParams({ format: 'simple', url: links.long });
      let response;
      try {
        response = await this.fetchLink('https://api.allorigins.win/get?url=' + encodeURIComponent(endpoint), { signal: controller.signal });
      } catch (_) {
        const online = this.isOnline();
        throw new ShareError(online ? 'network' : 'offline', online
          ? 'Could not reach AllOrigins, the proxy used to contact is.gd. Your browser did not provide a response, so a service outage, connection problem, or browser restriction may be responsible. Check your connection and content blockers, then retry later or choose Save to HashBin.'
          : 'You are offline. Reconnect and try Shorten link again.');
      }
      if (!response.ok) throw this.httpError('AllOrigins (shortening proxy)', response.status);
      let result;
      try { result = await response.json(); }
      catch (_) { throw new ShareError('response', 'AllOrigins returned an unreadable response. Retry later, or choose Save to HashBin.'); }
      const upstreamStatus = Number(result?.status?.http_code);
      if (Number.isInteger(upstreamStatus) && upstreamStatus >= 400 &&
          !(typeof result?.contents === 'string' && /^\s*Error\b/i.test(result.contents))) {
        throw this.httpError('is.gd (shortening service)', upstreamStatus);
      }
      if (typeof result?.contents !== 'string' || !result.contents.trim() ||
          (result.contents.length > 256 && !/^\s*Error\b/i.test(result.contents))) {
        throw new ShareError('response', 'AllOrigins returned an incomplete or unexpected response instead of a short link. Retry later, or choose Save to HashBin.');
      }
      const contents = result.contents.trim();
      if (/^Error\b/i.test(contents)) {
        const detail = contents.replace(/^Error\b[\s:,]*/i, '').replace(/[\x00-\x1f\x7f]/g, ' ').slice(0, 256);
        const status = Number(result.status?.http_code);
        const guidance = /\brate[\s-]+limits?\b|\btoo many\b|\blimit exceeded\b/i.test(detail) || status === 502
          ? 'Wait at least one minute before retrying, or choose Save to HashBin.'
          : /too long|maximum.*length|length.*exceed/i.test(detail)
            ? 'Choose Save to HashBin to share this source without sending a long URL to is.gd.'
            : /database|insert failed|maintenance|internal.*error/i.test(detail)
              ? 'This is a problem with the shortening service. Retry later, or choose Save to HashBin.'
            : status === 400 || status === 406
              ? 'Copy the source link to check it, or choose Save to HashBin instead.'
              : 'Retry later, or choose Save to HashBin.';
        const reason = detail || 'unspecified service error';
        throw new ShareError('provider', `is.gd could not shorten the link: ${reason}${/[.!?]$/.test(reason) ? '' : '.'} ${guidance}`);
      }
      let url;
      try { url = new URL(contents); } catch (_) { /* Rejected below. */ }
      if (!url) throw new ShareError('response', 'is.gd returned an invalid short link. Retry later, or choose Save to HashBin.');
      if (url.protocol !== 'https:' || url.hostname !== 'is.gd' || url.port || url.username || url.password ||
          url.search || url.hash || !/^\/[A-Za-z0-9_-]+$/.test(url.pathname)) {
        throw new ShareError('response', 'is.gd returned an unexpected short-link address. It was rejected. Retry later, or choose Save to HashBin.');
      }
      return url.href;
    })();
    try {
      const url = await Promise.race([request, cancellation]);
      return revision === this.revision ? { url, shortened: true } : null;
    } catch (error) {
      return revision === this.revision ? { url: links.fallback, shortened: false,
        error: { code: error.code || 'unknown', message: (error instanceof ShareError ? error.message
          : 'Link shortening failed unexpectedly. Retry later, or choose Save to HashBin.') + ' The source link above is still ready to copy.' } } : null;
    } finally {
      this.timers.clearTimeout(timer);
      if (revision === this.revision) this.pending = null;
    }
  }
  httpError(service, status) {
    const code = Number.isInteger(status) ? `HTTP ${status}` : 'an HTTP error';
    const guidance = status === 429
      ? 'Wait at least one minute before retrying, or choose Save to HashBin.'
      : status === 413 || status === 414
        ? 'The source URL is too large for this request. Choose Save to HashBin to share it instead.'
        : status === 401 || status === 403
          ? 'The service refused this request. Choose Save to HashBin or copy the source link.'
          : 'Retry later, or choose Save to HashBin.';
    return new ShareError('http', `${service} returned ${code}. ${guidance}`);
  }
}
if (typeof module !== 'undefined') module.exports = { ShareLinks, ShareClient };
else Object.assign(globalThis, { ShareLinks, ShareClient });
