#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { args, walk, sha256, inside } from './lib.mjs';
import { endpoint, keys, string } from '../src/ai/data.js';
import { modelEntry } from '../src/ai/models.js';
export async function stageAiHost({ config, output }) {
  keys(config, ['name', 'storagePrefix', 'allowedOrigins', 'routes', 'models'], 'host config');
  string(config.name, 'host name'); if (!/^[\w.-]+$/.test(config.storagePrefix)) throw new Error('Host needs a storage prefix.');
  if (!Array.isArray(config.allowedOrigins) || !config.allowedOrigins.length || config.allowedOrigins.length > 100) throw new Error('Host needs exact allowed origins.');
  for (const value of config.allowedOrigins) {
    const url = endpoint(value);
    if (url.origin !== value || value.includes('*') || /(^|\.)(github\.io|hashbin\.app)$/.test(url.hostname) || /preview/i.test(url.hostname)) throw new Error('Host allowlist must use exact dedicated app origins, never shared, preview or run origins.');
  }
  if (!Array.isArray(config.routes) || config.routes.some(r => !['openai', 'openrouter', 'anthropic', 'gemini', 'local', 'browser', 'paste'].includes(r))) throw new Error('Invalid host routes.');
  if (!Array.isArray(config.models)) throw new Error('Host models required.'); config.models.forEach(modelEntry);
  const root = fileURLToPath(new URL('../', import.meta.url)), destination = path.resolve(output);
  if (destination === root || root.startsWith(destination + path.sep) || ['src', 'vendor', 'demo'].some(d => destination.startsWith(path.join(root, d)))) throw new Error('Use a separate staging directory.');
  await fs.mkdir(destination, { recursive: false });
  for (const folder of ['src', 'vendor']) await fs.cp(path.join(root, folder), path.join(destination, folder), { recursive: true });
  let html = await fs.readFile(path.join(root, 'src/ai/host/host.html'), 'utf8');
  html = html.replace('src="host.js"', 'src="src/ai/host/host.js"').replace('href="../../ui/kit.css"', 'href="src/ui/kit.css"').replace('href="../ui/ai.css"', 'href="src/ai/ui/ai.css"');
  await fs.writeFile(path.join(destination, 'host.html'), html);
  await fs.writeFile(path.join(destination, 'ai-host.config.json'), JSON.stringify(config, null, 2) + '\n');
  const csp = `default-src 'self'; script-src 'self' blob: 'wasm-unsafe-eval'; style-src 'self'; connect-src 'self' blob: https: http://localhost:* http://127.0.0.1:*; worker-src 'self' blob:; img-src 'self' data:; object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors ${config.allowedOrigins.join(' ')}`;
  await fs.writeFile(path.join(destination, '_headers'), `/*\n  Content-Security-Policy: ${csp}\n  Referrer-Policy: no-referrer\n  X-Content-Type-Options: nosniff\n`);
  const hashes = {};
  for (const file of await walk(destination)) hashes[file] = sha256(await fs.readFile(inside(destination, file)));
  await fs.writeFile(path.join(destination, 'ai-host-manifest.json'), JSON.stringify({ protocol: 1, version: sha256(JSON.stringify(hashes)).slice(0, 24), files: hashes }, null, 2) + '\n');
  return destination;
}
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const opts = args(); stageAiHost({ config: JSON.parse(await fs.readFile(opts.config, 'utf8')), output: opts.output }).then(console.log).catch(e => { console.error(e.message); process.exitCode = 1; });
}
