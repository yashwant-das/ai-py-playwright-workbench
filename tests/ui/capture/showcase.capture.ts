import { mkdirSync, rmSync } from 'node:fs';
import path from 'node:path';

import type { Page } from '@playwright/test';

import { expect, test } from '../support/app';
import { expectResult, resultViews } from '../support/page';

test.use({ appOptions: { model: 'demo' } });

const ROOT = path.resolve(__dirname, '..', '..', '..');
const ASSETS = path.join(ROOT, 'docs', 'assets');
const FRAMES = path.join(ROOT, 'test-results', 'capture-frames');

/** Screenshots the page over and over until stopped; make_gif.py turns the files into the GIF. */
function film(page: Page): { stop: () => Promise<void> } {
  const started = Date.now();
  let filming = true;
  const loop = (async () => {
    while (filming) {
      const name = String(Date.now() - started).padStart(6, '0');
      // A page that is mid-navigation cannot be captured; the next pass will be.
      await page
        .screenshot({ path: path.join(FRAMES, `${name}.png`), scale: 'css' })
        .catch(() => undefined);
      await page.waitForTimeout(80);
    }
  })();
  return {
    stop: async () => {
      filming = false;
      await loop;
    },
  };
}

test('the heal GIF and the heal screenshots', async ({ page }) => {
  rmSync(FRAMES, { recursive: true, force: true });
  mkdirSync(FRAMES, { recursive: true });
  await page.goto('/heal');
  await expect(page.getByRole('heading', { name: 'Pick a sample or upload a spec' })).toBeVisible();
  const sample = page.getByRole('button', { name: 'Heal the Selector drift sample' });

  const camera = film(page);
  await page.waitForTimeout(1200);
  await sample.hover();
  await page.waitForTimeout(500);
  await sample.click();
  await expectResult(page, 'Healed');
  await page.waitForTimeout(2600);
  await resultViews(page).getByRole('link', { name: 'Model I/O' }).click();
  await expect(page.getByRole('columnheader', { name: 'Sent to the model' })).toBeVisible();
  await page.waitForTimeout(2400);
  await camera.stop();

  await page.screenshot({ path: path.join(ASSETS, 'heal-model-io.png') });
  await resultViews(page).getByRole('link', { name: 'Diff' }).click();
  await expect(page.getByRole('region', { name: 'Diff' })).toBeVisible();
  await page.screenshot({ path: path.join(ASSETS, 'heal-healed.png') });
});

test('the app-bug screenshot', async ({ page }) => {
  await page.goto('/heal');
  await page.getByRole('button', { name: 'Heal the App bug sample' }).click();
  await expectResult(page, 'Likely app bug');
  await page.screenshot({ path: path.join(ASSETS, 'heal-app-bug.png') });
});

test('the generate screenshot', async ({ page }) => {
  await page.goto('/generate?example=contact-form');
  await page.getByRole('button', { name: 'Generate test' }).click();
  await expectResult(page, 'Passed');
  await page.screenshot({ path: path.join(ASSETS, 'generate-passed.png') });
});
