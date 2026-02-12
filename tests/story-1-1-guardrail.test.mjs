import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

const appRoot = path.resolve(process.cwd(), 'nba-prono');

function read(filePath) {
  return fs.readFileSync(filePath, 'utf8');
}

test('GuardrailBanner component exists in policy feature', () => {
  const guardrailPath = path.join(
    appRoot,
    'src',
    'features',
    'policy',
    'components',
    'GuardrailBanner.tsx',
  );

  assert.equal(fs.existsSync(guardrailPath), true, 'Missing GuardrailBanner component');
});

test('Dashboard layout renders GuardrailBanner via alias import', () => {
  const layoutPath = path.join(appRoot, 'src', 'app', '(dashboard)', 'layout.tsx');
  const layout = read(layoutPath);

  assert.match(
    layout,
    /from ['"]@\/features\/policy\/components\/GuardrailBanner['"]/,
    'Layout must import GuardrailBanner via @ alias',
  );
  assert.match(layout, /<GuardrailBanner\s*\/?\s*>|<GuardrailBanner\s*\/>/, 'Layout must render GuardrailBanner');
});

test('GuardrailBanner displays explicit default status', () => {
  const guardrailPath = path.join(
    appRoot,
    'src',
    'features',
    'policy',
    'components',
    'GuardrailBanner.tsx',
  );
  const guardrail = read(guardrailPath);

  assert.match(guardrail, /Statut guardrail par defaut\s*:\s*No-Hard-Stop/i, 'Default guardrail status text missing');
});
