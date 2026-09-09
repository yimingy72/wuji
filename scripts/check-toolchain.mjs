import { readFile } from 'node:fs/promises';

const repositoryRoot = new URL('../', import.meta.url);
const read = path => readFile(new URL(path, repositoryRoot), 'utf8');
const [manifestText, packageText, nodeVersionText, pythonVersionText, bootstrapText, apiProjectText] = await Promise.all([
  read('toolchain/manifest.json'),
  read('package.json'),
  read('.node-version'),
  read('.python-version'),
  read('scripts/bootstrap-toolchain.sh'),
  read('apps/api/pyproject.toml'),
]);
const manifest = JSON.parse(manifestText);
const packageJson = JSON.parse(packageText);

function assertEqual(actual, expected, label) {
  if (actual !== expected) throw new Error(`${label}: expected ${expected}, got ${actual}`);
}

assertEqual(process.version, `v${manifest.node.version}`, 'active Node');
assertEqual(nodeVersionText.trim(), manifest.node.version, '.node-version');
assertEqual(packageJson.packageManager, `pnpm@${manifest.node.manager_version}`, 'packageManager');
assertEqual(pythonVersionText.trim(), manifest.python.version, '.python-version');
for (const artifact of Object.values(manifest.uv.artifacts)) {
  if (!bootstrapText.includes(artifact.sha256)) throw new Error(`bootstrap omits uv checksum ${artifact.sha256}`);
}
if (!bootstrapText.includes('python install --no-bin')) throw new Error('bootstrap must prevent user-bin Python links');
if (!apiProjectText.includes(`requires-python = "==${manifest.python.version}"`)) {
  throw new Error('API Python requirement differs from toolchain manifest');
}
for (const image of Object.values(manifest.images)) {
  if (!/^sha256:[a-f0-9]{64}$/.test(image.index_digest)) throw new Error(`Invalid index digest for ${image.tag}`);
  if (!/^sha256:[a-f0-9]{64}$/.test(image.linux_amd64_digest)) throw new Error(`Invalid linux/amd64 digest for ${image.tag}`);
}

console.log('Toolchain manifest, bootstrap pins, project versions and image digests are consistent.');
