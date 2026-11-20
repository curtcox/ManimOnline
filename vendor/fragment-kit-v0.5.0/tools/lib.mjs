import fs from 'node:fs/promises';
import path from 'node:path';
import { createHash } from 'node:crypto';
export const sha256 = value => createHash('sha256').update(value).digest('hex');
export function args(argv = process.argv.slice(2)) {
  const result = {};
  for (let i = 0; i < argv.length; i++) {
    if (!argv[i].startsWith('--')) { (result._ ??= []).push(argv[i]); continue; }
    const name = argv[i].slice(2);
    result[name] = argv[i + 1] && !argv[i + 1].startsWith('--') ? argv[++i] : true;
  }
  return result;
}
export function inside(root, relative) {
  if (typeof relative !== 'string' || !relative || relative.includes('\\') || path.isAbsolute(relative) || relative.split('/').some(part => part === '..' || part === '.' || !part)) throw new Error(`Unsafe path: ${relative}`);
  return path.join(root, relative);
}
export async function walk(root, relative = '') {
  const entries = await fs.readdir(path.join(root, relative), { withFileTypes: true });
  const result = [];
  for (const entry of entries.sort((a, b) => a.name.localeCompare(b.name))) {
    if (entry.name.startsWith('.') || entry.name === 'node_modules') continue;
    const name = relative ? relative + '/' + entry.name : entry.name;
    if (entry.isSymbolicLink()) throw new Error(`Symlinks are not shipped: ${name}`);
    if (entry.isDirectory()) result.push(...await walk(root, name));
    else result.push(name);
  }
  return result;
}
export async function readJSON(file) { return JSON.parse(await fs.readFile(file, 'utf8')); }
export async function writeJSON(file, value) { await fs.mkdir(path.dirname(file), { recursive: true }); await fs.writeFile(file, JSON.stringify(value, null, 2) + '\n'); }
