#!/bin/bash
# CI Local Runner - Mirror CI environment locally
# Usage: ./scripts/ci-local.sh
# Généré par BMad TEA Agent - Test Architect Module

set -e

WORKSPACE_DIR="nba-prono"
TEST_ENV="ci"

echo "🖥️  CI Local Runner"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Simulating CI environment locally..."
echo "Workspace: $WORKSPACE_DIR"
echo "Test Environment: $TEST_ENV"
echo ""

cd "$WORKSPACE_DIR" || exit 1

# Step 1: Pre-check
echo "📋 Step 1: Workspace context check"
node scripts/check-workspace-context.mjs
echo "✅ Context check passed"
echo ""

# Step 2: Clean install
echo "📦 Step 2: Clean dependency install"
rm -rf node_modules package-lock.json
npm ci --prefer-offline --no-audit
echo "✅ Dependencies installed"
echo ""

# Step 3: Install Playwright browsers
echo "🎭 Step 3: Install Playwright browsers"
npx playwright install --with-deps chromium
echo "✅ Browsers installed"
echo ""

# Step 4: Lint
echo "🔍 Step 4: Lint check"
npm run lint
echo "✅ Lint passed"
echo ""

# Step 5: Unit tests
echo "🧪 Step 5: Unit tests"
npm run test:unit
echo "✅ Unit tests passed"
echo ""

# Step 6: Smoke tests
echo "💨 Step 6: Smoke tests"
npm run test:smoke
echo "✅ Smoke tests passed"
echo ""

# Step 7: E2E tests (single shard for local)
echo "🎭 Step 7: E2E tests"
TEST_ENV=ci npm run test:e2e
echo "✅ E2E tests passed"
echo ""

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 CI Local Run Complete"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "All CI stages passed locally!"
echo ""
echo "Next steps:"
echo "  1. Commit your changes"
echo "  2. Push to remote"
echo "  3. Create a PR to trigger CI"
echo ""
