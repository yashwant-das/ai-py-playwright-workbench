import { test, expect } from '@playwright/test';

test('Contact form sends a message', async ({ page }) => {
  await page.goto('{{BASE_URL}}');
  await page.getByLabel('Name').fill('Ada Lovelace');
  await page.locator('#submit-btn').click({ timeout: 3000 });
  await expect(page.getByRole('status')).toHaveText('Submitted');
});
