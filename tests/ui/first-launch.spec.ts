import { expect, test } from './support/app';
import { expectNoSeriousViolations } from './support/axe';
import { expectResult, openModelMenu } from './support/page';

// S1: a first-time visitor with no model installed heals the sample.
test.use({ appOptions: { model: 'none' } });

test('a fresh workspace has no model and says how to get one', async ({ page, app }) => {
  // The suite's app never uses the developer's port or workspace.
  expect(app.url).not.toContain(':7860');
  expect(app.workspace).not.toContain(process.cwd());

  await page.goto('/');

  await expect(page).toHaveURL(/\/heal$/);
  await expect(page.getByRole('heading', { name: 'No model server found' })).toBeVisible();
  await expect(page.getByRole('button', { name: /Change the model/ })).toContainText(
    'Not connected'
  );
  await expect(page.getByRole('button', { name: 'Heal the Selector drift sample' })).toBeDisabled();
  await expect(page.getByText('Connect a model to run this.')).toBeVisible();
  await expectNoSeriousViolations(page);
});

test('the model menu opens and closes from the keyboard', async ({ page }) => {
  await page.goto('/heal');
  const pill = page.getByRole('button', { name: /Change the model/ });
  const menu = page.locator('#model-menu');

  await pill.focus();
  await page.keyboard.press('Enter');
  await expect(menu.getByRole('heading', { name: 'Model' })).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(menu).toBeHidden();
  await expect(pill).toBeFocused();
});

test('the model menu will not save a server that is down', async ({ page }) => {
  await page.goto('/heal');
  const menu = await openModelMenu(page);
  await menu.getByLabel('Server').fill('http://127.0.0.1:9/v1');
  await menu.getByRole('button', { name: 'Retry' }).click();

  await expect(menu.getByText('Unreachable', { exact: true })).toBeVisible();
  await expect(menu.getByLabel('Server')).toHaveValue('http://127.0.0.1:9/v1');
  await expect(menu.getByLabel('Server')).toHaveAttribute('aria-invalid', 'true');
  await expect(menu.getByRole('button', { name: 'Save' })).toBeDisabled();
  await expectNoSeriousViolations(page);
});

test('choosing Demo heals the selector-drift sample', async ({ page }) => {
  await page.goto('/heal');
  const menu = await openModelMenu(page);
  await menu.locator('label', { hasText: 'Demo' }).click();
  await expect(menu.getByText('Replays recorded model answers')).toBeVisible();
  await menu.getByRole('button', { name: 'Save' }).click();

  await expect(page.getByRole('button', { name: /Change the model/ })).toContainText(
    'scripted answers'
  );
  await page.getByRole('button', { name: 'Heal the Selector drift sample' }).click();

  await expectResult(page, 'Healed');
  await expect(page.getByRole('heading', { name: 'contact-form.spec.ts' })).toBeVisible();
  await expect(page.locator('#main .result-head').getByText('Demo', { exact: true })).toBeVisible();
});
