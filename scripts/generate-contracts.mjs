import { readFile, mkdir, writeFile } from 'node:fs/promises';
import openapiTS, { astToString } from 'openapi-typescript';

const source = new URL('../packages/contracts/openapi.yaml', import.meta.url);
const destination = new URL('../packages/contracts/generated/api.d.ts', import.meta.url);
const output = astToString(await openapiTS(source));
if (process.argv.includes('--check')) {
  const existing = await readFile(destination, 'utf8').catch(() => '');
  if (existing !== output) {
    throw new Error('Generated contracts are stale. Run pnpm contracts:generate and include the output.');
  }
  console.log('Generated TypeScript contract matches OpenAPI.');
} else {
  await mkdir(new URL('../packages/contracts/generated/', import.meta.url), { recursive: true });
  await writeFile(destination, output);
  console.log('Generated packages/contracts/generated/api.d.ts');
}
