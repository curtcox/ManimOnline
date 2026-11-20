import { createConfig } from '../../src/core/config.js';
export const config = createConfig({ slug: 'test', name: 'Test', storagePrefix: 'test', canonicalOrigin: 'https://test.hashbin.page/', recoveryOrigin: 'https://curtcox.github.io/test/', repo: 'curtcox/test', docs: 'docs/', gallery: 'gallery.html', documentType: 'test' });
export const type = { type: 'test', settingsKeys: ['w'], normalize: doc => ({ src: doc.src, test: doc.test ?? { width: 800 }, ...(doc.files ? { files: doc.files } : {}) }), isDefault: doc => doc.test.width === 800 && !doc.files };
export function memory() { const values = new Map(); return { getItem: key => values.get(key) ?? null, setItem: (key, value) => values.set(key, String(value)), removeItem: key => values.delete(key), values }; }
export function clock() { let count = 0; const pending = new Map(); return { setTimeout(fn) { pending.set(++count, fn); return count; }, clearTimeout(id) { pending.delete(id); }, async flush() { const work = [...pending.values()]; pending.clear(); for (const fn of work) await fn(); }, pending }; }

