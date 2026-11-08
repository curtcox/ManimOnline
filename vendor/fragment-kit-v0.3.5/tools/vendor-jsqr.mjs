import fs from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
/** Reproducible, documented derivative. The original npm distribution stays untouched. */
export async function prepareJsQR(check = false) {
  const root = new URL('../vendor/jsqr/', import.meta.url);
  const original = await fs.readFile(new URL('jsQR.js', root), 'utf8');
  const needle = 'alignmentPatternCenters: [6, 30, 54, 74, 102]';
  if (original.split(needle).length !== 2) throw new Error('Unexpected jsQR source. Review the version-23 correction.');
  const source = '// Fragment Kit derivative of jsQR 1.4.0. Changed version 23 alignment center 74 to 78.\n// Original distribution: jsQR.js; Apache-2.0 license: ../LICENSE-jsQR.\n' + original.replace(needle, 'alignmentPatternCenters: [6, 30, 54, 78, 102]');
  const output = new URL('jsQR-fk.js', root);
  if (check) { if (await fs.readFile(output, 'utf8') !== source) throw new Error('jsQR derivative is stale.'); }
  else await fs.writeFile(output, source);
}
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) await prepareJsQR(process.argv.includes('--check'));
