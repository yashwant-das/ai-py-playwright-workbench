import { defineConfig, devices } from '@playwright/test';

/**
 * Captures the README's screenshots and the frames of its GIF: `npm run docs:capture`.
 * Not a test suite: it drives the real app with the Demo model and writes to docs/assets/.
 */
export default defineConfig({
  testDir: 'tests/ui/capture',
  testMatch: /.*\.capture\.ts$/,
  outputDir: 'test-results/capture',
  workers: 1,
  timeout: 120_000,
  reporter: [['list']],
  use: {
    ...devices['Desktop Chrome'],
    viewport: { width: 1280, height: 800 },
    deviceScaleFactor: 2,
  },
});
