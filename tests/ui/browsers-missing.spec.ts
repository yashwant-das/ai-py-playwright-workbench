import { expect, test } from './support/app';
import { expectNoSeriousViolations } from './support/axe';

test.use({ appOptions: { model: 'demo', browsers: false } });

const PAGES = [
  { path: '/heal', start: 'Heal sample test: Selector drift' },
  { path: '/generate', start: 'Generate test' },
];

for (const { path, start } of PAGES) {
  test(`${path}: missing browsers block the page and say how to install them`, async ({ page }) => {
    await page.goto(path);

    const banner = page
      .getByRole('alert')
      .filter({ hasText: "Playwright browsers aren't installed" });
    await expect(banner).toContainText('npx playwright install chromium');
    await expect(page.getByRole('button', { name: start })).toBeDisabled();
    await expectNoSeriousViolations(page);
  });
}
