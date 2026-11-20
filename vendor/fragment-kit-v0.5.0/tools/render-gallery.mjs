#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';
import { args, sha256, inside, readJSON, writeJSON } from './lib.mjs';

export async function renderGallery(configFile, check = false) {
  configFile = path.resolve(configFile);
  const root = path.dirname(configFile), { default: config } = await import(pathToFileURL(configFile));
  const output = inside(root, config.output), fingerprints = {};
  const dependencies = {};
  for (const file of config.dependencies ?? []) dependencies[file] = sha256(await fs.readFile(inside(root, file)));
  const renderer = sha256(await fs.readFile(configFile));
  if (check) {
    const recorded = await readJSON(path.join(output, 'fingerprints.json'));
    if (JSON.stringify(recorded.dependencies) !== JSON.stringify(dependencies) || recorded.renderer !== renderer) throw new Error('Gallery renderer dependencies changed. Regenerate covers.');
    if (Object.keys(recorded.examples).length !== config.catalog.length) throw new Error('Gallery catalog changed.');
    for (const example of config.catalog) {
      if (!/^[\w-]+$/.test(example.id)) throw new Error('Invalid example id.');
      const entry = recorded.examples[example.id];
      if (entry?.document !== sha256(JSON.stringify(example)) || entry.cover !== sha256(await fs.readFile(path.join(output, example.id + '.png')))) throw new Error(`Stale gallery cover: ${example.id}`);
    }
    return;
  }
  const { chromium } = await import('@playwright/test');
  const browser = await chromium.launch({ ...(process.env.PLAYWRIGHT_EXECUTABLE_PATH ? { executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH } : {}) });
  try {
    await fs.mkdir(output, { recursive: true });
    const page = await browser.newPage({ viewport: { width: 1280, height: 800 }, deviceScaleFactor: 1, colorScheme: 'light', serviceWorkers: 'block' });
    for (const example of config.catalog) {
      if (!/^[\w-]+$/.test(example.id)) throw new Error('Invalid example id.');
      const target = await config.renderCover(page, example) ?? page;
      const cover = await target.screenshot({ path: path.join(output, example.id + '.png') });
      fingerprints[example.id] = { document: sha256(JSON.stringify(example)), cover: sha256(cover) };
    }
    await writeJSON(path.join(output, 'fingerprints.json'), { dependencies, renderer, examples: fingerprints });
  } finally { await browser.close(); }
}
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const options = args();
  renderGallery(options.config ?? 'gallery.config.mjs', Boolean(options.check)).catch(error => { console.error(error.message); process.exitCode = 1; });
}
