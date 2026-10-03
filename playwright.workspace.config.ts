import { defineConfig, devices } from '@playwright/test';

/**
 * The config the workbench runner (src/workbench/runner.py) uses for every
 * generated, uploaded or healed spec. The runner sets:
 *
 *   WORKBENCH_SPECS_DIR     folder that holds the spec under test
 *   WORKBENCH_RECORD_VIDEO  "1" to record a video with captioned actions
 *
 * and passes --output and --reporter=json on the command line.
 */
const recordVideo = process.env.WORKBENCH_RECORD_VIDEO === '1';

export default defineConfig({
  testDir: process.env.WORKBENCH_SPECS_DIR ?? 'workspace/specs',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 30_000,
  use: {
    screenshot: 'only-on-failure',
    trace: 'off',
    video: recordVideo
      ? {
          mode: 'on',
          show: {
            actions: { position: 'top-right' },
            test: { level: 'title', position: 'top-left' },
          },
        }
      : 'off',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
});
