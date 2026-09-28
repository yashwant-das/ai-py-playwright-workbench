import { defineConfig } from '@playwright/test';
import baseConfig from './playwright.config';

/**
 * End-to-end report run: re-executes the specs the E2E suite
 * (tests/e2e/e2e_test_pipeline.py) generated and healed, against the local
 * fixture site, and keeps every artifact CI uploads.
 *
 *   npm run test:e2e:report
 */
export default defineConfig(baseConfig, {
  reporter: [
    ['list'],
    ['html', { open: 'never', outputFolder: 'playwright-report' }],
    ['junit', { outputFile: 'reports/playwright-junit.xml' }],
  ],

  use: {
    trace: 'on',
    screenshot: 'on',
  },

  webServer: {
    command: 'python3 -m http.server 4173 --bind 127.0.0.1 --directory tests/e2e/site',
    url: 'http://127.0.0.1:4173/',
    reuseExistingServer: !process.env.CI,
  },
});
