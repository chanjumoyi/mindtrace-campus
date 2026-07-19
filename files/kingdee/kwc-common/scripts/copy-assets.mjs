import { copyFile, readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';

const root = new URL('../', import.meta.url);
const dist = new URL('../dist/', import.meta.url);
await copyFile(new URL('src/theme.css', root), new URL('theme.css', dist));
await copyFile(new URL('component-manifest.json', root), new URL('component-manifest.json', dist));

const files = ['index.js', 'common-shell.js', 'host-adapter.js', 'kingdee-host-adapter.js', 'api-client.js', 'lifecycle.js', 'theme.css', 'component-manifest.json'];
const checksums = [];
for (const file of files) {
  const body = await readFile(new URL(file, dist));
  checksums.push(`${createHash('sha256').update(body).digest('hex')}  ${file}`);
}
await writeFile(new URL('checksums.sha256', dist), `${checksums.join('\n')}\n`);
