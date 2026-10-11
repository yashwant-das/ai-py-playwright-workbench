import { test, expect } from '@playwright/test';

test('Checkout places an order', async ({ page }) => {
  await page.goto('{{BASE_URL}}checkout.html');
  await page.getByLabel('Email').fill('ada@example.com');
  await page.getByRole('button', { name: 'Place order' }).click();
  await expect(page.getByRole('status')).toHaveText('Order placed', { timeout: 3000 });
});
