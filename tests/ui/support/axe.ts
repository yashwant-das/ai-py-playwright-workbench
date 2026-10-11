import { AxeBuilder } from '@axe-core/playwright';
import { expect, type Page } from '@playwright/test';

/** Fails on any axe violation rated serious or critical: the gate in the v2 spec, section 8. */
export async function expectNoSeriousViolations(page: Page): Promise<void> {
  const { violations } = await new AxeBuilder({ page }).analyze();
  const blocking = violations
    .filter((violation) => violation.impact === 'serious' || violation.impact === 'critical')
    .map((violation) => {
      const where = violation.nodes.map((node) => node.target.join(' ')).join(' | ');
      return `${violation.id}: ${where}`;
    });
  expect(blocking).toEqual([]);
}
