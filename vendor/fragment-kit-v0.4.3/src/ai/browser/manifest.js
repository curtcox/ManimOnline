import { cid as parseCID, isCID, cidLength } from '../../core/cid.js';
import { loadContent } from '../../core/content.js';
import { text } from '../../core/bytes.js';
import { keys, string, number, parseData, endpoint } from '../data.js';
export const MAX_MANIFEST_BYTES = 1024 * 1024, MAX_SHARD_BYTES = 64 * 1024 * 1024;
export function parseManifest(input) {
  const m = parseData(input, MAX_MANIFEST_BYTES);
  keys(m, ['format', 'version', 'name', 'license', 'source', 'engine', 'capabilities', 'contextTokens', 'requires', 'files', 'mirrors'], 'model manifest');
  if (m.format !== 'fragment-kit-model' || m.version !== 1) throw new Error('Unsupported model manifest.');
  string(m.name, 'model name', 1024); keys(m.license, ['id', 'url'], 'license'); string(m.license.id, 'license ID', 200); endpoint(m.license.url, { loopback: false });
  endpoint(m.source, { loopback: false }); keys(m.engine, ['id', 'format'], 'engine');
  if (m.engine.id !== 'wllama' || m.engine.format !== 'gguf') throw new Error('This engine or model format is not allowlisted.');
  if (!Array.isArray(m.capabilities) || m.capabilities.length !== 1 || m.capabilities[0] !== 'generate') throw new Error('Unsupported browser capability.');
  number(m.contextTokens, 'model context', { min: 1, max: 1048576, integer: true });
  keys(m.requires, ['webgpu', 'memoryBytes'], 'model requirements');
  if (typeof m.requires.webgpu !== 'boolean') throw new Error('Invalid WebGPU requirement.'); number(m.requires.memoryBytes, 'model memory', { min: 1, integer: true });
  if (!Array.isArray(m.files) || !m.files.length || m.files.length > 100 || !Array.isArray(m.mirrors) || !m.mirrors.length || m.mirrors.length > 20) throw new Error('Expected bounded model files and mirrors.');
  const paths = new Set(); let total = 0;
  for (const f of m.files) {
    keys(f, ['path', 'bytes', 'shards'], 'model file'); string(f.path, 'model path', 1024);
    if (paths.has(f.path) || !/^[\w./-]+\.gguf$/.test(f.path) || f.path.startsWith('/') || f.path.split('/').some(p => p === '.' || p === '..' || !p)) throw new Error('Unsafe or duplicate model path.'); paths.add(f.path);
    number(f.bytes, 'model file bytes', { min: 1, max: 2 ** 31 - 1, integer: true }); total += f.bytes;
    if (!Number.isSafeInteger(total) || !Array.isArray(f.shards) || !f.shards.length || f.shards.length > 32768) throw new Error('Invalid model shards.');
    let offset = 0;
    for (const shard of f.shards) {
      keys(shard, ['cid', 'offset'], 'shard');
      if (!isCID(shard.cid) || cidLength(shard.cid) < 1 || cidLength(shard.cid) > MAX_SHARD_BYTES || shard.offset !== offset) throw new Error('Invalid shard CID, size or offset.');
      offset += cidLength(shard.cid);
    }
    if (offset !== f.bytes) throw new Error('Model shards do not cover the file.');
  }
  for (const mirror of m.mirrors) {
    if (typeof mirror === 'object') { keys(mirror, ['url', 'ranges'], 'mirror'); if (mirror.ranges !== true) throw new Error('Range mirror must declare ranges.'); }
    const template = typeof mirror === 'string' ? mirror : mirror.url;
    string(template, 'mirror URL', 4096);
    if (typeof mirror === 'string' && !template.includes('{cid}')) throw new Error('CID mirror needs {cid}.');
    if (typeof mirror !== 'string' && !template.includes('{path}')) throw new Error('Range mirror needs {path}.');
    endpoint(template.replaceAll('{cid}', 'CID').replaceAll('{path}', 'model.gguf'), { loopback: true });
    if (typeof mirror !== 'string' && !/\/resolve\/[a-f0-9]{40}\//.test(template)) throw new Error('Range mirrors must use a commit-pinned /resolve/<40-hex>/ path.');
  }
  return m;
}
export async function loadManifest(value, options = {}) {
  const cid = parseCID(typeof value === 'string' ? value.replace(/^256t:/, '') : value, options.allowedHosts ?? ['256t.us', '256t.org', 'hashbin.org']);
  if (!cid) throw new Error('Enter a valid model manifest CID or saved link.');
  return { cid, manifest: parseManifest(text(await loadContent(cid, { ...options, maxBytes: MAX_MANIFEST_BYTES }))) };
}
export function modelSuggestion(href) {
  const value = new URL(href).searchParams.get('model');
  if (value === null) return null;
  if (!isCID(value)) throw new Error('Invalid model suggestion. The document can still be opened.');
  return value;
}
