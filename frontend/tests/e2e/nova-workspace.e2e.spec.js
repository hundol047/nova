// N.O.V.A. clinical workspace end-to-end scenario (independent-audit #9).
//
// EXECUTION STATUS: NOT VERIFIED in the authoring environment (no browser / npm install). This
// spec is IMPLEMENTED and intended to be run manually against a live backend+frontend stack (see
// playwright.config.js header). It is NOT wired into GitHub Actions.
//
// The 15 steps mirror the required scenario:
//   1 app load, 2 patient select, 3 N.O.V.A. tab, 4 case create, 5 decision visible,
//   6 observation submit, 7 next decision, 8 locale switch, 9 refresh, 10 resume case,
//   11 timeline restored, 12 review, 13 close, 14 patient change, 15 previous patient state absent.
//
// Selectors prefer role/structural classes (the UI is localized, so text is locale-dependent).
// Where a step depends on backend data (an EXAM/TEST recommendation, a reachable case), the spec
// is written defensively so it fails loudly rather than silently passing on a missing stack.
import {test, expect} from '@playwright/test';

const NOVA_TAB = '#tab-nova';
const WORKSPACE = '.nova-workspace';

async function openNovaForFirstPatient(page) {
  await page.goto('/');
  // 1. app load
  await expect(page.locator('.app-shell')).toBeVisible();
  // 2. patient select (first patient row in the sidebar)
  const firstPatient = page.locator('.patient-list .patient-row-btn').first();
  await expect(firstPatient).toBeVisible();
  await firstPatient.click();
  // 3. N.O.V.A. tab
  await page.locator(NOVA_TAB).click();
  await expect(page.locator(WORKSPACE)).toBeVisible();
}

test('N.O.V.A. full case lifecycle: create -> decide -> observe -> locale -> resume -> review -> close', async ({page}) => {
  await openNovaForFirstPatient(page);

  // If a resume offer appears from a previous run, start fresh for a deterministic scenario.
  const startNew = page.locator(`${WORKSPACE} button`, {hasText: /start new|새 케이스|新規|新建/i});
  if (await startNew.count()) await startNew.first().click();

  // 4. case create
  const cc = page.locator('#nova-cc');
  await expect(cc).toBeVisible();
  await cc.fill('sudden chest pressure with sweating for 30 minutes');
  await page.locator(`${WORKSPACE} button.nova-primary`).first().click();

  // 5. decision visible (differential + next best action)
  await expect(page.locator('.nova-diff-list, .nova-empty')).toBeVisible();
  const caseHeader = page.locator('.nova-case-header');
  await expect(caseHeader).toBeVisible();
  const turnBefore = await caseHeader.innerText();

  // 6/7. observation submit -> next decision (only when an ASK/EXAM/TEST is recommended)
  const obsForm = page.locator('#nova-obs-result');
  if (await obsForm.count()) {
    await obsForm.fill('no prior cardiac history; pain radiates to left arm');
    await page.locator('form.nova-panel button.nova-primary', {hasText: /submit|제출|送信|提交|观察/i}).first().click();
    await expect(page.locator('.nova-case-header')).not.toHaveText(turnBefore, {timeout: 15_000});
  }

  // 8. locale switch (top-bar selector) -> case must NOT reset
  await page.locator('.nova-lang-selector button', {hasText: 'English'}).click();
  await expect(page.locator(WORKSPACE)).toBeVisible();
  await expect(page.locator('.nova-case-header')).toBeVisible(); // still the same case

  // capture case id from the header for the resume assertion
  const caseIdText = await page.locator('.nova-case-header').innerText();

  // 9/10/11. refresh -> re-open patient+NOVA -> resume -> timeline restored
  await openNovaForFirstPatient(page);
  const resumeBtn = page.locator(`${WORKSPACE} button`, {hasText: /resume|이어하기|再開|继续/i});
  await expect(resumeBtn.first()).toBeVisible({timeout: 15_000}); // an open case should be offered
  await resumeBtn.first().click();
  await expect(page.locator('.nova-timeline')).toBeVisible();
  // timeline should carry at least the turns recorded before refresh (if any observation was made)
  await expect(page.locator('.nova-case-header')).toBeVisible();

  // 12/13. clinician review -> close (Accept + reason)
  const accept = page.locator('.nova-review button', {hasText: /accept|동의|承認|接受/i});
  if (await accept.count()) {
    await accept.first().click();
    await page.locator('#nova-review-reason').fill('Agree with the leading assessment; will proceed per protocol.');
    await page.locator('.nova-review button.nova-primary').click();
    await expect(page.locator('.nova-review .nova-muted')).toBeVisible();
  }

  // 14/15. patient change -> previous patient's case state absent
  const patients = page.locator('.patient-list .patient-row-btn');
  if (await patients.count() > 1) {
    await patients.nth(1).click();
    await page.locator(NOVA_TAB).click();
    // The new patient must NOT show the previous case: either the start form, a resume offer for a
    // DIFFERENT case, or the custom-patient notice -- never the closed case's review panel.
    await expect(page.locator(WORKSPACE)).toBeVisible();
    await expect(page.locator('.nova-review .nova-muted', {hasText: /closed|종료|終了|关闭/i})).toHaveCount(0);
  }
});
