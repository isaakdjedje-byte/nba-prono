import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

const appRoot = path.resolve(process.cwd(), 'nba-prono');

test('Story 1.1 scaffold exists with src/ alias config', () => {
  const packageJsonPath = path.join(appRoot, 'package.json');
  const tsconfigPath = path.join(appRoot, 'tsconfig.json');

  assert.equal(fs.existsSync(packageJsonPath), true, 'package.json missing: scaffold not created');
  assert.equal(fs.existsSync(tsconfigPath), true, 'tsconfig.json missing: scaffold not created');

  const tsconfigRaw = fs.readFileSync(tsconfigPath, 'utf8');
  const tsconfig = JSON.parse(tsconfigRaw);
  assert.equal(tsconfig.compilerOptions?.paths?.['@/*']?.[0], './src/*', 'alias @/* -> ./src/* missing');
});
