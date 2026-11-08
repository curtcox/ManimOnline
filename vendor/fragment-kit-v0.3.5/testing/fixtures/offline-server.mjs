import http from 'node:http';
import fs from 'node:fs/promises';
import { sha256 } from '../../tools/lib.mjs';

/** A real mutable deployment fixture, with a private port per test. */
export async function offlineServer() {
  let revision = 1, bad = false;
  const worker = await fs.readFile(new URL('../../src/offline/sw-core.js', import.meta.url), 'utf8');
  const client = await fs.readFile(new URL('../../src/offline/client.js', import.meta.url), 'utf8');
  function assets() {
    return {
      'index.html': '<!doctype html><html><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src \'self\'; script-src \'self\'"><script type="module" src="probe.js"></script></head><body><p id="status">Installing</p></body></html>',
      'probe.js': `import { OfflineClient } from './client.js'; window.client = new OfflineClient({onStatus: value => { document.getElementById('status').textContent = value.ready ? 'Ready' : 'Incomplete'; }}); await window.client.init();`,
      'client.js': client, 'sw-core.js': worker, 'value.txt': 'version ' + revision,
    };
  }
  const server = http.createServer((request, response) => {
    const url = new URL(request.url, 'http://localhost'), name = url.pathname === '/' ? 'index.html' : url.pathname.slice(1);
    const files = assets(); let body = files[name];
    if (name === 'service-worker.js') body = `importScripts('offline-assets.js', 'sw-core.js'); // release ${revision}`;
    if (name === 'offline-assets.js') {
      const hashes = Object.fromEntries(Object.entries(files).map(([file, source]) => [file, sha256(source)]));
      body = 'self.OfflineAssets=' + JSON.stringify({ prefix: 'fk-offline-contract', version: 'fk-offline-contract-' + revision, assets: Object.keys(files), hashes });
    }
    if (bad && name === 'value.txt') body = 'wrong bytes';
    if (body === undefined) { response.writeHead(404); response.end(); return; }
    response.writeHead(200, { 'Content-Type': name.endsWith('.js') ? 'text/javascript' : name.endsWith('.html') ? 'text/html' : 'text/plain', 'Cache-Control': 'no-store' }); response.end(body);
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  return { url: `http://127.0.0.1:${server.address().port}/`, update() { revision++; }, corrupt(value) { bad = value; }, close: () => new Promise(resolve => { server.closeAllConnections(); server.close(resolve); }) };
}
