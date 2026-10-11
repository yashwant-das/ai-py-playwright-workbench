import { readFileSync } from 'node:fs';

import { expect, test } from './support/app';
import { expectNoSeriousViolations } from './support/axe';
import { expectResult, resultViews, statusPill } from './support/page';

test.use({ appOptions: { model: 'demo' } });

const SPEC_INPUT = 'input[name="spec"]';

test('idle: the samples and the upload are offered', async ({ page }) => {
  await page.goto('/heal');

  await expect(page.getByRole('heading', { name: 'Pick a sample or upload a spec' })).toBeVisible();
  await expect(page.getByRole('button', { name: /Change the model/ })).toContainText(
    'scripted answers'
  );
  await expect(page.getByRole('button', { name: 'Heal the Selector drift sample' })).toBeEnabled();
  await expect(page.getByRole('button', { name: 'Heal the App bug sample' })).toBeEnabled();
  await expect(page.getByRole('button', { name: 'Heal uploaded file' })).toBeEnabled();
  await expectNoSeriousViolations(page);
});

test('selector drift: live steps, then a healed test with its evidence', async ({ page }) => {
  await page.goto('/heal');
  await page.getByRole('button', { name: 'Heal the Selector drift sample' }).click();

  // Running
  await expect(statusPill(page)).toHaveText('Healing');
  await expect(page.getByRole('list', { name: 'Progress' }).getByRole('listitem')).toContainText([
    'Run the test',
    'Collect evidence',
    'Diagnose',
    'Repair',
    'Verify',
  ]);
  await expect(page.getByRole('button', { name: 'Cancel' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Heal the App bug sample' })).toBeDisabled();
  await expect(page.getByRole('log')).not.toBeEmpty();
  await expectNoSeriousViolations(page);

  // Healed
  await expectResult(page, 'Healed');
  await expect(page.getByRole('heading', { name: 'contact-form.spec.ts' })).toBeVisible();
  await expect(page.locator('#main .result-head').getByText('Demo', { exact: true })).toBeVisible();
  const diff = page.getByRole('region', { name: 'Diff' });
  await expect(diff.locator('.code__line--del')).toContainText("page.locator('#submit-btn')");
  await expect(diff.locator('.code__line--add')).toContainText('data-testid="submit"');
  const diagnosis = page.getByRole('complementary', { name: /Diagnosis/ });
  await expect(diagnosis).toContainText('LOCATOR_DRIFT');
  await expect(diagnosis).toContainText('Re-run passed in');
  await expect(diagnosis).toContainText('not a live model');
  await expectNoSeriousViolations(page);

  // Re-run video
  const views = resultViews(page);
  await views.getByRole('link', { name: 'Re-run video' }).click();
  await expect(page.getByText('Verification re-run of attempt 1')).toBeVisible();
  const source = await page.locator('video').getAttribute('src');
  const clip = await page.request.get(source ?? '');
  expect(clip.ok()).toBe(true);
  expect(clip.headers()['content-type']).toContain('video/webm');

  // Execution log
  await views.getByRole('link', { name: 'Execution log' }).click();
  const log = page.getByRole('region', { name: 'Execution log' });
  await expect(log).toContainText('$ npx playwright test contact-form.spec.ts');
  await expect(log).toContainText('[attempt 1] Healed');

  // Model I/O
  await views.getByRole('link', { name: 'Model I/O' }).click();
  await expect(page.getByRole('columnheader', { name: 'Sent to the model' })).toBeVisible();
  await expect(page.getByRole('region', { name: 'Model reply' })).toContainText(
    'valid HealingAnalysis'
  );
  await expectNoSeriousViolations(page);

  // Downloads
  const report = page.waitForEvent('download');
  await page.getByRole('link', { name: 'Download report' }).click();
  expect((await report).suggestedFilename()).toMatch(/\.json$/);
  const fixed = page.waitForEvent('download');
  await page.getByRole('link', { name: 'Download fixed spec' }).click();
  expect(readFileSync(await (await fixed).path(), 'utf8')).toContain('data-testid="submit"');
});

test('app bug: the heal stops and leaves the test alone', async ({ page }) => {
  await page.goto('/heal');
  await page.getByRole('button', { name: 'Heal the App bug sample' }).click();

  await expectResult(page, 'Likely app bug');
  await expect(page.getByRole('heading', { name: 'checkout.spec.ts' })).toBeVisible();
  await expect(page.getByText('Stopped: likely app bug')).toBeVisible();
  await expect(page.getByRole('complementary', { name: /Diagnosis/ })).toContainText(
    'POTENTIAL_APP_DEFECT'
  );
  await expect(page.getByRole('link', { name: 'Download fixed spec' })).toHaveCount(0);
  await expect(page.getByRole('link', { name: 'Heal again' })).toBeVisible();
  await expectNoSeriousViolations(page);
});

test('an uploaded test that already passes has nothing to heal', async ({ page, baseURL }) => {
  const passing = [
    "import { test, expect } from '@playwright/test';",
    '',
    "test('The sample site loads', async ({ page }) => {",
    `  await page.goto('${baseURL}/sample-site/');`,
    "  await expect(page.getByLabel('Name')).toBeVisible();",
    '});',
    '',
  ].join('\n');

  await page.goto('/heal');
  await page.locator(SPEC_INPUT).setInputFiles({
    name: 'site-loads.spec.ts',
    mimeType: 'text/plain',
    buffer: Buffer.from(passing),
  });
  await expect(page.locator('#upload-name')).toHaveText('site-loads.spec.ts');
  await page.getByRole('button', { name: 'Heal uploaded file' }).click();

  await expectResult(page, 'Nothing to heal');
  await expect(page.getByText('The test passed on its first run')).toBeVisible();
});

test('cancel stops a run and keeps the test unchanged', async ({ page }) => {
  await page.goto('/heal');
  await page.getByRole('button', { name: 'Heal the Selector drift sample' }).click();
  await page.getByRole('button', { name: 'Cancel' }).click();

  await expectResult(page, 'Cancelled');
  await expect(page.getByText('The file was not changed')).toBeVisible();
});

test('upload errors are shown next to the upload', async ({ page }) => {
  await page.goto('/heal');
  const error = page.locator('#upload-error');
  const start = page.getByRole('button', { name: 'Heal uploaded file' });

  await start.click();
  await expect(error).toHaveText('Choose a .spec.ts file first.');

  await page.locator(SPEC_INPUT).setInputFiles({
    name: 'notes.txt',
    mimeType: 'text/plain',
    buffer: Buffer.from('not a test'),
  });
  await start.click();
  await expect(error).toHaveText("notes.txt isn't a test file. Only .spec.ts files are supported.");

  await page.locator(SPEC_INPUT).setInputFiles({
    name: 'huge.spec.ts',
    mimeType: 'text/plain',
    buffer: Buffer.alloc(200 * 1024 + 1, 'a'),
  });
  await start.click();
  await expect(error).toHaveText('huge.spec.ts is larger than 200 KB.');
  await expect(page.getByRole('heading', { name: 'Pick a sample or upload a spec' })).toBeVisible();
});
