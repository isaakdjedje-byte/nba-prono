#!/bin/bash
# Test Changed Files - Selective test execution
# Usage: ./scripts/test-changed.sh [base-branch]
# Généré par BMad TEA Agent - Test Architect Module

set -e

BASE_BRANCH=${1:-main}
WORKSPACE_DIR="nba-prono"

echo "🎯 Selective Test Runner"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Base branch: $BASE_BRANCH"
echo ""

cd "$WORKSPACE_DIR" || exit 1

# Detect changed files
CHANGED_FILES=$(git diff --name-only "$BASE_BRANCH...HEAD")

if [ -z "$CHANGED_FILES" ]; then
  echo "✅ No files changed. Skipping tests."
  exit 0
fi

echo "Changed files:"
echo "$CHANGED_FILES" | sed 's/^/  - /'
echo ""

# Determine test strategy
run_all=false
run_smoke_only=false

# Critical files = run all tests
if echo "$CHANGED_FILES" | grep -qE '(package\.json|package-lock\.json|playwright\.config|cypress\.config|\.github/workflows)'; then
  echo "⚠️  Critical configuration files changed. Running ALL tests."
  run_all=true

# Auth/security changes
elif echo "$CHANGED_FILES" | grep -qE '(auth|login|signup|security)'; then
  echo "🔒 Auth/security files changed. Running auth + smoke tests."
  npm run test:e2e -- --grep "@auth|@smoke"
  exit $?

# API changes
elif echo "$CHANGED_FILES" | grep -qE '(api|service|controller)'; then
  echo "🔌 API files changed. Running API + smoke tests."
  npm run test:e2e -- --project=api
  exit $?

# Test files changed = run those specific tests
elif echo "$CHANGED_FILES" | grep -qE '\.(spec|test)\.(ts|js)$'; then
  CHANGED_TESTS=$(echo "$CHANGED_FILES" | grep -E '\.(spec|test)\.(ts|js)$' || echo "")
  echo "🧪 Test files changed. Running specific tests:"
  echo "$CHANGED_TESTS" | sed 's/^/  - /'
  npm run test:e2e -- $CHANGED_TESTS
  exit $?

# Documentation/config only
elif echo "$CHANGED_FILES" | grep -qE '\.(md|txt|json|yml|yaml)$'; then
  echo "📝 Documentation/config files changed. Running smoke tests only."
  run_smoke_only=true
else
  echo "⚙️  Other files changed. Running smoke tests."
  run_smoke_only=true
fi

# Execute selected strategy
if [ "$run_all" = true ]; then
  echo ""
  echo "Running full E2E test suite..."
  npm run test:e2e
elif [ "$run_smoke_only" = true ]; then
  echo ""
  echo "Running smoke tests..."
  npm run test:smoke
fi
