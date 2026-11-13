import fs from 'node:fs/promises';
import path from 'node:path';
const root = process.cwd(), output = path.join(root, '_site');
await fs.rm(output, { recursive: true, force: true }); await fs.mkdir(output);
for (const file of ['index.html', 'demo', 'docs']) await fs.cp(path.join(root, file), path.join(output, file), { recursive: true });
await fs.writeFile(path.join(output, '.nojekyll'), '');
