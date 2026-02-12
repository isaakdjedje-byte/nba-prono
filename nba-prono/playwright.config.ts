import { defineConfig, devices } from '@playwright/test';
import { config as dotenvConfig } from 'dotenv';
import path from 'path';

// Load environment variables from .env file
dotenvConfig({
  path: path.resolve(__dirname, '.env'),
});

// Determine environment
const environment = process.env.TEST_ENV || 'local';
console.log(`🎭 Running Playwright tests against: ${environment.toUpperCase()}`);

// Base configuration shared across all environments
const baseConfig = defineConfig({
  testDir: './tests',
  outputDir: './test-results',

  // Parallel execution settings
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,

  // Timeout standards
  timeout: 60000, // Global test timeout: 60 seconds
  expect: {
    timeout: 10000, // Expect assertions timeout: 10 seconds
  },

  // Reporter configuration
  reporter: [
    ['html', { outputFolder: 'playwright-report', open: 'never' }],
    ['junit', { outputFile: 'test-results/results.xml' }],
    ['list'],
  ],

  // Shared settings for all projects
  use: {
    // Timeouts
    actionTimeout: 15000, // Click, fill, etc.: 15 seconds
    navigationTimeout: 30000, // page.goto: 30 seconds

    // Artifacts - captured on failure
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    trace: 'on-first-retry',

    // Viewport
    viewport: { width: 1280, height: 720 },
  },

  // Project configuration for different browsers and scenarios
  projects: [
    // Setup project for authentication
    {
      name: 'setup',
      testMatch: /global\.setup\.ts/,
    },

    // Desktop browsers
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
      dependencies: ['setup'],
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
      dependencies: ['setup'],
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
      dependencies: ['setup'],
    },

    // Mobile browsers
    {
      name: 'mobile-chrome',
      use: { ...devices['Pixel 5'] },
      dependencies: ['setup'],
    },
    {
      name: 'mobile-safari',
      use: { ...devices['iPhone 13'] },
      dependencies: ['setup'],
    },

    // API tests (no browser needed)
    {
      name: 'api',
      testMatch: /api\/.*\.spec\.ts/,
      use: {
        baseURL: process.env.API_URL || 'http://localhost:3000',
      },
    },
  ],

  // Web server configuration for local development
  webServer: environment === 'local' ? {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 120000,
  } : undefined,
});

// Environment-specific overrides
const envConfigMap: Record<string, typeof baseConfig> = {
  local: {
    ...baseConfig,
    use: {
      ...baseConfig.use,
      baseURL: process.env.BASE_URL || 'http://localhost:3000',
    },
  },
  staging: {
    ...baseConfig,
    use: {
      ...baseConfig.use,
      baseURL: process.env.BASE_URL || 'https://staging.nba-prono.app',
      ignoreHTTPSErrors: true,
    },
  },
  production: {
    ...baseConfig,
    retries: 3,
    use: {
      ...baseConfig.use,
      baseURL: process.env.BASE_URL || 'https://nba-prono.app',
      video: 'on',
    },
  },
};

// Validate environment
if (!envConfigMap[environment]) {
  console.error(`❌ No configuration found for environment: ${environment}`);
  console.error(`   Available environments: ${Object.keys(envConfigMap).join(', ')}`);
  process.exit(1);
}

export default envConfigMap[environment];
