#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath } from 'node:url';
import { args } from './lib.mjs';
import { computeCID } from '../src/core/cid.js';
import { readResponse } from '../src/core/bytes.js';
import { parseManifest, MAX_SHARD_BYTES } from '../src/ai/browser/manifest.js';
export async function makeModelManifest({ input, name, license, source, mirrors, contextTokens = 2048, memoryBytes = 1024 * 1024 * 1024, shardBytes = MAX_SHARD_BYTES, onShard = async () => {} }) {
  if (!Number.isSafeInteger(shardBytes) || shardBytes < 1 || shardBytes > MAX_SHARD_BYTES) throw new Error('Shard size must be between 1 and 64 MiB.');
  const fileName = path.basename(new URL(input, 'file:///').pathname);
  if (/^https:/.test(input)) {
    if (!/\/resolve\/[a-f0-9]{40}\//.test(input)) throw new Error('URL must be commit-pinned.');
    const response = await fetch(input, { signal: AbortSignal.timeout(120000), credentials: 'omit' });
    if (!response.ok) throw new Error(`Model fetch failed: ${response.status}.`);
    if (Number(response.headers.get('content-length')) >= 2 ** 31) { await response.body.cancel(); throw new Error('Model file exceeds 2 GiB.'); }
    const temporary = await fs.mkdtemp(path.join(os.tmpdir(), 'fragment-kit-model-'));
    const target = path.join(temporary, fileName), output = await fs.open(target, 'w');
    const reader = response.body.getReader(); let size = 0;
    try {
      while (true) { const {value,done} = await reader.read(); if (done) break; size += value.byteLength; if (size >= 2 ** 31) throw new Error('Model file exceeds 2 GiB.'); await output.write(value); }
      await output.close();
      return await makeModelManifest({ input: target, name, license, source, mirrors, contextTokens, memoryBytes, shardBytes, onShard });
    } finally { await reader.cancel().catch(() => {}); reader.releaseLock(); await output.close().catch(() => {}); await fs.rm(temporary, {recursive:true,force:true}); }
  }
  const file = await fs.open(input, 'r'), size = (await file.stat()).size, close = () => file.close();
  const shards = [];
  try {
    if (size < 1 || size >= 2 ** 31) throw new Error('Model file must be between 1 byte and 2 GiB.');
    for (let offset = 0; offset < size; offset += shardBytes) {
      const buffer = new Uint8Array(Math.min(shardBytes, size - offset)); let filled = 0;
      while (filled < buffer.length) { const { bytesRead } = await file.read(buffer.subarray(filled), 0, buffer.length - filled, offset + filled); if (!bytesRead) throw new Error('Model file changed during reading.'); filled += bytesRead; }
      const cid = await computeCID(buffer); shards.push({ cid, offset }); await onShard({ cid, bytes: buffer });
    }
  } finally { await close(); }
  const manifest = parseManifest({ format: 'fragment-kit-model', version: 1, name, license, source, engine: { id: 'wllama', format: 'gguf' }, capabilities: ['generate'], contextTokens, requires: { webgpu: false, memoryBytes }, files: [{ path: fileName, bytes: size, shards }], mirrors });
  return { manifest, cid: await computeCID(JSON.stringify(manifest)) };
}
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const opts = args();
  const mirrors = opts.mirrors ? JSON.parse(await fs.readFile(opts.mirrors, 'utf8')) : ['https://256t.us/{cid}', 'https://256t.org/{cid}'];
  if (opts.shards) await fs.mkdir(opts.shards, { recursive: true });
  makeModelManifest({ input: opts.input, name: opts.name, license: { id: opts.license, url: opts['license-url'] }, source: opts.source, mirrors,
    contextTokens: Number(opts.context ?? 2048), memoryBytes: Number(opts.memory ?? 1073741824), shardBytes: Number(opts['shard-bytes'] ?? MAX_SHARD_BYTES),
    onShard: opts.shards ? ({ cid, bytes }) => fs.writeFile(path.join(opts.shards, cid), bytes) : undefined,
  }).then(async result => { await fs.writeFile(opts.output, JSON.stringify(result.manifest)); console.log(JSON.stringify({ cid: result.cid, output: opts.output })); }).catch(error => { console.error(error.message); process.exitCode = 1; });
}
