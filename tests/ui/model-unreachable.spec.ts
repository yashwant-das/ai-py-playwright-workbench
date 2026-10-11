import { expect, test } from './support/app';
import { expectNoSeriousViolations } from './support/axe';

test.use({ appOptions: { model: 'unreachable' } });

test('a saved model that is down blocks runs and offers the demo', async ({ page }) => {
  await page.goto('/heal');
  await expect(
    page.getByRole('heading', { name: "Can't reach Ollama at 127.0.0.1:9/v1" })
  ).toBeVisible();
  await expect(page.getByRole('button', { name: /Change the model/ })).toContainText(
    'Not connected'
  );
  await expect(page.getByRole('button', { name: 'Heal the Selector drift sample' })).toBeDisabled();
  await expectNoSeriousViolations(page);

  await page.goto('/generate');
  await expect(page.getByRole('heading', { name: /Can't reach Ollama/ })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Generate test' })).toBeDisabled();

  await page.getByRole('button', { name: 'Switch to demo model' }).click();
  await expect(page.getByRole('button', { name: /Change the model/ })).toContainText(
    'scripted answers'
  );
  await expect(page.getByRole('button', { name: 'Generate test' })).toBeEnabled();
});
