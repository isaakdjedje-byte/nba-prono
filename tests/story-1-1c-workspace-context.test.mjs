import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const testFilePath = fileURLToPath(import.meta.url);
const testDir = path.dirname(testFilePath);
const repoRoot = path.resolve(testDir, '..');
const appRoot = path.join(repoRoot, 'nba-prono');

function readText(filePath) {
  return fs.readFileSync(filePath, 'utf8');
}

test('README documents canonical workspace boundaries and command contexts', () => {
  const readmePath = path.join(appRoot, 'README.md');
  const readme = readText(readmePath);

  assert.match(readme, /nba_prono\//, 'README must mention coordination root nba_prono/');
  assert.match(readme, /nba-prono\//, 'README must mention app root nba-prono/');
  assert.match(readme, /`dev`/i, 'README must document dev command context');
  assert.match(readme, /`build`/i, 'README must document build command context');
  assert.match(readme, /`test:unit`/i, 'README must document test:unit command context');
  assert.match(readme, /`test:smoke`/i, 'README must document test:smoke command context');
  assert.match(readme, /`contracts:check`/i, 'README must document contracts:check command context');
});

test('Workspace guard script exists and fails fast outside app root', () => {
  const guardPath = path.join(appRoot, 'scripts', 'check-workspace-context.mjs');
  assert.equal(fs.existsSync(guardPath), true, 'Guard script must exist at nba-prono/scripts/check-workspace-context.mjs');

  const result = spawnSync(process.execPath, [guardPath], {
    cwd: repoRoot,
    encoding: 'utf8',
  });

  assert.notEqual(result.status, 0, 'Guard must fail with non-zero status outside app root');
  assert.match(result.stderr + result.stdout, /nba-prono\//i, 'Guard error must direct user to run commands from nba-prono/');
});

test('Critical npm scripts prepend workspace guard', () => {
  const packageJsonPath = path.join(appRoot, 'package.json');
  const pkg = JSON.parse(readText(packageJsonPath));
  const mustBeGuarded = ['dev', 'build', 'lint', 'test:unit', 'test:smoke', 'contracts:check'];

  for (const name of mustBeGuarded) {
    const script = pkg.scripts?.[name];
    assert.equal(typeof script, 'string', `Script ${name} must exist`);
    assert.match(script, /^node\s+scripts\/check-workspace-context\.mjs\s+&&\s+/, `Script ${name} must start with workspace guard`);
  }
});

test('CI declares app working-directory for npm steps', () => {
  const ciPath = path.join(appRoot, '.github', 'workflows', 'ci.yml');
  const ci = readText(ciPath);

  const stepBlocks = ci.split(/\n\s*-\s+name:/g).slice(1);

  for (const block of stepBlocks) {
    if (/\brun:\s*\|?[\s\S]*?\bnpm\b/m.test(block)) {
      assert.match(
        block,
        /\n\s*working-directory:\s*nba-prono\b/,
        'Each npm step must set working-directory: nba-prono',
      );
    }
  }

  assert.match(ci, /working-directory:\s*nba-prono/, 'CI must set working-directory to nba-prono for npm steps');
  assert.match(ci, /npm\s+ci/, 'CI must still install dependencies with npm ci');
  assert.match(ci, /npm\s+run\s+lint/, 'CI must still run lint');
  assert.match(ci, /npm\s+run\s+test:unit/, 'CI must still run unit tests');
  assert.match(ci, /npm\s+run\s+contracts:check/, 'CI must still run contracts check');
  assert.match(ci, /npm\s+run\s+test:smoke/, 'CI must run smoke tests');
});
