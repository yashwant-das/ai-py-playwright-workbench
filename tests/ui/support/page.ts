import { expect, type Locator, type Page } from '@playwright/test';

/** A live heal or generation is real work in Chromium; allow for slow machines. */
export const RUN_TIMEOUT_MS = 60_000;

/** The status pill at the top of a live run or a result. */
export function statusPill(page: Page): Locator {
  return page.locator('#main .result-head .pill').first();
}

/** Waits for a run to finish and its report page to show `status`. */
export async function expectResult(page: Page, status: string): Promise<void> {
  await expect(statusPill(page)).toHaveText(status, { timeout: RUN_TIMEOUT_MS });
  await expect(page).toHaveURL(/\/reports\//);
}

/**
 * Opens the model menu and waits until the server has filled it in.
 * Use it once per page load: every reopening fetches the menu again, which
 * replaces anything typed into it in the meantime.
 */
export async function openModelMenu(page: Page): Promise<Locator> {
  await page.getByRole('button', { name: /Change the model/ }).click();
  const menu = page.locator('#model-menu');
  await expect(menu.getByRole('heading', { name: 'Model' })).toBeVisible();
  return menu;
}

/** The links that switch a heal result between Diff, video, log and Model I/O. */
export function resultViews(page: Page): Locator {
  return page.getByRole('navigation', { name: 'Result views' });
}
