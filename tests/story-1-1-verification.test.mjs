import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';

const appRoot = path.resolve(process.cwd(), 'nba-prono');

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

test('Verification scripts exist for lint and route smoke checks', () => {
  const packageJsonPath = path.join(appRoot, 'package.json');
  const smokeScriptPath = path.join(appRoot, 'scripts', 'smoke-routes.mjs');
  const pkg = readJson(packageJsonPath);

  assert.equal(typeof pkg.scripts?.lint, 'string', 'lint script must exist');
  assert.equal(typeof pkg.scripts?.['test:smoke'], 'string', 'test:smoke script must exist');
  assert.equal(fs.existsSync(smokeScriptPath), true, 'smoke-routes.mjs must exist');
});

test('Smoke routes runtime check validates picks, no-bet and guardrail', () => {
  const npmCmd = process.platform === 'win32' ? 'npm.cmd' : 'npm';
  const result = spawnSync(npmCmd, ['run', 'test:smoke'], {
    cwd: appRoot,
    encoding: 'utf8',
    timeout: 180000,
  });

  assert.equal(result.status, 0, result.stderr || result.stdout || 'test:smoke failed');
  assert.match(result.stdout, /Smoke routes check passed\./, 'Smoke check success marker missing');
});
