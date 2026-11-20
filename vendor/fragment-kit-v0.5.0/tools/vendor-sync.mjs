#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';
import { args, sha256, inside, walk, readJSON, writeJSON } from './lib.mjs';

export const kitRoot = fileURLToPath(new URL('../', import.meta.url));
const shipped = ['src', 'vendor', 'tools', 'testing', 'docs', 'package.json', 'LICENSE', 'CHANGELOG.md'];
export async function makeManifest(root = kitRoot) {
  const pkg = await readJSON(path.join(root, 'package.json')), files = {};
  for (const entry of shipped) {
    const stat = await fs.stat(path.join(root, entry));
    for (const file of stat.isDirectory() ? await walk(root, entry) : [entry]) files[file] = sha256(await fs.readFile(inside(root, file)));
  }
  const [major,minor,patch]=pkg.version.split('.').map(Number), supportsOptional=major>0||minor>4||(minor===4&&patch>=1);
  return { name: 'fragment-kit', version: pkg.version, files, ...(supportsOptional?{optionalFiles:Object.keys(files).filter(file=>file.startsWith('vendor/wllama-'))}:{}) };
}
function omissions(manifest, withoutBrowserEngine) {
  const optional=manifest.optionalFiles??[];
  if(!Array.isArray(optional)||new Set(optional).size!==optional.length||optional.some(file=>!/^vendor\/wllama-\d+\.\d+\.\d+\/(?:LICENSE|README\.md|index\.js|compat\.js|compat\.wasm|wllama\.wasm)$/.test(file)||!Object.hasOwn(manifest.files,file)))throw new Error('Invalid optional engine files.');
  if(withoutBrowserEngine&&!optional.length)throw new Error('This release has no optional browser engine declaration.');
  return new Set(withoutBrowserEngine?optional:[]);
}
export async function verifyManifest(root, { published = false, withoutBrowserEngine = false } = {}) {
  const manifest = await readJSON(path.join(root, 'manifest.json'));
  if (manifest.name !== 'fragment-kit' || !/^\d+\.\d+\.\d+$/.test(manifest.version) || !Object.keys(manifest.files ?? {}).length) throw new Error('Invalid kit manifest.');
  const omitted=omissions(manifest,withoutBrowserEngine);
  for (const [file, hash] of Object.entries(manifest.files)) {
    if (!/^[a-f0-9]{64}$/.test(hash) || (!omitted.has(file)&&sha256(await fs.readFile(inside(root, file))) !== hash)) throw new Error(`Vendored file changed: ${file}`);
  }
  const actual = (await walk(root)).filter(file => file !== 'manifest.json').sort();
  if (JSON.stringify(actual) !== JSON.stringify(Object.keys(manifest.files).filter(file=>!omitted.has(file)).sort())) throw new Error('Kit contains missing or unlisted files.');
  if ((await readJSON(path.join(root, 'package.json'))).version !== manifest.version) throw new Error('Kit version mismatch.');
  if (published) {
    // Verify release identity against its published manifest, not merely a self-consistent local hash list.
    const response = await fetch(`https://github.com/curtcox/Tools-for-pages-with-state-in-URL-fragments/releases/download/v${manifest.version}/manifest.json`);
    if (!response.ok) throw new Error(`Kit version v${manifest.version} is not a published release.`);
    if (JSON.stringify(await response.json()) !== JSON.stringify(manifest)) throw new Error('Kit manifest differs from the published release.');
  }
  return manifest;
}
export async function sync({ source = kitRoot, target = process.cwd(), to, withoutBrowserEngine = false } = {}) {
  const pkg = await readJSON(path.join(source, 'package.json'));
  const version = (to ?? pkg.version).replace(/^v/, '');
  if (!/^\d+\.\d+\.\d+$/.test(version)) throw new Error('Use an exact release, e.g. --to v0.1.0.');
  if (pkg.version !== version) throw new Error(`Source is v${pkg.version}, requested v${version}.`);
  let manifest = await makeManifest(source);
  const recorded=await readJSON(path.join(source,'manifest.json')).catch(error=>{if(error.code!=='ENOENT')throw error;return null;});
  if(recorded?.optionalFiles?.some(file=>!Object.hasOwn(manifest.files,file))){
    if(!withoutBrowserEngine)throw new Error('Source omits the browser engine. Use a full release or --without-browser-engine.');
    await verifyManifest(source,{withoutBrowserEngine:true});manifest=recorded;
  }
  const omitted=omissions(manifest,withoutBrowserEngine);
  const destination = path.join(target, 'vendor', `fragment-kit-v${version}`);
  let exists=true;
  try {await fs.access(destination);}catch(error){if(error.code!=='ENOENT')throw error;exists=false;}
  if(exists){
    await verifyManifest(destination,{withoutBrowserEngine});
    const existing = await readJSON(path.join(destination, 'manifest.json'));
    if (JSON.stringify(existing) !== JSON.stringify(manifest)) throw new Error('Pinned version already exists with different bytes. Bump the kit version.');
    return destination;
  }
  await fs.mkdir(path.dirname(destination), { recursive: true });
  const temporary = await fs.mkdtemp(path.join(path.dirname(destination), '.fragment-kit-'));
  try {
    for (const file of Object.keys(manifest.files)) {
      if(omitted.has(file))continue;
      const output = inside(temporary, file); await fs.mkdir(path.dirname(output), { recursive: true }); await fs.copyFile(inside(source, file), output);
    }
    await writeJSON(path.join(temporary, 'manifest.json'), manifest);
    await verifyManifest(temporary,{withoutBrowserEngine}); await fs.rename(temporary, destination);
  } catch (error) { await fs.rm(temporary, { recursive: true, force: true }); throw error; }
  return destination;
}
async function main() {
  const options = args();
  if (options.check) {
    const target = path.resolve(options.target ?? '.');
    const folder = options.kit ? path.resolve(options.kit) : path.join(target, 'vendor', `fragment-kit-${options.to ?? 'v' + (await readJSON(path.join(kitRoot, 'package.json'))).version}`);
    await verifyManifest(folder, { published: Boolean(options.published),withoutBrowserEngine:Boolean(options['without-browser-engine']) }); console.log('Verified ' + folder); return;
  }
  let source = options.source ? path.resolve(options.source) : kitRoot, temporary;
  const localVersion = (await readJSON(path.join(source, 'package.json'))).version;
  if (!options.source && options.to && options.to.replace(/^v/, '') !== localVersion) {
    const version = options.to.replace(/^v/, '');
    if (!/^\d+\.\d+\.\d+$/.test(version)) throw new Error('Invalid release version.');
    temporary = await fs.mkdtemp(path.join(os.tmpdir(), 'fragment-kit-release-'));
    const url = `https://github.com/curtcox/Tools-for-pages-with-state-in-URL-fragments/releases/download/v${version}/fragment-kit-v${version}.tgz`;
    const response = await fetch(url); if (!response.ok) throw new Error(`Release download failed: ${response.status}.`);
    const archive = path.join(temporary, 'release.tgz'); await fs.writeFile(archive, new Uint8Array(await response.arrayBuffer()));
    const entries = execFileSync('tar', ['-tzf', archive], { encoding: 'utf8' }).trim().split('\n');
    for (const entry of entries) { const name = entry.replace(/\/$/, ''); if (name) inside(temporary, name); }
    const listing = execFileSync('tar', ['-tvzf', archive], { encoding: 'utf8' }).trim().split('\n');
    if (listing.some(line => !['d', '-'].includes(line[0]))) throw new Error('Release archive contains links or special files.');
    execFileSync('tar', ['-xzf', archive, '-C', temporary]); source = path.join(temporary, 'fragment-kit');
    await verifyManifest(source, { published: true });
  }
  try { console.log(await sync({ source, target: path.resolve(options.target ?? '.'), to: options.to,withoutBrowserEngine:Boolean(options['without-browser-engine']) })); }
  finally { if (temporary) await fs.rm(temporary, { recursive: true, force: true }); }
}
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) main().catch(error => { console.error(error.message); process.exitCode = 1; });
