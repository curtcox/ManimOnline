/** Links capture one editor version; shortening is optional and bounded. */
const ShareLinks = {
  build({ url, code, mode = 'auto', type, scene = '', engine = 'dot', format = 'svg', compress }) {
    const link = new URL(url);
    for (const parameter of ['raw', 'compressed', 'url', 'type', 'scene', 'engine', 'format']) link.searchParams.delete(parameter);
    if (mode !== 'auto') link.searchParams.set('type', mode === 'graphviz' ? 'dot' : 'manim');
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

class ShareClient {
  constructor({ fetchLink = (url, options) => fetch(url, options), timeout = 10000, timers = globalThis } = {}) {
    this.fetchLink = fetchLink;
    this.timeout = timeout;
    this.timers = timers;
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
      timer = this.timers.setTimeout(() => { controller.abort(); reject(new Error('Timed out')); }, this.timeout);
    });
    const request = (async () => {
      const endpoint = 'https://is.gd/create.php?' + new URLSearchParams({ format: 'simple', url: links.long });
      const response = await this.fetchLink('https://api.allorigins.win/get?url=' + encodeURIComponent(endpoint), { signal: controller.signal });
      if (!response.ok) throw new Error('Could not shorten link');
      const result = await response.json();
      if (typeof result.contents !== 'string' || result.contents.length > 256) throw new Error('Invalid short link');
      const url = new URL(result.contents.trim());
      if (url.protocol !== 'https:' || url.hostname !== 'is.gd' || url.port || url.username || url.password ||
          url.search || url.hash || !/^\/[A-Za-z0-9_-]+$/.test(url.pathname)) throw new Error('Invalid short link');
      return url.href;
    })();
    try {
      const url = await Promise.race([request, cancellation]);
      return revision === this.revision ? { url, shortened: true } : null;
    } catch (_) {
      return revision === this.revision ? { url: links.fallback, shortened: false } : null;
    } finally {
      this.timers.clearTimeout(timer);
      if (revision === this.revision) this.pending = null;
    }
  }
}
if (typeof module !== 'undefined') module.exports = { ShareLinks, ShareClient };
else Object.assign(globalThis, { ShareLinks, ShareClient });
