import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e', fullyParallel: false, workers: 1, retries: 0,
  forbidOnly: !!process.env.CI,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: { baseURL: 'http://127.0.0.1:4173', trace: 'retain-on-failure', screenshot: 'only-on-failure' },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    { command: 'node e2e/service.mjs model', url: 'http://127.0.0.1:8766/state', reuseExistingServer: false },
    { command: 'node e2e/service.mjs backend', url: 'http://127.0.0.1:8765/api/health/', reuseExistingServer: false },
    { command: 'node e2e/service.mjs frontend', url: 'http://127.0.0.1:4173', reuseExistingServer: false },
  ],
});
