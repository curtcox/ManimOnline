#!/usr/bin/env node
import http from 'node:http';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { args } from './lib.mjs';
export async function serve({ root = process.cwd(), port = 8000, host = '127.0.0.1' } = {}) {
  root = await fs.realpath(root);
  const types = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.svg': 'image/svg+xml', '.png': 'image/png', '.webmanifest': 'application/manifest+json' };
  const server = http.createServer(async (request, response) => {
    try {
      const url = new URL(request.url, 'http://localhost');
      let name = decodeURIComponent(url.pathname);
      if (name.includes('\0') || name.split('/').some(part => part.startsWith('.'))) throw new Error('Invalid path.');
      let file = path.resolve(root, '.' + name);
      if (!file.startsWith(root + path.sep) && file !== root) throw new Error('Invalid path.');
      if ((await fs.stat(file)).isDirectory()) file = path.join(file, 'index.html');
      file = await fs.realpath(file);
      if (!file.startsWith(root + path.sep)) throw new Error('Invalid path.');
      const data = await fs.readFile(file);
      response.writeHead(200, { 'Content-Type': types[path.extname(file)] ?? 'application/octet-stream', 'Cache-Control': 'no-cache' }); response.end(data);
    } catch { response.writeHead(404); response.end('Not found'); }
  });
  await new Promise((resolve, reject) => { server.once('error', reject); server.listen(port, host, resolve); });
  return { server, url: `http://${host}:${server.address().port}/` };
}
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const options = args();
  const { url } = await serve({ root: options.root ?? process.cwd(), port: Number(options.port ?? 8000) });
  console.log(url);
}
