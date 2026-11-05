import { bounded, MAX_BYTES } from './bytes.js';

export class DocumentRegistry {
  constructor() { this.types = new Map(); }
  register(adapter) {
    if (!adapter || typeof adapter.type !== 'string' || typeof adapter.normalize !== 'function') throw new Error('A DocumentType needs type and normalize.');
    if (this.types.has(adapter.type)) throw new Error(`Document type already registered: ${adapter.type}.`);
    this.types.set(adapter.type, Object.freeze({ settingsKeys: [], isDefault: () => false, fileName: 'document.json', contentType: 'application/json', ...adapter }));
    return this.types.get(adapter.type);
  }
  get(type) { if (!this.types.has(type)) throw new Error(`Unknown document type: ${type}.`); return this.types.get(type); }
}
export function createDocuments(adapter, maxBytes = MAX_BYTES) {
  if (typeof adapter.normalize !== 'function' || !adapter.type) throw new Error('Invalid DocumentType.');
  function normalize(value) {
    const doc = adapter.normalize(value);
    if (!doc || typeof doc.src !== 'string') throw new Error('Source must be text.');
    bounded(JSON.stringify(doc), maxBytes);
    return doc;
  }
  function serialize(value) {
    const doc = normalize(value);
    return bounded(JSON.stringify({ ...doc, format: 'hashbin-diagram', version: 1, type: adapter.type }), maxBytes);
  }
  function parse(payload) {
    bounded(payload, maxBytes);
    let value;
    try { value = JSON.parse(payload); } catch { return normalize(adapter.parseLegacy?.(payload) ?? { src: payload }); }
    if (adapter.legacyEnvelopeTypes?.includes(`${value?.format}:${value?.type ?? ''}`)) {
      const legacy = adapter.parseLegacy?.(payload);
      if (legacy === undefined) throw new Error('Legacy adapter could not read this document.');
      return normalize(legacy);
    }
    if (value?.format === 'hashbin-diagram') {
      if (value.version !== 1) throw new Error('Unsupported saved document version.');
      if (value.type !== adapter.type) throw new Error(`Saved document is for ${value.type ?? 'an unknown app'}, not ${adapter.type}.`);
      const { format, version, type, ...doc } = value;
      return normalize(doc);
    }
    const legacy = adapter.parseLegacy?.(payload);
    if (legacy !== undefined) return normalize(legacy);
    // Legacy fragments sometimes contain an unwrapped JSON document, or JSON source.
    if (value && typeof value === 'object' && typeof value.src === 'string') return normalize(value);
    return normalize({ src: payload });
  }
  return Object.freeze({ normalize, serialize, parse, adapter, maxBytes });
}
