import { expect, test } from './support/app';
import { expectNoSeriousViolations } from './support/axe';
import { resultViews, statusPill } from './support/page';

// Every result state, rendered by the app from a saved report (tests/unit/report_fixtures.py).
test.use({ appOptions: { model: 'demo', seed: true } });

type Expected = { state: string; pill: string; shows: string[] };

const RESULTS: Expected[] = [
  { state: 'healed', pill: 'Healed', shows: ['Download fixed spec', 'Re-run passed in 2.1s'] },
  {
    state: 'healed_after_retries',
    pill: 'Healed',
    shows: ['Attempt 1', 'Fix not applied', 'Attempt 2', 'Showing attempt 2'],
  },
  {
    state: 'not_healed',
    pill: 'Not healed',
    shows: [
      'Re-run failed',
      'Fix not applied',
      'Invalid model reply',
      "The response didn't match the HealingAnalysis schema",
    ],
  },
  {
    state: 'app_defect',
    pill: 'Likely app bug',
    shows: ['Stopped: likely app bug', 'The test was not changed'],
  },
  {
    state: 'nothing_to_heal',
    pill: 'Nothing to heal',
    shows: ['The test passed on its first run'],
  },
  { state: 'cancelled', pill: 'Cancelled', shows: ['The file was not changed'] },
  { state: 'model_error', pill: 'Error', shows: ['Model unreachable', 'Could not reach Ollama'] },
  {
    state: 'with_warnings',
    pill: 'Healed',
    shows: ['Page context unavailable', 'Repair used text replacement', 'Applied as a text edit'],
  },
  {
    state: 'demo_healed',
    pill: 'Healed',
    shows: ['Demo', 'Answers replayed from samples/recordings'],
  },
  { state: 'generate_passed', pill: 'Passed', shows: ['Download spec', 'Passed in Chromium'] },
  { state: 'generate_not_run', pill: 'Not run', shows: ['Run test'] },
  { state: 'generate_failed', pill: 'Run failed', shows: ['Heal this test'] },
  {
    state: 'generate_error',
    pill: 'Error',
    shows: ['Model timed out', 'did not answer within 300 seconds', 'No test written'],
  },
];

for (const { state, pill, shows } of RESULTS) {
  test(`saved result: ${state}`, async ({ page, app }) => {
    await page.goto(`/reports/${app.reports[state]}`);

    await expect(statusPill(page)).toHaveText(pill);
    for (const text of shows) {
      await expect(page.locator('#main').getByText(text).first()).toBeVisible();
    }
    await expectNoSeriousViolations(page);
  });
}

test('result views and attempts are links that work from the keyboard', async ({ page, app }) => {
  await page.goto(`/reports/${app.reports.healed_after_retries}`);
  const views = resultViews(page);
  await expect(views.getByRole('link')).toHaveText([
    'Diff',
    'Re-run video',
    'Execution log',
    'Model I/O',
  ]);
  await expect(views.getByRole('link', { name: 'Diff' })).toHaveAttribute('aria-current', 'page');

  await views.getByRole('link', { name: 'Model I/O' }).focus();
  await page.keyboard.press('Enter');
  await expect(page).toHaveURL(/tab=model/);
  await expect(views.getByRole('link', { name: 'Model I/O' })).toHaveAttribute(
    'aria-current',
    'page'
  );
  await expect(page.getByRole('columnheader', { name: 'Sent to the model' })).toBeVisible();

  await page
    .getByRole('navigation', { name: 'Attempts' })
    .getByRole('link', { name: /Attempt 1/ })
    .focus();
  await page.keyboard.press('Enter');
  await expect(page).toHaveURL(/attempt=1/);
  await expect(page).toHaveURL(/tab=model/);
  await expect(page.getByRole('complementary', { name: 'Diagnosis · attempt 1' })).toBeVisible();
});

test('a view that a result does not have falls back to the first one', async ({ page, app }) => {
  await page.goto(`/reports/${app.reports.not_healed}?tab=diff`);

  await expect(resultViews(page).getByRole('link')).toHaveText(['Execution log', 'Model I/O']);
  await expect(page.getByRole('region', { name: 'Execution log' })).toBeVisible();
});

test('an unknown report says so', async ({ page }) => {
  await page.goto('/reports/20260101-000000-heal-missing');

  await expect(page.getByRole('heading', { name: 'No such report' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Back to Heal' })).toBeVisible();
});
