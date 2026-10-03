// Playwright E2E config for the N.O.V.A. clinical workspace (independent-audit #9/#10).
//
// This harness is IMPLEMENTED but its EXECUTION is NOT VERIFIED in the authoring environment
// (no browser / npm install available). It is deliberately NOT wired into GitHub Actions
// (Actions budget). To run locally against a running stack:
//
//   1. Start the backend (demo mode is fine):
//        cd backend && AUTH_MODE=demo EMR_MODE=demo NOVA_LLM_PROVIDER=mock \
//          python -m uvicorn app.main:app --port 8000
//   2. Start the frontend dev server (proxying /api -> :8000), or serve the built dist.
//   3. npm run test:e2e        (installs browsers on first run: npx playwright install)
//
// BASE_URL defaults to the vite dev server; override with PLAYWRIGHT_BASE_URL.
import {defineConfig, devices} from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 60_000,
  expect: {timeout: 10_000},
  fullyParallel: false,
  retries: 0,
  reporter: [['list']],
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    {name: 'chromium', use: {...devices['Desktop Chrome']}},
  ],
  // No webServer here on purpose: the backend + frontend are started manually (see header), so a
  // failed harness never masks a missing stack as a passing E2E.
});
