#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';
import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';
import { pathToFileURL } from 'node:url';
import { compress } from '../src/core/compression.js';
import { computeCID } from '../src/core/cid.js';
import { encode64, bytes } from '../src/core/bytes.js';
import { args, sha256, walk, writeJSON } from './lib.mjs';

const options = args(), parent = path.resolve(options.parent ?? '..');
const apps = { livelier: 'livelier', PythonOnline: 'python', ManimOnline: 'manim', AudioOnline: 'audio', R: 'r', pages: 'pages', GnuPlotOnline: 'gnuplot', modl: 'modl', sheets: 'sheets', apptron: 'apptron' };
const require = createRequire(import.meta.url);
for (const [repo, slug] of Object.entries(apps)) {
  const root = path.join(parent, repo), sourceFiles = {}, references = [], storage = [], caches = [];
  const files = [];
  for (const entry of await fs.readdir(root, { withFileTypes: true })) {
    if (entry.isDirectory() && ['src', 'js', 'tests', 'docs', 'docs-src'].includes(entry.name)) files.push(...await walk(root, entry.name));
    else if (entry.isFile() && /^(?:README|service-worker|offline-assets|index\.html)/.test(entry.name)) files.push(entry.name);
  }
  for (const file of files) {
    if (!/\.(?:js|cjs|html|md|json)$/.test(file)) continue;
    const data = await fs.readFile(path.join(root, file));
    if (data.length > 1_000_000) continue;
    const source = data.toString(); sourceFiles[file] = sha256(data);
    for (const match of source.matchAll(/(?:localStorage|sessionStorage)\.(?:getItem|setItem|removeItem)\(\s*['"]([^'"]+)|\bkey:\s*['"]([^'"]+)/g)) storage.push({ file, key: match[1] ?? match[2] });
    for (const match of source.matchAll(/(?:version|CACHE(?:_NAME)?|cacheName)\s*[:=]\s*['"`]([^'"`\n]+)/g)) caches.push({ file, expression: match[1] });
    for (const match of source.matchAll(/(?:https?:\/\/[^\s"'<>`]+|(?:\.\/)?\?(?:example|compressed|doc)=[^\s"'<>`]+)/g)) {
      if (references.length < 300 && /(?:#h1=|#src=|#project=|[?&](?:example|compressed|doc)=|\/docs\/|gallery\.html)/.test(match[0])) references.push({ file, href: match[0] });
    }
  }
  let example, src, raw, legacyDocuments;
  if (repo === 'modl') {
    src = await fs.readFile(path.join(parent, 'ManimOnline/examples/basic_diagram.modl'), 'utf8');
    example = { id: 'modl' }; raw = JSON.stringify({ src, pos: { a: [120, 80] } });
  } else if (repo === 'sheets') {
    const catalog = JSON.parse(await fs.readFile(path.join(root, 'examples/catalog.json'), 'utf8'));
    example = catalog[0]; src = await fs.readFile(path.join(root, example.path), 'utf8');
    legacyDocuments = (await import(pathToFileURL(path.join(root, 'src/hashbin.js')))).HashBinDocuments;
    raw = legacyDocuments.serialize({ src, type: example.format, view: 'preview' });
  } else if (repo === 'apptron') {
    example = (await import(pathToFileURL(path.join(root, 'src/examples.js')))).examples[0];
    src = await fs.readFile(path.join(root, `examples/${example.id}.txtar`), 'utf8');
    legacyDocuments = (await import(pathToFileURL(path.join(root, 'src/hashbin.js')))).HashBinDocuments;
    raw = legacyDocuments.serialize({ src });
  } else {
    const module = require(path.join(root, 'src/examples.js'));
    example = (Array.isArray(module) ? module : module.catalog ?? module.ExampleCatalog)[0];
    src = example.source ?? example.src ?? example.document?.src ?? example.project?.files.find(file => file.name === example.project.entry)?.text;
    if (src === undefined && example.path) src = await fs.readFile(path.join(root, example.path), 'utf8');
    legacyDocuments = require(path.join(root, 'src/hashbin.js')).HashBinDocuments;
    let doc = example.document ?? { src };
    if (repo === 'pages') doc = example.project;
    if (repo === 'ManimOnline') doc = { src, type: example.type };
    if (repo === 'R') doc.r = { stdin: 'Corpus input\n', autorun: false };
    if (repo === 'PythonOnline') doc.python = { stdin: example.stdin, autorun: false };
    if (repo === 'GnuPlotOnline') doc = { src, files: { 'values.dat': '1 2\n2 3' }, gnuplot: { width: 640, height: 480, background: 'transparent' } };
    if (repo === 'AudioOnline') doc.settings = { sampleRate: 22050, channels: 1 };
    raw = legacyDocuments.serialize(doc);
  }
  if (typeof src !== 'string') throw new Error(`No example source for ${repo}`);
  const recovery = `https://curtcox.github.io/${repo}/`, url = new URL(recovery);
  const cases = [
    { label: 'source fragment', href: recovery + '#' + encodeURIComponent(src), kind: 'source', src },
    { label: 'compressed query', href: recovery + '?compressed=' + compress(src), kind: 'source', src },
    { label: 'document query', href: recovery + '?doc=' + compress(raw), kind: 'source', raw },
    { label: 'document fragment', href: recovery + '#' + encodeURIComponent(raw), kind: 'source', raw },
    { label: 'example', href: recovery + '?example=' + example.id, kind: 'example', id: example.id },
    { label: 'CID', href: recovery + '#' + await computeCID(src), kind: 'cid', cid: await computeCID(src) },
  ];
  if (repo === 'sheets') cases.push({ label: 'source fragment overflow', href: recovery + '?format=gfm&view=preview#src=' + compress(src), kind: 'source', src });
  if (repo === 'modl') cases.push({ label: 'h1 positions', href: recovery + '#h1=' + encode64(bytes(raw)), kind: 'source', raw });
  if (repo === 'ManimOnline' && example.editorURL) cases.push({ label: 'catalog URL', href: new URL(example.editorURL, recovery).href, kind: 'example', id: example.id });
  // Record the old serializer's bytes and old parser's decoded document independently of the kit.
  const expected = legacyDocuments ? legacyDocuments.parse(raw) : JSON.parse(raw);
  await writeJSON(`tests/corpus/${repo}.json`, { repo, slug, commit: execFileSync('git', ['-C', root, 'rev-parse', 'HEAD'], { encoding: 'utf8' }).trim(), example: { id: example.id, source: src, raw, expected }, sourceFiles, storage, caches, references, cases });
  console.log(`${repo}: ${cases.length} executable cases, ${references.length} discovered references`);
}
