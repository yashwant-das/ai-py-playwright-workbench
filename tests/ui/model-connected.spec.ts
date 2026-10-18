import { expect, test } from './support/app';
import { expectNoSeriousViolations } from './support/axe';
import { openModelMenu } from './support/page';

// A fake OpenAI-compatible server stands in for LM Studio.
test.use({ appOptions: { model: 'fake' } });

test("a connected model shows its name and lists the server's chat models", async ({ page }) => {
  await page.goto('/heal');
  const pill = page.getByRole('button', { name: /Change the model/ });
  await expect(pill).toContainText('fake-model');
  await expect(pill).toContainText('LM Studio');
  await expect(page.getByText('asks fake-model · LM Studio for a fix')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Heal the Selector drift sample' })).toBeEnabled();

  const menu = await openModelMenu(page);
  await expect(menu.getByText('Connected', { exact: true })).toBeVisible();
  await expect(menu.getByLabel('Server')).toHaveValue(/^http:\/\/127\.0\.0\.1:\d+\/v1$/);
  const models = menu.getByLabel('Model', { exact: true });
  await expect(models).toHaveValue('fake-model');
  // The server also lists an embedding model, which cannot chat.
  await expect(models.locator('option')).toHaveText(['fake-model']);
  await expect(menu.getByRole('button', { name: 'Save' })).toBeEnabled();
  await expectNoSeriousViolations(page);
});

test('with a real model both Generate examples are offered', async ({ page }) => {
  await page.goto('/generate');

  await expect(page.getByRole('link', { name: 'Contact form' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Checkout' })).toBeVisible();
});

const publicExamples = [
  {
    title: 'Locked-out account',
    url: 'https://www.saucedemo.com/',
    scenario: 'Attempt to sign in with username locked_out_user and password secret_sauce.',
  },
  {
    title: 'Customer invoice data',
    url: 'https://the-internet.herokuapp.com/tables',
    scenario: 'In the first data table, find the row for Jason Doe.',
  },
  {
    title: 'Checkbox preferences',
    url: 'https://the-internet.herokuapp.com/checkboxes',
    scenario: 'Check both checkboxes and verify both are checked.',
  },
];

for (const example of publicExamples) {
  test(`public example fills the form without running: ${example.title}`, async ({ page }) => {
    await page.goto('/generate');
    await expect(page.getByRole('link', { name: `Use ${example.title} example` })).toBeVisible();
    await page.getByRole('link', { name: `Use ${example.title} example` }).click();
    await expect(page.getByLabel('Target URL')).toHaveValue(example.url);
    await expect(page.getByLabel('Scenario')).toHaveValue(new RegExp(example.scenario));
    await expect(page.getByRole('heading', { name: 'Your test will appear here' })).toBeVisible();
    await expect(page.locator('#scenario-help')).toContainText('starting page once');
    await expectNoSeriousViolations(page);
  });
}
