import fs from 'node:fs/promises';
import path from 'node:path';
import { kitRoot, sync, makeManifest } from './vendor-sync.mjs';
import { writeJSON, readJSON } from './lib.mjs';
import { generateOffline } from './offline-assets.mjs';
import { renderGallery } from './render-gallery.mjs';
import { serve } from './serve.mjs';

// Only the unreleased development demo is regenerated. Consumer sync never overwrites pins.
const target = path.join(kitRoot, 'demo');
const { version } = await readJSON(path.join(kitRoot, 'package.json'));
await fs.rm(path.join(target, `vendor/fragment-kit-v${version}`), { recursive: true, force: true });
await writeJSON(path.join(kitRoot, 'manifest.json'), await makeManifest());
await sync({ target });
const { server } = await serve({ root: kitRoot, port: 8000 });
try { await renderGallery(path.join(target, 'gallery.config.mjs')); }
finally { await new Promise(resolve => server.close(resolve)); }
await generateOffline(path.join(target, 'offline.config.json'));
console.log('Prepared pinned demo, gallery covers and offline assets.');
