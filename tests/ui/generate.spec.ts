import { expect, test } from './support/app';
import { expectNoSeriousViolations } from './support/axe';
import { expectResult, statusPill } from './support/page';

test.use({ appOptions: { model: 'demo', seed: true } });

const SCENARIO = 'A user can send the contact form';

test('empty: the form, the one example Demo can answer, and an empty result area', async ({
  page,
}) => {
  await page.goto('/generate');

  await expect(page.getByRole('heading', { name: 'Your test will appear here' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Contact form' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Checkout' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Generate test' })).toBeEnabled();
  await expect(page.getByRole('heading', { name: 'Locked-out account' })).toBeVisible();
  await expect(page.getByRole('link', { name: /Use .* example/ })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Choose LM Studio or Ollama to use' })).toHaveCount(
    3
  );
  await expect(
    page.getByRole('button', { name: 'Choose LM Studio or Ollama to use' }).first()
  ).toBeDisabled();
  await expectNoSeriousViolations(page);
});

test('an invalid URL is refused next to the field', async ({ page }) => {
  await page.goto('/generate');
  await page.getByLabel('Target URL').fill('not a url');
  await page.getByLabel('Scenario').fill(SCENARIO);
  await page.getByRole('button', { name: 'Generate test' }).click();

  await expect(page.locator('#url-error')).toHaveText(
    'Enter a full URL, starting with http:// or https://'
  );
  await expect(page.getByRole('heading', { name: 'Your test will appear here' })).toBeVisible();
});

test('the example generates a passing test, with live steps', async ({ page, baseURL }) => {
  await page.goto('/generate');
  await page.getByRole('link', { name: 'Contact form' }).click();
  await expect(page.getByLabel('Target URL')).toHaveValue(`${baseURL}/sample-site/`);
  await expect(page.getByLabel('Scenario')).toHaveValue(SCENARIO);
  await page.getByRole('button', { name: 'Generate test' }).click();

  // Generating
  await expect(statusPill(page)).toHaveText('Generating');
  await expect(page.getByRole('list', { name: 'Progress' }).getByRole('listitem')).toContainText([
    'Load page context',
    'Ask the model',
    'Run the test',
  ]);

  // Passed
  await expectResult(page, 'Passed');
  await expect(page.getByRole('region', { name: /workspace\/specs\// })).toContainText(
    "getByRole('button', { name: 'Submit' })"
  );
  const context = page.getByRole('complementary', { name: 'Page context used' });
  await expect(context).toContainText('Passed in Chromium');
  await expect(context).toContainText('not a live model');
  await expect(page.getByRole('link', { name: 'Download spec' })).toBeVisible();
  await expectNoSeriousViolations(page);
});

test('a test generated without running can be run afterwards', async ({ page }) => {
  await page.goto('/generate?example=contact-form');
  await page.getByLabel('Run the test after generating').uncheck();
  await page.getByRole('button', { name: 'Generate test' }).click();

  await expectResult(page, 'Not run');
  await expect(page.getByRole('complementary', { name: 'Page context used' })).toContainText(
    'Not run'
  );

  await page.getByRole('button', { name: 'Run test' }).click();
  await expectResult(page, 'Passed');
});

test('a generated test that fails can be sent to Heal', async ({ page, app }) => {
  await page.goto(`/reports/${app.reports.generate_failed}`);
  await expect(statusPill(page)).toHaveText('Run failed');

  await page.getByRole('button', { name: 'Heal this test' }).click();

  await expect(page).toHaveURL(/\/heal\?run=/);
  await expectResult(page, 'Healed');
  await expect(
    page.getByRole('heading', { name: 'a-user-can-send-the-contact-form.spec.ts' })
  ).toBeVisible();
});
