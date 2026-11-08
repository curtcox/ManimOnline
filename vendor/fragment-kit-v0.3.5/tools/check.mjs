#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { args, inside, walk, readJSON } from './lib.mjs';
import { fileURLToPath } from 'node:url';
import { prepareJsQR } from './vendor-jsqr.mjs';
import { makeManifest } from './vendor-sync.mjs';

export async function check({ root = fileURLToPath(new URL('../', import.meta.url)), appConfig } = {}) {
  await prepareJsQR(true);
  if (!appConfig && await fs.stat(path.join(root, 'demo')).catch(() => null)) {
    const current = await makeManifest(root);
    const recorded = await readJSON(path.join(root, 'manifest.json'));
    const consumer = await readJSON(path.join(root, `demo/vendor/fragment-kit-v${current.version}/manifest.json`));
    if (JSON.stringify(current) !== JSON.stringify(recorded) || JSON.stringify(current) !== JSON.stringify(consumer)) throw new Error('Pinned demo or release manifest differs from source. Run npm run demo.');
  }
  const pins = await readJSON(path.join(root, 'vendor/integrity.json'));
  for (const [file, expected] of Object.entries(pins.files)) {
    const data = await fs.readFile(inside(path.join(root, 'vendor'), file));
    for (const [key, actual] of [['sha256', createHash('sha256').update(data).digest('hex')], ['integrity', 'sha384-' + createHash('sha384').update(data).digest('base64')]]) {
      if (actual !== expected[key]) throw new Error(`Vendor ${key} mismatch: ${file}`);
    }
  }
  const sdkPin = pins.files['hashbin-sdk-v0.4.0.mjs'].integrity;
  if (sdkPin !== 'sha384-zzmaXw5svWRp0YF//G5ytyeqEowixccM/hHVDth46FnGrIlPS7fPki5vbhv+bWCr') throw new Error('HashBin SDK differs from the upstream v0.4.0 SRI.');
  for (const directory of ['src', 'tools', 'testing', 'tests', 'demo']) {
    try {
      for (const file of await walk(root, directory)) {
        if (file.startsWith('demo/vendor/')) continue;
        if (/\.(m?js|cjs)$/.test(file)) {
          const result = spawnSync(process.execPath, ['--check', inside(root, file)], { encoding: 'utf8' });
          if (result.status) throw new Error(result.stderr);
        }
        if (file.startsWith('src/') && /\.(m?js|cjs)$/.test(file)) {
          const text = await fs.readFile(inside(root, file), 'utf8');
          if (/\b(?:localStorage|sessionStorage)\s*\.\s*(?:getItem|setItem|removeItem)\s*\(/.test(text)) throw new Error(`Use the prefixed storage facade: ${file}`);
          if (/\beval\s*\(|new\s+Function\s*\(/.test(text)) throw new Error(`CSP-unsafe runtime code: ${file}`);
        }
      }
    } catch (error) { if (error.code !== 'ENOENT') throw error; }
  }
  if (appConfig) {
    const config = await readJSON(appConfig), appRoot = path.dirname(path.resolve(appConfig));
    if (!config.storagePrefix || !config.slug) throw new Error('App config requires storage and cache prefixes.');
    const html = await fs.readFile(path.join(appRoot, 'index.html'), 'utf8');
    if (!/viewport-fit=cover/.test(html)) throw new Error('Missing viewport-fit=cover.');
    for (const file of await walk(appRoot)) {
      if (file.startsWith('vendor/') || !file.endsWith('.js') || file.endsWith('domain-migration.js')) continue;
      const source = await fs.readFile(inside(appRoot, file), 'utf8');
      for (const match of source.matchAll(/(?:localStorage|sessionStorage)\.(?:getItem|setItem|removeItem)\(['"]([^'"]+)/g)) {
        if (!match[1].startsWith(config.storagePrefix + ':')) throw new Error(`Unprefixed storage key: ${file}: ${match[1]}`);
      }
    }
    if (!html.includes('script-src') || /script-src[^;"']*'unsafe-inline'/.test(html)) throw new Error('Expected a self-only script CSP.');
    if (!html.includes('fragment-kit') && (!html.includes(config.docs) || !html.includes(config.gallery))) throw new Error('Missing kit shell or Docs/Gallery links.');
    if (config.sandboxBootstrapHash) {
      const { SANDBOX_BOOTSTRAP } = await import(pathToSDK(root));
      const expected = 'sha256-' + createHash('sha256').update(SANDBOX_BOOTSTRAP).digest('base64');
      if (config.sandboxBootstrapHash !== expected || !html.includes(expected)) throw new Error('SDK sandbox CSP hash mismatch.');
    }
  }
  console.log('Static checks and vendor integrity passed.');
}
function pathToSDK(root) { return new URL('file://' + path.join(root, 'vendor/hashbin-sdk-v0.4.0.mjs')).href; }
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const options = args();
  check({ ...(options.root ? { root: path.resolve(options.root) } : {}), appConfig: options.config }).catch(error => { console.error(error.message); process.exitCode = 1; });
}
