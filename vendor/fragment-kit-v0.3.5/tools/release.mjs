#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import { execFileSync } from 'node:child_process';
import { kitRoot, sync, makeManifest } from './vendor-sync.mjs';
import { readJSON, writeJSON, sha256 } from './lib.mjs';

const { version } = await readJSON(path.join(kitRoot, 'package.json'));
const tag = process.env.GITHUB_REF_TYPE === 'tag' ? process.env.GITHUB_REF_NAME : null;
if (tag && tag !== 'v' + version) throw new Error('Release tag and package version differ.');
const temporary = await fs.mkdtemp(path.join(os.tmpdir(), 'fragment-kit-package-'));
try {
  const folder = await sync({ target: temporary });
  await fs.rename(folder, path.join(temporary, 'fragment-kit'));
  const output = path.join(kitRoot, 'dist'); await fs.mkdir(output, { recursive: true });
  const archive = `fragment-kit-v${version}.tgz`;
  execFileSync('tar', ['-czf', path.join(output, archive), '-C', temporary, 'fragment-kit']);
  await writeJSON(path.join(output, 'manifest.json'), await makeManifest());
  const sums = [];
  for (const file of [archive, 'manifest.json']) sums.push(sha256(await fs.readFile(path.join(output, file))) + '  ' + file);
  await fs.writeFile(path.join(output, 'SHA256SUMS'), sums.join('\n') + '\n');
  console.log(path.join(output, archive));
} finally { await fs.rm(temporary, { recursive: true, force: true }); }
