import { defineConfig, devices } from '@playwright/test';

/**
 * The UI suite: Playwright Test drives the real app in Chromium.
 *
 * Spec files start their own app on a free port with a temporary workspace
 * (tests/ui/support/app.ts), so the suite never touches workspace/ or port 7860.
 * Files that ask for the same app options share one app.
 */
export default defineConfig({
  testDir: 'tests/ui',
  outputDir: 'test-results/ui',
  // An app runs one heal or generation at a time.
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  timeout: 90_000,
  expect: { timeout: 10_000 },
  reporter: [['list'], ['html', { outputFolder: 'playwright-report', open: 'never' }]],
  use: { trace: 'retain-on-failure', screenshot: 'only-on-failure' },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } },
    },
  ],
});
