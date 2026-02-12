import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

const appRoot = path.resolve(process.cwd(), 'nba-prono');
const dashboardRoot = path.join(appRoot, 'src', 'app', '(dashboard)');

function read(filePath) {
  return fs.readFileSync(filePath, 'utf8');
}

test('Dashboard routes and layout files exist', () => {
  const picksPage = path.join(dashboardRoot, 'picks', 'page.tsx');
  const noBetPage = path.join(dashboardRoot, 'no-bet', 'page.tsx');
  const layout = path.join(dashboardRoot, 'layout.tsx');

  assert.equal(fs.existsSync(picksPage), true, 'Missing picks route page');
  assert.equal(fs.existsSync(noBetPage), true, 'Missing no-bet route page');
  assert.equal(fs.existsSync(layout), true, 'Missing dashboard layout');
});

test('Dashboard layout exposes tabs and children slot', () => {
  const layout = path.join(dashboardRoot, 'layout.tsx');
  const content = read(layout);

  assert.match(content, /href="\/picks"/, 'Layout must expose Picks tab link');
  assert.match(content, /href="\/no-bet"/, 'Layout must expose No-Bet tab link');
  assert.match(content, /\{children\}/, 'Layout must render children');
});

test('Picks and No-Bet pages include explicit headings', () => {
  const picksPage = read(path.join(dashboardRoot, 'picks', 'page.tsx'));
  const noBetPage = read(path.join(dashboardRoot, 'no-bet', 'page.tsx'));

  assert.match(picksPage, />\s*Picks\s*</, 'Picks page heading is missing');
  assert.match(noBetPage, />\s*No-Bet\s*</, 'No-Bet page heading is missing');
});
