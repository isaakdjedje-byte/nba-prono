#!/bin/bash
# Burn-In Test Runner
# Usage: ./scripts/burn-in.sh [iterations] [base-branch]
# Généré par BMad TEA Agent - Test Architect Module

set -e

# Configuration
ITERATIONS=${1:-10}
BASE_BRANCH=${2:-main}
WORKSPACE_DIR="nba-prono"

echo "🔥 Burn-In Test Runner"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Iterations: $ITERATIONS"
echo "Base branch: $BASE_BRANCH"
echo "Workspace: $WORKSPACE_DIR"
echo ""

cd "$WORKSPACE_DIR" || exit 1

# Detect changed test files
echo "📋 Detecting changed test files..."
CHANGED_SPECS=$(git diff --name-only "$BASE_BRANCH...HEAD" | grep -E '\.(spec|test)\.(ts|js|tsx|jsx)$' || echo "")

if [ -z "$CHANGED_SPECS" ]; then
  echo "✅ No test files changed. Running all tests for burn-in."
  TEST_CMD="npm run test:e2e"
else
  echo "Changed test files:"
  echo "$CHANGED_SPECS" | sed 's/^/  - /'
  echo ""
  SPEC_COUNT=$(echo "$CHANGED_SPECS" | wc -l | xargs)
  echo "Running burn-in on $SPEC_COUNT test file(s)..."
  TEST_CMD="npm run test:e2e -- $CHANGED_SPECS"
fi

echo ""

# Burn-in loop
FAILURES=()
for i in $(seq 1 $ITERATIONS); do
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "🔄 Iteration $i/$ITERATIONS"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  if $TEST_CMD 2>&1 | tee "../burn-in-log-$i.txt"; then
    echo "✅ Iteration $i passed"
  else
    echo "❌ Iteration $i failed"
    FAILURES+=($i)

    # Save failure artifacts
    mkdir -p "../burn-in-failures/iteration-$i"
    cp -r test-results/ "../burn-in-failures/iteration-$i/" 2>/dev/null || true
    cp -r playwright-report/ "../burn-in-failures/iteration-$i/" 2>/dev/null || true

    echo ""
    echo "🛑 BURN-IN FAILED on iteration $i"
    echo "Failure artifacts saved to: burn-in-failures/iteration-$i/"
    echo "Logs saved to: burn-in-log-$i.txt"
    echo ""
    exit 1
  fi

echo ""
done

# Success summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 BURN-IN PASSED"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "All $ITERATIONS iterations passed"
echo "Tests are stable and ready to merge."
echo ""

# Cleanup logs
rm -f ../burn-in-log-*.txt

exit 0
