#!/usr/bin/env node
/**
 * Workspace Context Checker
 * Validates that the project is running in the correct workspace context
 */

import { fileURLToPath } from 'url';
import { dirname, resolve } from 'path';
import { existsSync, readFileSync } from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Check if we're in the correct workspace
const packageJsonPath = resolve(process.cwd(), 'package.json');

if (!existsSync(packageJsonPath)) {
  console.error('❌ No package.json found in current directory');
  process.exit(1);
}

const packageJson = JSON.parse(readFileSync(packageJsonPath, 'utf-8'));

if (packageJson.name !== 'nba-prono') {
  console.error(`❌ Wrong workspace: expected "nba-prono" but found "${packageJson.name}"`);
  console.error('   Make sure to run commands from the nba-prono directory');
  process.exit(1);
}

console.log('✅ Workspace context validated: nba-prono');
process.exit(0);
