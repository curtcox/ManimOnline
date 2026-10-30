/* HashBin verified cache for service workers. Load with importScripts (a classic script).
   Cache Storage is shared by every app on an origin, so a service worker on a shared host must
   check bytes against pinned SHA-256 hashes before it stores or serves them. */
(() => {
  const TYPES = { html: 'text/html', js: 'text/javascript', mjs: 'text/javascript', css: 'text/css', json: 'application/json', svg: 'image/svg+xml', png: 'image/png', jpg: 'image/jpeg', webp: 'image/webp', mp4: 'video/mp4', webm: 'video/webm', wasm: 'application/wasm', zip: 'application/zip', whl: 'application/zip', webmanifest: 'application/manifest+json', txt: 'text/plain', md: 'text/markdown', py: 'text/plain' };
  const hex = buffer => [...new Uint8Array(buffer)].map(byte => byte.toString(16).padStart(2, '0')).join('');

  // Headers are rebuilt from the file extension rather than trusted from the cache entry.
  function contentType(url) {
    return TYPES[/\.([a-z0-9]+)$/.exec(new URL(url).pathname)?.[1]] || 'text/plain';
  }

  async function sha256(buffer) {
    return hex(await crypto.subtle.digest('SHA-256', buffer));
  }

  /** A fresh response holding the body only if it matches the expected hex SHA-256, otherwise null. */
  async function verify(response, expected, url) {
    if (!response?.ok || response.type === 'opaque' || !expected) return null;
    const body = await response.arrayBuffer();
    if (await sha256(body) !== expected) return null;
    return new Response(body, { status: 200, headers: { 'Content-Type': contentType(url || response.url) } });
  }

  /** Looks up a hash by absolute URL, or by the path relative to scope as manifests usually list it. */
  function lookup(hashes, scope) {
    return url => hashes[url] || (scope && url.startsWith(scope) ? hashes[url.slice(scope.length)] : undefined);
  }

  /** Package hashes from a Pyodide-style lockfile, keyed by absolute URL. Verify the lockfile itself first. */
  async function lockfileHashes(response, base) {
    const lock = await response.json();
    return new Map(Object.values(lock.packages || {}).filter(pkg => pkg.file_name && pkg.sha256).map(pkg => [new URL(pkg.file_name, base).href, pkg.sha256]));
  }

  /**
   * Verified cache operations over one cache.
   * hashFor(url) returns the expected hex SHA-256 (or a promise of it), or undefined for files not to cache.
   */
  function create({ cacheName, hashFor }) {
    const open = () => caches.open(cacheName);
    const expected = async url => hashFor(url);
    return {
      async verified(response, url) { return verify(response, await expected(url), url); },
      /** The cached copy only if it still matches; anything another app altered is ignored. */
      async match(url) { return verify(await (await open()).match(url), await expected(url), url); },
      /** Stores a verified copy and returns another for the caller, or null if the bytes do not match. */
      async put(url, response) {
        const checked = await verify(response, await expected(url), url);
        if (!checked) return null;
        await (await open()).put(url, checked.clone());
        return checked;
      },
      /** Downloads every URL and stores it; throws on the first mismatch. */
      async download(urls, init) {
        await Promise.all(urls.map(async url => {
          if (!await this.put(url, await fetch(new Request(url, init)))) throw new Error('Offline file did not match its pinned hash: ' + url);
        }));
      }
    };
  }

  const api = Object.freeze({ contentType, sha256, verify, lookup, lockfileHashes, create });
  globalThis.HashBinCache = api;
})();
